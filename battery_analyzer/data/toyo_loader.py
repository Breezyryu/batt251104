"""Toyo cycler data loader."""

import os
import re
from glob import glob

import pandas as pd

from battery_analyzer.config.enums import CyclerType
from battery_analyzer.data.base_loader import BaseDataLoader
from battery_analyzer.utils.parsers import name_capacity


class ToyoDataLoader(BaseDataLoader):
    """Toyo raw data 로더

    데이터 형식:
        - Raw data: CSV 또는 TXT 형식
        - Condition 컬럼으로 사이클 구분
        - Shift-JIS 인코딩

    컬럼 매핑:
        - Time: 시간 (분으로 변환 필요)
        - Voltage: 전압 (V)
        - Current: 전류 (A → C-rate 변환 필요)
        - Temperature: 온도 (°C)
        - Condition: 사이클 정보 ("Cycle 1", "Cycle 2", ...)

    Note:
        - Condition 컬럼 기반 사이클 분리
        - 시간/전류 단위 변환 필요
    """

    def __init__(self):
        """초기화"""
        super().__init__(CyclerType.TOYO)
        self._raw_data_cache = None  # 원본 데이터 캐싱 (전체 로드 1회)

    def load_cycle(self, data_path: str, cycle_no: int) -> pd.DataFrame:
        """Toyo 사이클 데이터 로드

        Args:
            data_path: 데이터 폴더 경로
            cycle_no: 사이클 번호

        Returns:
            pd.DataFrame: 사이클 데이터

        Raises:
            FileNotFoundError: Raw data 파일이 없는 경우
            ValueError: Condition 컬럼이 없는 경우
        """
        # 원본 데이터 로드 (캐싱)
        if self._raw_data_cache is None:
            self._raw_data_cache = self._load_raw_data(data_path)

        df = self._raw_data_cache

        # Condition 컬럼으로 사이클 필터링
        cycle_pattern = f"Cycle\\s+{cycle_no}"
        cycle_mask = df["Condition"].str.contains(cycle_pattern, case=False, na=False)

        cycle_df = df[cycle_mask].copy()

        if len(cycle_df) == 0:
            raise ValueError(f"No data found for Cycle {cycle_no}")

        # 컬럼 매핑 및 전처리
        cycle_df = self._map_columns(cycle_df)
        self.validate_data(cycle_df)
        cycle_df = self.preprocess_data(cycle_df)

        return cycle_df

    def _load_raw_data(self, data_path: str) -> pd.DataFrame:
        """Toyo raw data 전체 로드

        Args:
            data_path: 데이터 폴더 경로

        Returns:
            pd.DataFrame: 전체 raw data

        Raises:
            FileNotFoundError: 데이터 파일이 없는 경우
        """
        # CSV 또는 TXT 파일 찾기
        raw_files = glob(os.path.join(data_path, "*.csv")) + glob(
            os.path.join(data_path, "*.txt")
        )

        if not raw_files:
            raise FileNotFoundError(f"No raw data files found in {data_path}")

        # 첫 번째 파일 로드 (일반적으로 1개 파일에 전체 데이터)
        df = pd.read_csv(
            raw_files[0], sep="\t", encoding="shift_jis", low_memory=False
        )

        # Condition 컬럼 확인
        if "Condition" not in df.columns:
            raise ValueError(f"'Condition' column not found in {raw_files[0]}")

        return df

    def _map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Toyo 컬럼 → 표준 컬럼 매핑

        Args:
            df: 원본 데이터프레임

        Returns:
            pd.DataFrame: 매핑된 데이터프레임

        Note:
            Time (s) → TimeMin (분)
            Current (A) → Crate (C-rate, 용량 기반 변환 필요)
            Voltage (V) → Vol (V)
            Temperature (°C) → Temp (°C)
        """
        column_mapping = {
            "Time": "TimeMin",
            "Voltage": "Vol",
            "Current": "Crate",
            "Temperature": "Temp",
        }

        # 컬럼 이름 변경
        df = df.rename(columns=column_mapping)

        # 시간 단위 변환 (초 → 분)
        if "TimeMin" in df.columns:
            df["TimeMin"] = df["TimeMin"] / 60

        # 전류 → C-rate 변환 (용량 필요, 임시로 절대값 사용)
        # 실제 변환은 용량 정보 필요
        # 여기서는 A 단위 그대로 사용 (나중에 용량으로 나누기)

        return df

    def get_capacity(self, data_path: str, cycle_no: int, c_rate: float) -> float:
        """Toyo 용량 추출

        Args:
            data_path: 데이터 폴더 경로
            cycle_no: 사이클 번호
            c_rate: 기준 C-rate

        Returns:
            float: 추출된 용량 (mAh)
        """
        # 1. 파일명에서 용량 추출
        capacity = name_capacity(data_path)
        if capacity is not None:
            return capacity

        # 2. 첫 사이클 방전 용량 사용
        try:
            df = self.load_cycle(data_path, cycle_no)

            # 방전 구간 (Crate < 0, 여기서는 Current < 0)
            discharge = df[df["Crate"] < 0]

            if len(discharge) > 0:
                # 방전 전하량 계산 (시간 적분)
                # Q (mAh) = integral(|I(A)| * dt(min))
                time_diff = discharge["TimeMin"].diff().fillna(0)
                capacity_mah = abs(discharge["Crate"] * time_diff).sum()

                if capacity_mah > 0:
                    return capacity_mah

        except (FileNotFoundError, ValueError):
            pass

        # 기본값 반환
        return 58.0  # mAh

    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Toyo 데이터 전처리

        Args:
            df: 원본 데이터프레임

        Returns:
            pd.DataFrame: 전처리된 데이터프레임
        """
        # 기본 전처리 호출
        df = super().preprocess_data(df)

        # Toyo 특화 전처리
        # 시간 0부터 시작하도록 조정
        if "TimeMin" in df.columns and len(df) > 0:
            df["TimeMin"] = df["TimeMin"] - df["TimeMin"].min()

        return df

    def clear_cache(self) -> None:
        """캐시 초기화 (메모리 해제)"""
        self._raw_data_cache = None

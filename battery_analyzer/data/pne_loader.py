"""PNE cycler data loader."""

import os
from glob import glob

import pandas as pd

from battery_analyzer.config.enums import CyclerType
from battery_analyzer.data.base_loader import BaseDataLoader
from battery_analyzer.utils.parsers import name_capacity


class PNEDataLoader(BaseDataLoader):
    """PNE Restore/SaveData*.csv 로더

    데이터 형식:
        - Restore 폴더: 복원 데이터
        - SaveData{N}.csv: 사이클별 데이터
        - Pattern 폴더: 사이클러 타입 식별용

    컬럼 매핑:
        - TimeMin: 시간 (분)
        - Vol: 전압 (V)
        - Crate: 전류 (C-rate)
        - Temp: 온도 (°C)
        - Profile: 프로파일 번호
    """

    def __init__(self):
        """초기화"""
        super().__init__(CyclerType.PNE)

    def load_cycle(self, data_path: str, cycle_no: int) -> pd.DataFrame:
        """PNE 사이클 데이터 로드

        Args:
            data_path: 데이터 폴더 경로
            cycle_no: 사이클 번호

        Returns:
            pd.DataFrame: 사이클 데이터

        Raises:
            FileNotFoundError: SaveData 파일이 없는 경우
        """
        # SaveData 파일 경로 생성
        savedata_file = os.path.join(data_path, f"SaveData{cycle_no}.csv")

        if not os.path.exists(savedata_file):
            # Restore 폴더에서 시도
            restore_file = os.path.join(data_path, "Restore", f"SaveData{cycle_no}.csv")
            if not os.path.exists(restore_file):
                raise FileNotFoundError(
                    f"SaveData{cycle_no}.csv not found in {data_path} or Restore/"
                )
            savedata_file = restore_file

        # CSV 로드
        df = pd.read_csv(savedata_file, encoding="utf-8")

        # 데이터 검증 및 전처리
        self.validate_data(df)
        df = self.preprocess_data(df)

        return df

    def get_capacity(self, data_path: str, cycle_no: int, c_rate: float) -> float:
        """PNE 용량 추출

        Args:
            data_path: 데이터 폴더 경로
            cycle_no: 사이클 번호
            c_rate: 기준 C-rate

        Returns:
            float: 추출된 용량 (mAh)

        Note:
            1. 파일명에서 용량 추출 시도 (name_capacity)
            2. 실패 시 첫 사이클 방전 용량 사용
        """
        # 1. 파일명에서 용량 추출
        capacity = name_capacity(data_path)
        if capacity is not None:
            return capacity

        # 2. 첫 사이클 방전 용량 사용
        try:
            df = self.load_cycle(data_path, cycle_no)

            # 방전 구간 (Crate < 0)
            discharge = df[df["Crate"] < 0]

            if len(discharge) > 0:
                # 방전 용량 계산 (시간 적분)
                # Capacity (mAh) = abs(Crate) * time_diff (min) * capacity_base
                # 여기서는 최대 방전 전하량 추정
                time_diff = discharge["TimeMin"].diff().fillna(0)
                capacity_mah = abs(discharge["Crate"] * time_diff).sum()

                # C-rate 기준으로 용량 환산
                if capacity_mah > 0:
                    return capacity_mah / abs(discharge["Crate"].mean())

        except FileNotFoundError:
            pass

        # 기본값 반환
        return 58.0  # mAh (기본값)

    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """PNE 데이터 전처리

        Args:
            df: 원본 데이터프레임

        Returns:
            pd.DataFrame: 전처리된 데이터프레임
        """
        # 기본 전처리 호출
        df = super().preprocess_data(df)

        # PNE 특화 전처리
        # (필요 시 추가 처리)

        return df

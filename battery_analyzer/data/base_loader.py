"""Base data loader abstract class."""

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd

from battery_analyzer.config.enums import CyclerType


class BaseDataLoader(ABC):
    """데이터 로더 기본 클래스

    설계:
        - Template Method Pattern
        - 공통 로직은 기본 클래스에서 처리
        - 사이클러별 차이는 서브클래스에서 구현

    Subclasses:
        - PNEDataLoader: PNE Restore/SaveData*.csv
        - ToyoDataLoader: Toyo raw data with Condition-based cycle detection
    """

    def __init__(self, cycler_type: CyclerType):
        """초기화

        Args:
            cycler_type: 사이클러 타입 (PNE | TOYO)
        """
        self.cycler_type = cycler_type

    @abstractmethod
    def load_cycle(self, data_path: str, cycle_no: int) -> pd.DataFrame:
        """단일 사이클 데이터 로드

        Args:
            data_path: 데이터 폴더 경로
            cycle_no: 사이클 번호

        Returns:
            pd.DataFrame: 사이클 데이터

        Raises:
            FileNotFoundError: 사이클 데이터 파일이 없는 경우

        Note:
            서브클래스에서 구현 필요
        """
        pass

    @abstractmethod
    def get_capacity(self, data_path: str, cycle_no: int, c_rate: float) -> float:
        """용량 추출 (자동 감지 모드)

        Args:
            data_path: 데이터 폴더 경로
            cycle_no: 사이클 번호
            c_rate: 기준 C-rate

        Returns:
            float: 추출된 용량 (mAh)

        Note:
            - 파일명에서 용량 추출 시도
            - 실패 시 첫 사이클 방전 용량 사용
        """
        pass

    def validate_data(self, df: pd.DataFrame) -> None:
        """데이터 검증

        Args:
            df: 로드된 데이터프레임

        Raises:
            ValueError: 필수 컬럼이 없는 경우
        """
        required_columns = ["TimeMin", "Vol", "Crate"]
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터 전처리

        Args:
            df: 원본 데이터프레임

        Returns:
            pd.DataFrame: 전처리된 데이터프레임

        Note:
            - 공통 전처리 로직 (정렬, 결측치 처리 등)
            - 서브클래스에서 오버라이드 가능
        """
        # 시간 기준 정렬
        if "TimeMin" in df.columns:
            df = df.sort_values("TimeMin").reset_index(drop=True)

        # 결측치 제거
        df = df.dropna(subset=["Vol", "Crate"])

        return df

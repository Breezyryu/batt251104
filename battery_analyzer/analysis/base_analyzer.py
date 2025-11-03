"""Base analyzer abstract class using Template Method pattern."""

from abc import ABC, abstractmethod
from typing import Dict, Any

import pandas as pd

from battery_analyzer.config.models import AnalysisConfig
from battery_analyzer.data.container import CycleDataContainer


class BaseAnalyzer(ABC):
    """분석기 기본 클래스

    설계:
        - Template Method Pattern
        - 공통 워크플로우: prepare → analyze → postprocess
        - 각 단계별 훅 메서드 제공

    Workflow:
        1. prepare(): 데이터 준비 및 검증
        2. analyze(): 실제 분석 수행 (서브클래스 구현)
        3. postprocess(): 결과 후처리 및 포맷팅

    Subclasses:
        - Cycle: IndividualCycleAnalyzer, LinkedCycleAnalyzer, ReliabilityCycleAnalyzer
        - Profile: StepProfileAnalyzer, RateProfileAnalyzer, ChargeProfileAnalyzer,
                   DischargeProfileAnalyzer, DCIRProfileAnalyzer
    """

    def __init__(self, config: AnalysisConfig, container: CycleDataContainer):
        """초기화

        Args:
            config: 분석 설정
            container: 사이클 데이터 컨테이너
        """
        self.config = config
        self.container = container
        self.results: Dict[str, Any] = {}

    def run(self) -> Dict[str, Any]:
        """분석 실행 (템플릿 메서드)

        Returns:
            Dict[str, Any]: 분석 결과

        Workflow:
            prepare → analyze → postprocess
        """
        # 1. 준비
        self.prepare()

        # 2. 분석
        self.analyze()

        # 3. 후처리
        self.postprocess()

        return self.results

    def prepare(self) -> None:
        """데이터 준비 및 검증 (훅 메서드)

        Note:
            서브클래스에서 오버라이드 가능
        """
        # 설정 검증
        self.config.validate()

        # 컨테이너 검증
        if len(self.container) == 0:
            raise ValueError("Container is empty. Load cycles first.")

    @abstractmethod
    def analyze(self) -> None:
        """실제 분석 수행 (추상 메서드)

        Note:
            서브클래스에서 반드시 구현
            self.results에 결과 저장
        """
        pass

    def postprocess(self) -> None:
        """결과 후처리 (훅 메서드)

        Note:
            서브클래스에서 오버라이드 가능
        """
        # 기본 후처리: 결과 검증
        if not self.results:
            raise ValueError("Analysis produced no results")

    def get_capacity(self, cycle_no: int) -> float:
        """사이클 용량 계산

        Args:
            cycle_no: 사이클 번호

        Returns:
            float: 방전 용량 (mAh)
        """
        df = self.container.get_cycle(cycle_no)

        # 시간 차이 계산
        df = df.copy()
        df["TimeDiff"] = df["TimeMin"].diff().fillna(0)

        # 방전 용량 (Crate < 0)
        discharge = df[df["Crate"] < 0].copy()

        if len(discharge) == 0:
            return 0.0

        # 용량 계산
        if self.config.capacity.mode.value == "manual":
            capacity_base = self.config.capacity.manual_capacity
        else:
            # 자동 감지 모드는 로더에서 처리
            capacity_base = 58.0  # 기본값

        capacity_mah = abs(discharge["Crate"] * discharge["TimeDiff"]).sum() * capacity_base

        return capacity_mah

    def calculate_ir(self, df: pd.DataFrame) -> float:
        """내부 저항 계산 (DCIR)

        Args:
            df: 사이클 데이터

        Returns:
            float: 내부 저항 (mΩ)

        Note:
            전압 변화 / 전류 변화 기반 계산
        """
        # 펄스 구간 감지 (전류가 급격히 변하는 지점)
        df = df.copy()
        df["CurrentDiff"] = df["Crate"].diff().abs()

        # 펄스 시작점 (전류 변화 > 임계값)
        threshold = df["CurrentDiff"].quantile(0.95)
        pulse_points = df[df["CurrentDiff"] > threshold]

        if len(pulse_points) < 2:
            return 0.0

        # 첫 번째 펄스 구간
        pulse_start = pulse_points.index[0]
        pulse_end = min(pulse_start + 10, len(df) - 1)

        # 전압/전류 변화
        v_diff = df.loc[pulse_end, "Vol"] - df.loc[pulse_start, "Vol"]
        i_diff = df.loc[pulse_end, "Crate"] - df.loc[pulse_start, "Crate"]

        if abs(i_diff) < 0.01:
            return 0.0

        # 저항 계산 (mΩ)
        # R = ΔV / ΔI, 단위 조정 필요
        ir = abs(v_diff / i_diff) * 1000  # Ω → mΩ

        return ir

    def __repr__(self) -> str:
        """문자열 표현

        Returns:
            str: 분석기 정보
        """
        return f"{self.__class__.__name__}(config={self.config}, container={self.container})"

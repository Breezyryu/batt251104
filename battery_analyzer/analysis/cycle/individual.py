"""Individual Cycle Analyzer - 개별 사이클 분석."""

from typing import Dict, Any, List
import pandas as pd
import numpy as np

from battery_analyzer.analysis.base_analyzer import BaseAnalyzer
from battery_analyzer.config.models import AnalysisConfig
from battery_analyzer.data.container import CycleDataContainer


class IndividualCycleAnalyzer(BaseAnalyzer):
    """개별 사이클 분석기

    기능:
        - 개별 사이클별 용량/전압/DCIR 분석
        - 6 subplot 출력 구조
        - 사이클 간 비교

    출력 구조:
        1. Discharge Capacity vs Cycle
        2. Charge Capacity vs Cycle
        3. Efficiency vs Cycle
        4. Voltage Profile (Discharge)
        5. Voltage Profile (Charge)
        6. DCIR vs Cycle

    Note:
        원본 BatteryDataTool.py의 indiv_cyc_confirm_button() 기능
    """

    def __init__(self, config: AnalysisConfig, container: CycleDataContainer):
        """초기화

        Args:
            config: 분석 설정 (cycle_numbers 필요)
            container: 사이클 데이터 컨테이너
        """
        super().__init__(config, container)

        if not config.cycle or not config.cycle.cycle_numbers:
            raise ValueError("IndividualCycleAnalyzer requires cycle_numbers in config")

    def analyze(self) -> None:
        """개별 사이클 분석 수행

        결과:
            self.results = {
                'summary': DataFrame (사이클별 요약 통계),
                'voltage_profiles': Dict[int, DataFrame] (사이클별 전압 프로파일),
                'dcir_data': DataFrame (사이클별 DCIR),
            }
        """
        cycle_numbers = self.config.cycle.cycle_numbers

        # 1. 사이클별 요약 통계 계산
        summary_data = []

        for cycle_no in cycle_numbers:
            if not self.container.has_cycle(cycle_no):
                continue

            df = self.container.get_cycle(cycle_no)

            # 용량 계산
            capacity_result = self._calculate_cycle_capacity(df)

            # DCIR 계산
            dcir = self.calculate_ir(df)

            # 요약 저장
            summary_data.append(
                {
                    "Cycle": cycle_no,
                    "Discharge_Capacity": capacity_result["discharge_capacity"],
                    "Charge_Capacity": capacity_result["charge_capacity"],
                    "Efficiency": capacity_result["efficiency"],
                    "DCIR": dcir,
                }
            )

        # DataFrame 생성
        summary_df = pd.DataFrame(summary_data)

        # 2. 전압 프로파일 추출
        voltage_profiles = {}

        for cycle_no in cycle_numbers:
            if not self.container.has_cycle(cycle_no):
                continue

            df = self.container.get_cycle(cycle_no)

            # 방전 프로파일
            discharge = df[df["Crate"] < 0].copy()
            discharge["Capacity_Normalized"] = self._normalize_capacity(discharge)

            # 충전 프로파일
            charge = df[df["Crate"] > 0].copy()
            charge["Capacity_Normalized"] = self._normalize_capacity(charge)

            voltage_profiles[cycle_no] = {
                "discharge": discharge[["TimeMin", "Vol", "Capacity_Normalized"]],
                "charge": charge[["TimeMin", "Vol", "Capacity_Normalized"]],
            }

        # 3. 결과 저장
        self.results = {
            "summary": summary_df,
            "voltage_profiles": voltage_profiles,
            "cycle_numbers": cycle_numbers,
        }

    def _calculate_cycle_capacity(self, df: pd.DataFrame) -> Dict[str, float]:
        """사이클 용량 계산

        Args:
            df: 사이클 데이터

        Returns:
            Dict: discharge_capacity, charge_capacity, efficiency
        """
        df = df.copy()
        df["TimeDiff"] = df["TimeMin"].diff().fillna(0)

        # 용량 기준값
        if self.config.capacity.mode.value == "manual":
            capacity_base = self.config.capacity.manual_capacity
        else:
            capacity_base = 58.0  # 기본값

        # 방전 용량
        discharge = df[df["Crate"] < 0].copy()
        discharge_capacity = (
            abs(discharge["Crate"] * discharge["TimeDiff"]).sum() * capacity_base
        )

        # 충전 용량
        charge = df[df["Crate"] > 0].copy()
        charge_capacity = (charge["Crate"] * charge["TimeDiff"]).sum() * capacity_base

        # 효율
        efficiency = (
            (discharge_capacity / charge_capacity * 100) if charge_capacity > 0 else 0
        )

        return {
            "discharge_capacity": discharge_capacity,
            "charge_capacity": charge_capacity,
            "efficiency": efficiency,
        }

    def _normalize_capacity(self, df: pd.DataFrame) -> pd.Series:
        """용량 정규화 (0-100% SOC)

        Args:
            df: 충전 또는 방전 데이터

        Returns:
            pd.Series: 정규화된 용량 (%)
        """
        if len(df) == 0:
            return pd.Series([], dtype=float)

        df = df.copy()
        df["TimeDiff"] = df["TimeMin"].diff().fillna(0)

        # 누적 용량 계산
        df["Capacity_Cumulative"] = (abs(df["Crate"]) * df["TimeDiff"]).cumsum()

        # 0-100% 정규화
        max_capacity = df["Capacity_Cumulative"].max()
        if max_capacity > 0:
            normalized = (df["Capacity_Cumulative"] / max_capacity) * 100
        else:
            normalized = pd.Series([0] * len(df), index=df.index)

        return normalized

    def postprocess(self) -> None:
        """후처리: 통계 계산 및 검증

        추가 계산:
            - 평균 용량
            - 용량 감소율
            - DCIR 평균/표준편차
        """
        super().postprocess()

        summary_df = self.results["summary"]

        # 통계 계산
        stats = {
            "mean_discharge_capacity": summary_df["Discharge_Capacity"].mean(),
            "mean_charge_capacity": summary_df["Charge_Capacity"].mean(),
            "mean_efficiency": summary_df["Efficiency"].mean(),
            "mean_dcir": summary_df["DCIR"].mean(),
            "std_dcir": summary_df["DCIR"].std(),
        }

        # 용량 감소율 (첫 사이클 대비)
        if len(summary_df) > 1:
            first_capacity = summary_df.iloc[0]["Discharge_Capacity"]
            last_capacity = summary_df.iloc[-1]["Discharge_Capacity"]
            fade_rate = (
                ((first_capacity - last_capacity) / first_capacity * 100)
                if first_capacity > 0
                else 0
            )
            stats["capacity_fade_rate"] = fade_rate

        self.results["statistics"] = stats

    def get_summary_table(self) -> pd.DataFrame:
        """요약 테이블 가져오기

        Returns:
            pd.DataFrame: 사이클별 요약 통계
        """
        return self.results.get("summary", pd.DataFrame())

    def get_voltage_profile(self, cycle_no: int, profile_type: str = "discharge") -> pd.DataFrame:
        """전압 프로파일 가져오기

        Args:
            cycle_no: 사이클 번호
            profile_type: "discharge" 또는 "charge"

        Returns:
            pd.DataFrame: 전압 프로파일 데이터
        """
        voltage_profiles = self.results.get("voltage_profiles", {})

        if cycle_no not in voltage_profiles:
            raise KeyError(f"Cycle {cycle_no} not found in results")

        if profile_type not in ["discharge", "charge"]:
            raise ValueError("profile_type must be 'discharge' or 'charge'")

        return voltage_profiles[cycle_no][profile_type]

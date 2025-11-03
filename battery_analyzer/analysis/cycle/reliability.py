"""Reliability Cycle Analyzer - 신뢰성 사이클 분석."""

from typing import Dict, Any, List
import pandas as pd
import numpy as np
from scipy import stats

from battery_analyzer.analysis.base_analyzer import BaseAnalyzer
from battery_analyzer.config.models import AnalysisConfig
from battery_analyzer.data.container import CycleDataContainer


class ReliabilityCycleAnalyzer(BaseAnalyzer):
    """신뢰성 사이클 분석기

    기능:
        - 장기 사이클 수명 평가
        - 용량 감소 추세 분석
        - 통계적 신뢰성 지표 계산

    분석 항목:
        1. Capacity Fade (용량 감소율)
        2. Cycle Life (수명 예측)
        3. Degradation Rate (열화 속도)
        4. Statistical Metrics (평균, 표준편차, 신뢰구간)

    출력 구조:
        - Capacity fade curve
        - Statistical summary
        - Reliability metrics

    Note:
        원본 BatteryDataTool.py의 reliability cycle 분석 기능
        장기 수명 데이터 분석에 최적화
    """

    def __init__(self, config: AnalysisConfig, container: CycleDataContainer):
        """초기화

        Args:
            config: 분석 설정
            container: 사이클 데이터 컨테이너
        """
        super().__init__(config, container)

    def analyze(self) -> None:
        """신뢰성 사이클 분석 수행

        결과:
            self.results = {
                'capacity_data': DataFrame (사이클별 용량 데이터),
                'fade_analysis': Dict (용량 감소 분석),
                'statistical_metrics': Dict (통계 지표),
                'lifecycle_prediction': Dict (수명 예측),
            }
        """
        # 사이클 범위 결정
        if self.config.cycle and self.config.cycle.cycle_numbers:
            cycle_numbers = self.config.cycle.cycle_numbers
        else:
            # 전체 로드된 사이클 사용
            cycle_numbers = self.container.get_loaded_cycle_numbers()

        # 1. 사이클별 용량 데이터 수집
        capacity_data = []

        for cycle_no in cycle_numbers:
            if not self.container.has_cycle(cycle_no):
                continue

            df = self.container.get_cycle(cycle_no)

            # 용량 계산
            capacity_result = self._calculate_cycle_capacity(df)

            capacity_data.append(
                {
                    "Cycle": cycle_no,
                    "Discharge_Capacity": capacity_result["discharge_capacity"],
                    "Charge_Capacity": capacity_result["charge_capacity"],
                    "Efficiency": capacity_result["efficiency"],
                }
            )

        capacity_df = pd.DataFrame(capacity_data)

        # 2. 용량 감소 분석
        fade_analysis = self._analyze_capacity_fade(capacity_df)

        # 3. 통계 지표 계산
        statistical_metrics = self._calculate_statistical_metrics(capacity_df)

        # 4. 수명 예측
        lifecycle_prediction = self._predict_lifecycle(capacity_df, fade_analysis)

        # 결과 저장
        self.results = {
            "capacity_data": capacity_df,
            "fade_analysis": fade_analysis,
            "statistical_metrics": statistical_metrics,
            "lifecycle_prediction": lifecycle_prediction,
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
            capacity_base = 58.0

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

    def _analyze_capacity_fade(self, capacity_df: pd.DataFrame) -> Dict[str, Any]:
        """용량 감소 분석

        Args:
            capacity_df: 용량 데이터

        Returns:
            Dict: 용량 감소 분석 결과
        """
        if len(capacity_df) < 2:
            return {
                "initial_capacity": 0,
                "final_capacity": 0,
                "absolute_fade": 0,
                "relative_fade": 0,
                "fade_per_cycle": 0,
            }

        # 초기/최종 용량
        initial_capacity = capacity_df.iloc[0]["Discharge_Capacity"]
        final_capacity = capacity_df.iloc[-1]["Discharge_Capacity"]

        # 절대 감소량
        absolute_fade = initial_capacity - final_capacity

        # 상대 감소율 (%)
        relative_fade = (
            (absolute_fade / initial_capacity * 100) if initial_capacity > 0 else 0
        )

        # 사이클당 감소율
        cycle_count = len(capacity_df)
        fade_per_cycle = relative_fade / cycle_count if cycle_count > 0 else 0

        # 선형 회귀 (용량 vs 사이클)
        x = capacity_df["Cycle"].values
        y = capacity_df["Discharge_Capacity"].values

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        return {
            "initial_capacity": initial_capacity,
            "final_capacity": final_capacity,
            "absolute_fade": absolute_fade,
            "relative_fade": relative_fade,
            "fade_per_cycle": fade_per_cycle,
            "linear_slope": slope,
            "r_squared": r_value**2,
            "p_value": p_value,
        }

    def _calculate_statistical_metrics(self, capacity_df: pd.DataFrame) -> Dict[str, Any]:
        """통계 지표 계산

        Args:
            capacity_df: 용량 데이터

        Returns:
            Dict: 통계 지표
        """
        discharge_capacities = capacity_df["Discharge_Capacity"].values
        efficiencies = capacity_df["Efficiency"].values

        # 기본 통계
        metrics = {
            "capacity_mean": np.mean(discharge_capacities),
            "capacity_std": np.std(discharge_capacities),
            "capacity_min": np.min(discharge_capacities),
            "capacity_max": np.max(discharge_capacities),
            "capacity_cv": (
                (np.std(discharge_capacities) / np.mean(discharge_capacities) * 100)
                if np.mean(discharge_capacities) > 0
                else 0
            ),
            "efficiency_mean": np.mean(efficiencies),
            "efficiency_std": np.std(efficiencies),
        }

        # 95% 신뢰구간
        if len(discharge_capacities) > 1:
            confidence_interval = stats.t.interval(
                0.95,
                len(discharge_capacities) - 1,
                loc=np.mean(discharge_capacities),
                scale=stats.sem(discharge_capacities),
            )
            metrics["capacity_ci_lower"] = confidence_interval[0]
            metrics["capacity_ci_upper"] = confidence_interval[1]

        return metrics

    def _predict_lifecycle(
        self, capacity_df: pd.DataFrame, fade_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """수명 예측

        Args:
            capacity_df: 용량 데이터
            fade_analysis: 용량 감소 분석 결과

        Returns:
            Dict: 수명 예측 결과

        Note:
            80% 용량 유지 기준 (End of Life)
        """
        initial_capacity = fade_analysis["initial_capacity"]
        linear_slope = fade_analysis["linear_slope"]

        if initial_capacity <= 0 or linear_slope >= 0:
            return {
                "eol_capacity": 0,
                "predicted_eol_cycle": 0,
                "remaining_cycles": 0,
            }

        # EOL 용량 (80% 기준)
        eol_capacity = initial_capacity * 0.8

        # 선형 추세로 EOL 사이클 예측
        # eol_capacity = initial_capacity + slope * cycle
        # cycle = (eol_capacity - initial_capacity) / slope
        predicted_eol_cycle = int(
            (eol_capacity - initial_capacity) / linear_slope
        )

        # 현재 사이클
        current_cycle = capacity_df.iloc[-1]["Cycle"]

        # 남은 사이클
        remaining_cycles = max(0, predicted_eol_cycle - current_cycle)

        return {
            "eol_capacity": eol_capacity,
            "predicted_eol_cycle": predicted_eol_cycle,
            "current_cycle": current_cycle,
            "remaining_cycles": remaining_cycles,
        }

    def postprocess(self) -> None:
        """후처리: 신뢰성 등급 평가"""
        super().postprocess()

        fade_analysis = self.results["fade_analysis"]
        statistical_metrics = self.results["statistical_metrics"]

        # 신뢰성 등급 평가
        relative_fade = fade_analysis["relative_fade"]
        capacity_cv = statistical_metrics["capacity_cv"]

        # 등급 기준
        if relative_fade < 5 and capacity_cv < 2:
            grade = "Excellent"
        elif relative_fade < 10 and capacity_cv < 5:
            grade = "Good"
        elif relative_fade < 20 and capacity_cv < 10:
            grade = "Fair"
        else:
            grade = "Poor"

        self.results["reliability_grade"] = grade

    def get_capacity_fade_curve(self) -> pd.DataFrame:
        """용량 감소 곡선 데이터

        Returns:
            pd.DataFrame: Cycle, Discharge_Capacity, Normalized_Capacity
        """
        capacity_df = self.results.get("capacity_data", pd.DataFrame())

        if len(capacity_df) == 0:
            return pd.DataFrame()

        # 정규화된 용량 추가 (초기 용량 대비 %)
        initial_capacity = capacity_df.iloc[0]["Discharge_Capacity"]
        capacity_df["Normalized_Capacity"] = (
            (capacity_df["Discharge_Capacity"] / initial_capacity * 100)
            if initial_capacity > 0
            else 0
        )

        return capacity_df[["Cycle", "Discharge_Capacity", "Normalized_Capacity"]]

    def get_summary_report(self) -> str:
        """신뢰성 분석 요약 보고서

        Returns:
            str: 요약 보고서 텍스트
        """
        fade = self.results["fade_analysis"]
        stats = self.results["statistical_metrics"]
        lifecycle = self.results["lifecycle_prediction"]
        grade = self.results.get("reliability_grade", "Unknown")

        report = f"""
=== Reliability Analysis Report ===

Capacity Fade:
  - Initial Capacity: {fade['initial_capacity']:.2f} mAh
  - Final Capacity: {fade['final_capacity']:.2f} mAh
  - Relative Fade: {fade['relative_fade']:.2f} %
  - Fade per Cycle: {fade['fade_per_cycle']:.4f} %/cycle

Statistical Metrics:
  - Mean Capacity: {stats['capacity_mean']:.2f} mAh
  - Std Dev: {stats['capacity_std']:.2f} mAh
  - Coefficient of Variation: {stats['capacity_cv']:.2f} %
  - Mean Efficiency: {stats['efficiency_mean']:.2f} %

Lifecycle Prediction:
  - EOL Capacity (80%): {lifecycle['eol_capacity']:.2f} mAh
  - Predicted EOL Cycle: {lifecycle['predicted_eol_cycle']}
  - Current Cycle: {lifecycle['current_cycle']}
  - Remaining Cycles: {lifecycle['remaining_cycles']}

Reliability Grade: {grade}
"""
        return report

"""Linked Cycle Analyzer - 연결 사이클 분석."""

from typing import Dict, Any, List
import pandas as pd
import numpy as np

from battery_analyzer.analysis.base_analyzer import BaseAnalyzer
from battery_analyzer.config.models import AnalysisConfig
from battery_analyzer.data.container import CycleDataContainer


class LinkedCycleAnalyzer(BaseAnalyzer):
    """연결 사이클 분석기

    기능:
        - 여러 경로의 사이클 데이터 연결 분석
        - TSV 파일 기반 경로 연결
        - 사이클 번호 누적 처리

    데이터 구조:
        - 외부 루프: 경로 (폴더)
        - 내부 루프: 사이클
        - 사이클 번호 연속성 유지

    출력 구조:
        - 6 subplot (개별 사이클과 동일)
        - 경로별 탭 구분
        - Excel: 누적 방식 (row 0부터 순차 추가)

    Note:
        원본 BatteryDataTool.py의 link_cyc_indiv_confirm_button() 기능
        TSV 형식: cyclepath | cyclename
    """

    def __init__(self, config: AnalysisConfig, containers: Dict[str, CycleDataContainer]):
        """초기화

        Args:
            config: 분석 설정 (TSV 파일 필요)
            containers: 경로별 CycleDataContainer 딕셔너리
                       {path: container}
        """
        # 첫 번째 컨테이너를 기본으로 설정 (BaseAnalyzer 요구사항)
        first_container = next(iter(containers.values()))
        super().__init__(config, first_container)

        self.containers = containers

        if not config.path.use_tsv or not config.path.tsv_file:
            raise ValueError("LinkedCycleAnalyzer requires TSV file in config")

    def prepare(self) -> None:
        """데이터 준비: TSV 파일 로드 및 검증"""
        super().prepare()

        # TSV 파일 로드
        try:
            self.tsv_data = pd.read_csv(
                self.config.path.tsv_file, sep="\t", encoding="utf-8"
            )
        except FileNotFoundError:
            raise FileNotFoundError(f"TSV file not found: {self.config.path.tsv_file}")

        # 필수 컬럼 확인
        required_columns = ["cyclepath", "cyclename"]
        missing_columns = [
            col for col in required_columns if col not in self.tsv_data.columns
        ]

        if missing_columns:
            raise ValueError(f"Missing columns in TSV: {missing_columns}")

    def analyze(self) -> None:
        """연결 사이클 분석 수행

        결과:
            self.results = {
                'summary': DataFrame (전체 경로 누적 통계),
                'path_summaries': Dict[str, DataFrame] (경로별 요약),
                'voltage_profiles': Dict (경로 → 사이클 → 프로파일),
            }
        """
        all_summary_data = []
        path_summaries = {}
        voltage_profiles = {}

        cumulative_cycle_offset = 0  # 사이클 번호 누적 오프셋

        # TSV 파일 기반 경로 순회
        for idx, row in self.tsv_data.iterrows():
            cyclepath = row["cyclepath"]
            cyclename = row["cyclename"]

            if cyclepath not in self.containers:
                print(f"Warning: Path not found in containers: {cyclepath}")
                continue

            container = self.containers[cyclepath]

            # 경로별 사이클 분석
            path_summary = []
            path_profiles = {}

            loaded_cycles = container.get_loaded_cycle_numbers()

            for local_cycle_no in loaded_cycles:
                df = container.get_cycle(local_cycle_no)

                # 용량 계산
                capacity_result = self._calculate_cycle_capacity(df)

                # DCIR 계산
                dcir = self.calculate_ir(df)

                # 누적 사이클 번호
                global_cycle_no = cumulative_cycle_offset + local_cycle_no

                # 요약 데이터
                summary_row = {
                    "Path": cyclepath,
                    "Path_Name": cyclename,
                    "Local_Cycle": local_cycle_no,
                    "Global_Cycle": global_cycle_no,
                    "Discharge_Capacity": capacity_result["discharge_capacity"],
                    "Charge_Capacity": capacity_result["charge_capacity"],
                    "Efficiency": capacity_result["efficiency"],
                    "DCIR": dcir,
                }

                path_summary.append(summary_row)
                all_summary_data.append(summary_row)

                # 전압 프로파일
                discharge = df[df["Crate"] < 0].copy()
                discharge["Capacity_Normalized"] = self._normalize_capacity(discharge)

                charge = df[df["Crate"] > 0].copy()
                charge["Capacity_Normalized"] = self._normalize_capacity(charge)

                path_profiles[local_cycle_no] = {
                    "discharge": discharge[["TimeMin", "Vol", "Capacity_Normalized"]],
                    "charge": charge[["TimeMin", "Vol", "Capacity_Normalized"]],
                }

            # 경로별 요약 저장
            path_summaries[cyclepath] = pd.DataFrame(path_summary)
            voltage_profiles[cyclepath] = path_profiles

            # 다음 경로를 위한 오프셋 업데이트
            if loaded_cycles:
                cumulative_cycle_offset = max(
                    cumulative_cycle_offset, max(loaded_cycles)
                )

        # 전체 요약 DataFrame
        summary_df = pd.DataFrame(all_summary_data)

        # 결과 저장
        self.results = {
            "summary": summary_df,
            "path_summaries": path_summaries,
            "voltage_profiles": voltage_profiles,
            "tsv_data": self.tsv_data,
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
        """후처리: 경로별 및 전체 통계 계산"""
        super().postprocess()

        summary_df = self.results["summary"]

        # 전체 통계
        stats = {
            "total_paths": len(self.tsv_data),
            "total_cycles": len(summary_df),
            "mean_discharge_capacity": summary_df["Discharge_Capacity"].mean(),
            "mean_efficiency": summary_df["Efficiency"].mean(),
            "mean_dcir": summary_df["DCIR"].mean(),
        }

        # 경로별 통계
        path_stats = {}
        for path, path_df in self.results["path_summaries"].items():
            path_stats[path] = {
                "cycle_count": len(path_df),
                "mean_discharge_capacity": path_df["Discharge_Capacity"].mean(),
                "mean_efficiency": path_df["Efficiency"].mean(),
            }

        self.results["statistics"] = stats
        self.results["path_statistics"] = path_stats

    def get_path_summary(self, path: str) -> pd.DataFrame:
        """경로별 요약 가져오기

        Args:
            path: 경로

        Returns:
            pd.DataFrame: 경로별 요약 통계
        """
        path_summaries = self.results.get("path_summaries", {})

        if path not in path_summaries:
            raise KeyError(f"Path not found: {path}")

        return path_summaries[path]

    def get_cumulative_summary(self) -> pd.DataFrame:
        """누적 요약 테이블 (Excel 출력용)

        Returns:
            pd.DataFrame: Global_Cycle 기준 정렬된 전체 요약
        """
        summary_df = self.results.get("summary", pd.DataFrame())
        return summary_df.sort_values("Global_Cycle").reset_index(drop=True)

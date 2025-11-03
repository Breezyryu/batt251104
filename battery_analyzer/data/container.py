"""Cycle data container for efficient O(1) lookup."""

from typing import Dict, List

import pandas as pd


class CycleDataContainer:
    """전체 사이클 1회 로드 후 O(1) 필터링

    설계 철학:
        - 파일 I/O는 최초 1회만 수행
        - 메모리에 전체 사이클 저장
        - 사이클 번호로 O(1) 접근

    Attributes:
        _cycles: 사이클 번호 → DataFrame 매핑
        _metadata: 데이터 메타정보 (용량, 경로 등)

    Performance:
        - Load time: O(n) where n = total cycles
        - Lookup time: O(1) per cycle
        - Memory: ~25x improvement over repeated file I/O

    Examples:
        >>> container = CycleDataContainer()
        >>> container.load_all_cycles("/path/to/data", loader)
        >>> df = container.get_cycle(5)  # O(1)
        >>> df_range = container.get_cycle_range(3, 5)  # O(k) where k=3
    """

    def __init__(self):
        """초기화"""
        self._cycles: Dict[int, pd.DataFrame] = {}
        self._metadata: Dict[str, any] = {}

    def load_all_cycles(
        self, data_path: str, loader: "BaseDataLoader", cycle_range: tuple = None
    ) -> None:
        """전체 사이클 로드

        Args:
            data_path: 데이터 폴더 경로
            loader: 데이터 로더 인스턴스 (PNEDataLoader | ToyoDataLoader)
            cycle_range: 로드할 사이클 범위 (start, end), None이면 전체

        Raises:
            FileNotFoundError: 데이터 파일이 없는 경우
        """
        # 사이클 범위 결정
        if cycle_range is None:
            from battery_analyzer.utils.parsers import get_all_cycles

            cycle_range = get_all_cycles(data_path)

        start, end = cycle_range

        # 전체 사이클 로드
        for cycle_no in range(start, end + 1):
            try:
                df = loader.load_cycle(data_path, cycle_no)
                self._cycles[cycle_no] = df
            except FileNotFoundError:
                # 일부 사이클이 없을 수 있음 (예: 중간 사이클 누락)
                continue

        # 메타데이터 저장
        self._metadata["data_path"] = data_path
        self._metadata["cycle_range"] = (start, end)
        self._metadata["loaded_cycles"] = list(self._cycles.keys())

    def get_cycle(self, cycle_no: int) -> pd.DataFrame:
        """특정 사이클 데이터 가져오기 (O(1))

        Args:
            cycle_no: 사이클 번호

        Returns:
            pd.DataFrame: 사이클 데이터

        Raises:
            KeyError: 사이클이 로드되지 않은 경우
        """
        if cycle_no not in self._cycles:
            raise KeyError(f"Cycle {cycle_no} not found in container")

        return self._cycles[cycle_no].copy()

    def get_cycle_range(self, start: int, end: int) -> pd.DataFrame:
        """사이클 범위 데이터 병합 (O(k) where k=end-start)

        Args:
            start: 시작 사이클
            end: 종료 사이클 (포함)

        Returns:
            pd.DataFrame: 병합된 데이터 (시간 연속성 유지)

        Note:
            - 연속 범위 처리 시 시간 축 연속성 보정 필요
            - DCIR, Profile Continue 기능에서 사용
        """
        dfs = []
        cumulative_time = 0

        for cycle_no in range(start, end + 1):
            if cycle_no not in self._cycles:
                continue

            df = self._cycles[cycle_no].copy()

            # 시간 축 연속성 보정
            if "TimeMin" in df.columns and cumulative_time > 0:
                df["TimeMin"] = df["TimeMin"] + cumulative_time

            dfs.append(df)

            # 다음 사이클을 위한 누적 시간 업데이트
            if "TimeMin" in df.columns:
                cumulative_time = df["TimeMin"].max()

        if not dfs:
            raise ValueError(f"No cycles found in range {start}-{end}")

        # 모든 사이클 병합
        merged_df = pd.concat(dfs, ignore_index=True)

        return merged_df

    def get_cycles(self, cycle_list: List[int]) -> Dict[int, pd.DataFrame]:
        """개별 사이클 리스트 가져오기 (O(k) where k=len(cycle_list))

        Args:
            cycle_list: 사이클 번호 리스트 (예: [2, 3, 4, 8, 9])

        Returns:
            Dict[int, pd.DataFrame]: 사이클 번호 → DataFrame 매핑

        Raises:
            KeyError: 일부 사이클이 로드되지 않은 경우
        """
        result = {}
        missing_cycles = []

        for cycle_no in cycle_list:
            if cycle_no in self._cycles:
                result[cycle_no] = self._cycles[cycle_no].copy()
            else:
                missing_cycles.append(cycle_no)

        if missing_cycles:
            raise KeyError(f"Cycles not found: {missing_cycles}")

        return result

    def has_cycle(self, cycle_no: int) -> bool:
        """사이클 존재 여부 확인

        Args:
            cycle_no: 사이클 번호

        Returns:
            bool: 존재 여부
        """
        return cycle_no in self._cycles

    def get_metadata(self) -> Dict[str, any]:
        """메타데이터 가져오기

        Returns:
            Dict: 메타데이터 (data_path, cycle_range, loaded_cycles 등)
        """
        return self._metadata.copy()

    def get_loaded_cycle_numbers(self) -> List[int]:
        """로드된 사이클 번호 리스트

        Returns:
            List[int]: 사이클 번호 리스트 (정렬됨)
        """
        return sorted(self._cycles.keys())

    def clear(self) -> None:
        """컨테이너 초기화 (메모리 해제)"""
        self._cycles.clear()
        self._metadata.clear()

    def __len__(self) -> int:
        """로드된 사이클 개수

        Returns:
            int: 사이클 개수
        """
        return len(self._cycles)

    def __repr__(self) -> str:
        """문자열 표현

        Returns:
            str: 컨테이너 정보
        """
        cycle_range = self._metadata.get("cycle_range", "Unknown")
        loaded_count = len(self._cycles)
        return f"CycleDataContainer(range={cycle_range}, loaded={loaded_count} cycles)"

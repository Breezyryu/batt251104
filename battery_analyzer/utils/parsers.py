"""Parsing utility functions for cycle numbers and paths."""

import os
import re
from glob import glob
from typing import List, Tuple

from battery_analyzer.config.enums import CyclerType


def convert_steplist(stepnum: str) -> List[int]:
    """개별 사이클 번호 리스트 변환

    Args:
        stepnum: 사이클 입력 문자열 (예: "3 4 5 8-9")

    Returns:
        List[int]: 확장된 사이클 번호 리스트
        예: "3 4 5 8-9" → [3, 4, 5, 8, 9]

    Examples:
        >>> convert_steplist("3 4 5")
        [3, 4, 5]
        >>> convert_steplist("8-9")
        [8, 9]
        >>> convert_steplist("3 4 5 8-9")
        [3, 4, 5, 8, 9]
    """
    steplist = []
    for step in stepnum.split():
        if "-" in step:
            start, end = map(int, step.split("-"))
            steplist.extend(range(start, end + 1))
        else:
            steplist.append(int(step))

    return steplist


def parse_cycle_range(cycle_input: str) -> Tuple[int, int]:
    """연속 사이클 범위 파싱 (시작/종료 값 반환)

    Args:
        cycle_input: 범위 형식 문자열 (예: "3-5")

    Returns:
        tuple: (Step_CycNo, Step_CycEnd) - (시작 사이클, 종료 사이클)
        예: "3-5" → (3, 5)

    Raises:
        ValueError: 범위 형식이 아닌 경우

    사용처:
        - DCIR 연속 범위 처리
        - Profile Continue 기능
        - 연속 데이터 병합 처리

    Examples:
        >>> parse_cycle_range("3-5")
        (3, 5)
        >>> parse_cycle_range("1-100")
        (1, 100)
    """
    if "-" not in cycle_input:
        raise ValueError(f"Range format required (e.g., '3-5'), got: {cycle_input}")

    cycle_range = cycle_input.strip()
    Step_CycNo, Step_CycEnd = map(int, cycle_range.split("-"))

    return Step_CycNo, Step_CycEnd


def get_all_cycles(data_path: str) -> Tuple[int, int]:
    """데이터 경로의 전체 사이클 범위 자동 감지

    Args:
        data_path: 배터리 데이터 폴더 경로

    Returns:
        tuple: (Step_CycNo, Step_CycEnd) - (첫 사이클, 마지막 사이클)
        예: 데이터에 사이클 1~100이 있으면 → (1, 100)

    사용처:
        - 전체 사이클 로딩 (사용자 입력 불필요)
        - 전체 데이터 분석 및 통계
        - 초기 데이터 로드 시 범위 확인

    Raises:
        FileNotFoundError: 데이터 파일이 없는 경우
        ValueError: 사이클 정보를 추출할 수 없는 경우

    Examples:
        >>> get_all_cycles("/path/to/pne/data")
        (1, 100)
        >>> get_all_cycles("/path/to/toyo/data")
        (1, 50)
    """
    # 사이클러 타입 감지
    cycler_type = check_cycler(data_path)

    if cycler_type == CyclerType.PNE:
        # PNE: SaveData*.csv 파일 번호로 사이클 범위 추출
        # 예: SaveData1.csv ~ SaveData100.csv
        savedata_files = glob(os.path.join(data_path, "SaveData*.csv"))
        if not savedata_files:
            raise FileNotFoundError(f"No SaveData*.csv files found in {data_path}")

        # 파일명에서 숫자 추출
        cycle_numbers = []
        for file in savedata_files:
            basename = os.path.basename(file)  # SaveData100.csv
            match = re.search(r"SaveData(\d+)\.csv", basename)
            if match:
                cycle_numbers.append(int(match.group(1)))

        if not cycle_numbers:
            raise ValueError(f"No cycle numbers found in SaveData files at {data_path}")

        Step_CycNo = min(cycle_numbers)
        Step_CycEnd = max(cycle_numbers)

    else:
        # Toyo: Raw data의 Condition 컬럼으로 사이클 범위 추출
        import pandas as pd

        # Toyo raw data 파일 찾기 (일반적으로 .csv 또는 .txt)
        raw_files = glob(os.path.join(data_path, "*.csv")) + glob(
            os.path.join(data_path, "*.txt")
        )

        if not raw_files:
            raise FileNotFoundError(f"No raw data files found in {data_path}")

        # 첫 번째 파일에서 Condition 컬럼 읽기
        df = pd.read_csv(raw_files[0], sep="\t", encoding="shift_jis", low_memory=False)

        if "Condition" not in df.columns:
            raise ValueError(f"'Condition' column not found in {raw_files[0]}")

        # Condition 컬럼에서 사이클 번호 추출 (예: "Cycle 1", "Cycle 2", ...)
        conditions = df["Condition"].dropna().unique()
        cycle_numbers = []
        for cond in conditions:
            match = re.search(r"Cycle\s+(\d+)", str(cond), re.IGNORECASE)
            if match:
                cycle_numbers.append(int(match.group(1)))

        if not cycle_numbers:
            raise ValueError(f"No cycle numbers found in Condition column at {data_path}")

        Step_CycNo = min(cycle_numbers)
        Step_CycEnd = max(cycle_numbers)

    return Step_CycNo, Step_CycEnd


def name_capacity(filepath: str) -> float:
    """파일명에서 용량 추출

    Args:
        filepath: 파일 경로

    Returns:
        float: 추출된 용량 (mAh), 없으면 None

    Examples:
        >>> name_capacity("Battery_58mAh.csv")
        58.0
        >>> name_capacity("Test_4-5mAh.csv")
        4.5
        >>> name_capacity("Cell_3.2mAh.csv")
        3.2
    """
    # 정규식 패턴: (\d+([-.]\d+)?)mAh
    match = re.search(r"(\d+([-.]\d+)?)mAh", filepath)
    if match:
        capacity_str = match.group(1).replace("-", ".")
        return float(capacity_str)
    else:
        return None


def check_cycler(cyclefolder: str) -> CyclerType:
    """사이클러 타입 자동 감지

    Args:
        cyclefolder: 사이클 데이터 폴더 경로

    Returns:
        CyclerType: PNE 또는 TOYO

    Examples:
        >>> check_cycler("/path/to/pne/data")
        <CyclerType.PNE: 'pne'>
        >>> check_cycler("/path/to/toyo/data")
        <CyclerType.TOYO: 'toyo'>
    """
    # "Pattern" 폴더 존재 여부로 판단
    pattern_path = os.path.join(cyclefolder, "Pattern")

    if os.path.exists(pattern_path):
        return CyclerType.PNE
    else:
        return CyclerType.TOYO

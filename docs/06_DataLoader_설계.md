# Data Loader 상세 설계

## 개요

**전체 사이클 1회 로드 후 필터링 구조**를 핵심으로 하는 Data Loader 시스템의 상세 설계 문서입니다.
PNE/Toyo 사이클러별 데이터 로딩 전략과 CycleDataContainer의 구현 방안을 제시합니다.

---

## 설계 목표

### 1. 성능 최적화
- **1회 로드**: 전체 사이클 데이터를 한 번에 메모리로 로드
- **빠른 필터링**: 사이클 번호별 O(1) 접근
- **메모리 효율**: 필요한 데이터만 캐싱

### 2. 확장성
- **사이클러 타입 추가 용이**: 새로운 사이클러 지원 시 BaseDataLoader만 상속
- **데이터 형식 독립**: 내부 데이터 구조는 pandas DataFrame으로 통일

### 3. 사용 편의성
- **자동 감지**: 경로에서 사이클러 타입 자동 판별
- **유연한 조회**: 단일/범위/리스트 등 다양한 방식 지원

---

## CycleDataContainer 상세 설계

### 클래스 다이어그램

```
┌─────────────────────────────────────────────────┐
│            CycleDataContainer                   │
├─────────────────────────────────────────────────┤
│ - _all_cycles: Dict[int, DataFrame]             │
│ - _metadata: Dict[str, Any]                     │
│ - _channels: List[str]                          │
│ - _path: str                                    │
│ - _cycler_type: str                             │
├─────────────────────────────────────────────────┤
│ + add_cycle(cycle_no, data)                     │
│ + get_cycle(cycle_no) -> DataFrame              │
│ + get_cycle_range(start, end) -> DataFrame      │
│ + get_cycles(cycle_list) -> Dict                │
│ + list_available_cycles() -> List[int]          │
│ + set_metadata(key, value)                      │
│ + get_metadata(key) -> Any                      │
│ + capacity: float                               │
│ + channels: List[str]                           │
│ + cycler_type: str                              │
└─────────────────────────────────────────────────┘
```

### 구현 코드

```python
# data/data_container.py

from typing import Dict, List, Optional, Union
import pandas as pd
from pathlib import Path

class CycleDataContainer:
    """
    전체 사이클 데이터 컨테이너

    Purpose:
        - 1회 로드한 전체 사이클 데이터를 메모리에 캐싱
        - 빠른 사이클 조회 및 필터링
        - 메타데이터 관리

    Usage:
        container = CycleDataContainer()
        container.add_cycle(1, cycle1_df)
        container.add_cycle(2, cycle2_df)

        # 단일 조회
        cycle1 = container.get_cycle(1)

        # 범위 조회
        cycles_1_to_10 = container.get_cycle_range(1, 10)

        # 리스트 조회
        selected = container.get_cycles([1, 5, 10])
    """

    def __init__(self, path: Optional[str] = None):
        self._all_cycles: Dict[int, pd.DataFrame] = {}
        self._metadata: Dict[str, any] = {}
        self._channels: List[str] = []
        self._path = path
        self._cycler_type = None

    def add_cycle(self, cycle_no: int, data: pd.DataFrame):
        """
        사이클 데이터 추가

        Args:
            cycle_no: 사이클 번호 (1-based)
            data: 사이클 데이터 (pandas DataFrame)

        Raises:
            ValueError: 이미 존재하는 사이클 번호
        """
        if cycle_no in self._all_cycles:
            raise ValueError(f"Cycle {cycle_no} already exists")

        self._all_cycles[cycle_no] = data

    def get_cycle(self, cycle_no: int) -> pd.DataFrame:
        """
        단일 사이클 데이터 조회

        Args:
            cycle_no: 조회할 사이클 번호

        Returns:
            사이클 데이터 (DataFrame)

        Raises:
            KeyError: 존재하지 않는 사이클 번호
        """
        if cycle_no not in self._all_cycles:
            available = self.list_available_cycles()
            raise KeyError(
                f"Cycle {cycle_no} not found. "
                f"Available cycles: {available}"
            )

        return self._all_cycles[cycle_no].copy()

    def get_cycle_range(self, start: int, end: int) -> pd.DataFrame:
        """
        사이클 범위 데이터 조회 및 병합

        Args:
            start: 시작 사이클 번호 (inclusive)
            end: 종료 사이클 번호 (inclusive)

        Returns:
            병합된 DataFrame (index는 연속적으로 재설정)

        Raises:
            ValueError: 범위 내 사이클이 없음
        """
        if start > end:
            raise ValueError(f"Invalid range: {start} > {end}")

        dfs = []
        for cycle_no in range(start, end + 1):
            if cycle_no in self._all_cycles:
                dfs.append(self._all_cycles[cycle_no])

        if not dfs:
            raise ValueError(
                f"No cycles found in range {start}-{end}. "
                f"Available: {self.list_available_cycles()}"
            )

        # 연속 데이터로 병합
        merged = pd.concat(dfs, ignore_index=True)
        return merged

    def get_cycles(self, cycle_list: List[int]) -> Dict[int, pd.DataFrame]:
        """
        여러 사이클 데이터 조회 (개별)

        Args:
            cycle_list: 조회할 사이클 번호 리스트

        Returns:
            {cycle_no: DataFrame} 딕셔너리
        """
        result = {}
        for cycle_no in cycle_list:
            if cycle_no in self._all_cycles:
                result[cycle_no] = self._all_cycles[cycle_no].copy()

        return result

    def list_available_cycles(self) -> List[int]:
        """사용 가능한 사이클 번호 리스트 (정렬)"""
        return sorted(self._all_cycles.keys())

    def set_metadata(self, key: str, value: any):
        """메타데이터 설정"""
        self._metadata[key] = value

    def get_metadata(self, key: str, default: any = None) -> any:
        """메타데이터 조회"""
        return self._metadata.get(key, default)

    @property
    def capacity(self) -> float:
        """배터리 용량 (mAh)"""
        return self._metadata.get('capacity', 0.0)

    @capacity.setter
    def capacity(self, value: float):
        """배터리 용량 설정"""
        self._metadata['capacity'] = value

    @property
    def channels(self) -> List[str]:
        """채널 리스트"""
        return self._channels

    @channels.setter
    def channels(self, value: List[str]):
        """채널 리스트 설정"""
        self._channels = value

    @property
    def cycler_type(self) -> str:
        """사이클러 타입 (pne/toyo)"""
        return self._cycler_type

    @cycler_type.setter
    def cycler_type(self, value: str):
        """사이클러 타입 설정"""
        if value not in ['pne', 'toyo']:
            raise ValueError(f"Invalid cycler type: {value}")
        self._cycler_type = value

    @property
    def path(self) -> str:
        """데이터 경로"""
        return self._path

    def __len__(self) -> int:
        """전체 사이클 개수"""
        return len(self._all_cycles)

    def __repr__(self) -> str:
        return (
            f"CycleDataContainer("
            f"cycles={len(self)}, "
            f"capacity={self.capacity}mAh, "
            f"type={self.cycler_type})"
        )
```

---

## BaseDataLoader 상세 설계

### 추상 기본 클래스

```python
# data/data_loader_base.py

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import re

class BaseDataLoader(ABC):
    """
    데이터 로더 추상 기본 클래스

    Responsibilities:
        1. 전체 사이클 데이터 로드
        2. 사이클러 타입 감지
        3. 용량 추출 (파일명 또는 첫 사이클)
        4. 메타데이터 수집

    Subclass Requirements:
        - load_all_cycles() 구현 필수
        - detect_cycler_type() static method 구현 필수
    """

    @abstractmethod
    def load_all_cycles(
        self,
        path: str,
        config: 'CapacityConfig'
    ) -> CycleDataContainer:
        """
        전체 사이클 데이터 일괄 로드

        Args:
            path: 데이터 폴더 경로
            config: 용량 설정

        Returns:
            CycleDataContainer with all cycles loaded

        Implementation Guide:
            1. 용량 추출 (self._extract_capacity)
            2. 사이클 파일들 찾기
            3. 각 사이클 파싱
            4. CycleDataContainer에 추가
            5. 메타데이터 설정
        """
        pass

    @staticmethod
    @abstractmethod
    def detect_cycler_type(path: str) -> bool:
        """
        사이클러 타입 감지

        Args:
            path: 데이터 폴더 경로

        Returns:
            True if this loader can handle the path
        """
        pass

    def _extract_capacity(
        self,
        filepath: str,
        config: 'CapacityConfig'
    ) -> float:
        """
        용량 추출 (우선순위: 수동 > 파일명 > 첫 사이클)

        Args:
            filepath: 파일 경로
            config: 용량 설정

        Returns:
            용량 (mAh)
        """
        from config.analysis_config import CapacityMode

        # 1. 수동 입력
        if config.mode == CapacityMode.MANUAL:
            return config.manual_capacity

        # 2. 파일명에서 추출
        capacity = self._parse_capacity_from_filename(filepath)
        if capacity:
            return capacity

        # 3. 첫 사이클 데이터에서 계산
        return self._calculate_capacity_from_first_cycle(
            filepath,
            config.c_rate
        )

    @staticmethod
    def _parse_capacity_from_filename(filepath: str) -> Optional[float]:
        """
        파일명에서 용량 파싱

        Pattern: XXXmAh (예: 58mAh, 4500mAh, 3.2mAh)

        Args:
            filepath: 파일 경로 또는 파일명

        Returns:
            용량 (mAh) or None
        """
        # 정규식: 숫자 + 옵션(. 또는 - + 숫자) + mAh
        match = re.search(r'(\d+([-.]\d+)?)mAh', filepath)
        if match:
            capacity_str = match.group(1).replace('-', '.')
            return float(capacity_str)
        return None

    @abstractmethod
    def _calculate_capacity_from_first_cycle(
        self,
        filepath: str,
        c_rate: float
    ) -> float:
        """
        첫 사이클 데이터에서 용량 계산

        Args:
            filepath: 데이터 경로
            c_rate: 기준 C-rate

        Returns:
            계산된 용량 (mAh)

        Note:
            Subclass에서 사이클러별로 구현
        """
        pass
```

---

## PNEDataLoader 상세 설계

### PNE 데이터 구조

```
PNE 폴더 구조:
project_folder/
├── Pattern/                    # PNE 식별자
├── Restore/
│   ├── SaveData001.csv        # Cycle 1
│   ├── SaveData002.csv        # Cycle 2
│   ├── SaveData003.csv        # Cycle 3
│   └── ...
└── ...

SaveData CSV 구조:
- 컬럼: [Time, Step, Cycle, Voltage, Current, Capacity, ...]
- 각 파일은 하나의 사이클 데이터
```

### 구현 코드

```python
# data/pne_loader.py

from glob import glob
from pathlib import Path
import pandas as pd
import re

class PNEDataLoader(BaseDataLoader):
    """
    PNE 사이클러 데이터 로더

    Data Structure:
        - Restore/SaveDataXXX.csv: 각 사이클 데이터
        - Pattern/ 폴더 존재: PNE 식별자

    Features:
        - SaveData 파일 번호로 사이클 번호 자동 추출
        - PNE CSV 형식 파싱
    """

    def load_all_cycles(
        self,
        path: str,
        config: 'CapacityConfig'
    ) -> CycleDataContainer:
        """PNE Restore 폴더에서 모든 SaveData*.csv 로드"""

        container = CycleDataContainer(path=path)
        container.cycler_type = "pne"

        # 용량 추출
        capacity = self._extract_capacity(path, config)
        container.capacity = capacity

        # Restore 폴더 경로
        restore_path = Path(path) / "Restore"
        if not restore_path.exists():
            raise FileNotFoundError(
                f"PNE Restore folder not found: {restore_path}"
            )

        # 모든 SaveData 파일 찾기
        cycle_files = sorted(restore_path.glob("SaveData*.csv"))

        if not cycle_files:
            raise ValueError(f"No SaveData files found in {restore_path}")

        # 각 사이클 로드
        for file in cycle_files:
            cycle_no = self._extract_cycle_number(file.name)
            df = self._parse_pne_cycle(file)
            container.add_cycle(cycle_no, df)

        # 메타데이터
        container.set_metadata('num_cycles', len(cycle_files))
        container.set_metadata('c_rate', config.c_rate)

        return container

    def _extract_cycle_number(self, filename: str) -> int:
        """
        파일명에서 사이클 번호 추출

        Pattern: SaveDataXXX.csv → XXX (int)

        Examples:
            SaveData001.csv → 1
            SaveData042.csv → 42
        """
        match = re.search(r'SaveData(\d+)\.csv', filename)
        if not match:
            raise ValueError(f"Invalid PNE cycle filename: {filename}")

        return int(match.group(1))

    def _parse_pne_cycle(self, filepath: Path) -> pd.DataFrame:
        """
        PNE CSV 파일 파싱

        Args:
            filepath: SaveData*.csv 파일 경로

        Returns:
            파싱된 DataFrame

        Processing:
            1. CSV 읽기
            2. 컬럼 정리 (필요 시)
            3. 데이터 타입 변환
            4. 계산 컬럼 추가 (필요 시)
        """
        # CSV 읽기 (인코딩 주의)
        try:
            df = pd.read_csv(filepath, encoding='utf-8')
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, encoding='cp949')  # Windows 한글

        # 컬럼 정리 (원본 컬럼명 유지 또는 표준화)
        # df = self._normalize_columns(df)

        # 데이터 타입 변환
        # df = df.astype({'Voltage': float, 'Current': float, ...})

        return df

    def _calculate_capacity_from_first_cycle(
        self,
        filepath: str,
        c_rate: float
    ) -> float:
        """
        첫 사이클의 방전 용량에서 계산

        Logic:
            - SaveData001.csv 읽기
            - 방전 구간 찾기 (Current < 0)
            - 최대 방전 용량 추출
        """
        first_cycle = Path(filepath) / "Restore" / "SaveData001.csv"

        if not first_cycle.exists():
            raise FileNotFoundError(f"First cycle file not found: {first_cycle}")

        df = pd.read_csv(first_cycle)

        # 방전 용량 추출 (컬럼명은 실제에 맞게 조정)
        if 'Discharge_Capacity' in df.columns:
            capacity = df['Discharge_Capacity'].max()
        elif 'Capacity' in df.columns:
            # 방전 구간만 필터링
            discharge_mask = df['Current'] < 0
            capacity = df.loc[discharge_mask, 'Capacity'].max()
        else:
            raise ValueError("Cannot find capacity column in PNE data")

        return capacity

    @staticmethod
    def detect_cycler_type(path: str) -> bool:
        """Pattern 폴더 존재 여부로 PNE 판별"""
        pattern_path = Path(path) / "Pattern"
        return pattern_path.exists()
```

---

## ToyoDataLoader 상세 설계

### Toyo 데이터 구조

```
Toyo 폴더 구조:
project_folder/
├── raw_data.csv              # 전체 데이터 (모든 사이클 포함)
└── ...

Raw data CSV 구조:
- 컬럼: [Time, Condition, Voltage, Current, Capacity, ...]
- Condition: 0=휴지, 1=충전, 2=방전
- 모든 사이클이 하나의 파일에 연속적으로 저장
```

### 구현 코드

```python
# data/toyo_loader.py

from pathlib import Path
import pandas as pd
from typing import Dict, Tuple

class ToyoDataLoader(BaseDataLoader):
    """
    Toyo 사이클러 데이터 로더

    Data Structure:
        - 모든 사이클이 하나의 raw data 파일에 저장
        - Condition 변화로 사이클 경계 감지

    Features:
        - Condition 기반 사이클 자동 분할
        - 시간 기반 누적 용량 계산
    """

    def load_all_cycles(
        self,
        path: str,
        config: 'CapacityConfig'
    ) -> CycleDataContainer:
        """Toyo raw data에서 전체 로드 및 사이클 분할"""

        container = CycleDataContainer(path=path)
        container.cycler_type = "toyo"

        # 용량 추출
        capacity = self._extract_capacity(path, config)
        container.capacity = capacity

        # Raw data 파일 로드
        raw_data = self._load_toyo_raw(path)

        # Condition 기반 사이클 분할
        cycle_boundaries = self._detect_cycle_boundaries(raw_data)

        # 각 사이클 데이터 추출
        for cycle_no, (start_idx, end_idx) in cycle_boundaries.items():
            cycle_df = raw_data.iloc[start_idx:end_idx + 1].copy()
            cycle_df.reset_index(drop=True, inplace=True)
            container.add_cycle(cycle_no, cycle_df)

        # 메타데이터
        container.set_metadata('num_cycles', len(cycle_boundaries))
        container.set_metadata('c_rate', config.c_rate)

        return container

    def _load_toyo_raw(self, path: str) -> pd.DataFrame:
        """
        Toyo raw data 파일 로드

        Note:
            실제 Toyo 파일명 확인 필요
            (현재는 raw_data.csv로 가정)
        """
        # 가능한 파일명들
        possible_files = [
            "raw_data.csv",
            "data.csv",
            "toyo_data.csv"
        ]

        for filename in possible_files:
            filepath = Path(path) / filename
            if filepath.exists():
                try:
                    df = pd.read_csv(filepath, encoding='utf-8')
                    return df
                except UnicodeDecodeError:
                    df = pd.read_csv(filepath, encoding='cp949')
                    return df

        # 폴더 내 첫 번째 CSV 파일 사용
        csv_files = list(Path(path).glob("*.csv"))
        if csv_files:
            return pd.read_csv(csv_files[0])

        raise FileNotFoundError(f"No Toyo data file found in {path}")

    def _detect_cycle_boundaries(
        self,
        raw_data: pd.DataFrame
    ) -> Dict[int, Tuple[int, int]]:
        """
        Condition 변화 기반 사이클 경계 감지

        Logic:
            - 사이클 시작: Condition 0(휴지) → 1(충전) 전환
            - 사이클 종료: 다음 사이클 시작 직전 또는 데이터 끝

        Args:
            raw_data: 전체 raw DataFrame

        Returns:
            {cycle_no: (start_idx, end_idx)} 딕셔너리
        """
        boundaries = {}
        cycle_no = 1
        start_idx = 0

        # Condition 변화 감지
        condition_col = raw_data['Condition']

        for idx in range(1, len(raw_data)):
            prev_condition = condition_col.iloc[idx - 1]
            curr_condition = condition_col.iloc[idx]

            # 휴지 → 충전 전환 (새 사이클 시작)
            if prev_condition == 0 and curr_condition == 1:
                # 이전 사이클 저장
                if start_idx < idx - 1:
                    boundaries[cycle_no] = (start_idx, idx - 1)
                    cycle_no += 1

                # 새 사이클 시작
                start_idx = idx

        # 마지막 사이클
        if start_idx < len(raw_data):
            boundaries[cycle_no] = (start_idx, len(raw_data) - 1)

        return boundaries

    def _calculate_capacity_from_first_cycle(
        self,
        filepath: str,
        c_rate: float
    ) -> float:
        """
        첫 사이클의 방전 용량에서 계산

        Logic:
            - Raw data 로드
            - 첫 사이클 추출
            - 방전 구간 (Condition == 2) 최대 용량
        """
        raw_data = self._load_toyo_raw(filepath)
        cycle_boundaries = self._detect_cycle_boundaries(raw_data)

        if not cycle_boundaries:
            raise ValueError("No cycles detected in Toyo data")

        # 첫 사이클 데이터
        start, end = cycle_boundaries[1]
        first_cycle = raw_data.iloc[start:end + 1]

        # 방전 구간 최대 용량
        discharge_mask = first_cycle['Condition'] == 2
        capacity = first_cycle.loc[discharge_mask, 'Capacity'].max()

        return capacity

    @staticmethod
    def detect_cycler_type(path: str) -> bool:
        """Pattern 폴더 없으면 Toyo"""
        pattern_path = Path(path) / "Pattern"
        return not pattern_path.exists()
```

---

## DataLoaderFactory 상세 설계

```python
# data/__init__.py

class DataLoaderFactory:
    """
    사이클러 타입별 로더 자동 생성 팩토리

    Strategy:
        1. PNEDataLoader.detect_cycler_type() 확인
        2. True면 PNEDataLoader 반환
        3. False면 ToyoDataLoader 반환
    """

    _loaders = [PNEDataLoader, ToyoDataLoader]

    @classmethod
    def create_loader(cls, path: str) -> BaseDataLoader:
        """
        경로에서 사이클러 타입 감지 후 적절한 로더 반환

        Args:
            path: 데이터 폴더 경로

        Returns:
            BaseDataLoader 인스턴스

        Raises:
            ValueError: 알 수 없는 사이클러 타입
        """
        for loader_class in cls._loaders:
            if loader_class.detect_cycler_type(path):
                return loader_class()

        raise ValueError(
            f"Unknown cycler type for path: {path}\n"
            f"Checked: {[l.__name__ for l in cls._loaders]}"
        )

    @classmethod
    def register_loader(cls, loader_class: type):
        """
        새로운 로더 클래스 등록

        Usage:
            class CustomLoader(BaseDataLoader):
                ...

            DataLoaderFactory.register_loader(CustomLoader)
        """
        if not issubclass(loader_class, BaseDataLoader):
            raise TypeError(
                f"{loader_class} must inherit from BaseDataLoader"
            )

        cls._loaders.append(loader_class)
```

---

## 사용 워크플로우

### 전체 흐름

```python
# 1. 설정 생성
config = AnalysisConfig(
    path=PathConfig(paths=["Rawdata/test_data"]),
    capacity=CapacityConfig(mode=CapacityMode.AUTO_CRATE, c_rate=0.2)
)

# 2. 로더 생성 (자동 감지)
loader = DataLoaderFactory.create_loader(config.path.paths[0])
# → PNEDataLoader 또는 ToyoDataLoader

# 3. 전체 사이클 로드 (1회)
container = loader.load_all_cycles(
    path=config.path.paths[0],
    config=config.capacity
)
# → CycleDataContainer with all cycles

# 4. 사이클 조회 (빠른 필터링)
cycle_1 = container.get_cycle(1)
cycles_1_to_10 = container.get_cycle_range(1, 10)
selected = container.get_cycles([1, 5, 10, 20])

# 5. 메타데이터 확인
print(f"Capacity: {container.capacity} mAh")
print(f"Cycler: {container.cycler_type}")
print(f"Available cycles: {container.list_available_cycles()}")
```

---

## 성능 분석

### 로딩 시간 비교

**기존 방식 (매번 로드)**:
```
분석 요청 1: 사이클 1, 2, 3 → 3개 파일 로드
분석 요청 2: 사이클 5, 10 → 2개 파일 로드
분석 요청 3: 사이클 1-20 → 20개 파일 로드

총 로드 횟수: 25회
```

**새로운 방식 (1회 로드)**:
```
초기 로드: 모든 사이클 → 1회 전체 로드
분석 요청 1: 사이클 1, 2, 3 → 메모리 조회 (O(1))
분석 요청 2: 사이클 5, 10 → 메모리 조회 (O(1))
분석 요청 3: 사이클 1-20 → 메모리 조회 및 병합

총 로드 횟수: 1회
성능 향상: ~25배
```

### 메모리 사용량

**예상 메모리 사용** (100 사이클, 각 1MB):
```
전체 로드: ~100MB
컨테이너 오버헤드: ~10MB
총: ~110MB (현대 시스템에서 충분히 감당 가능)
```

---

## 크로스체크 검증 항목

### Data Loader 검증

#### PNEDataLoader
- [ ] SaveData 파일 자동 탐색: 모든 파일 발견
- [ ] 사이클 번호 추출: SaveData001 → 1 정확
- [ ] CSV 파싱: 원본과 동일한 DataFrame
- [ ] 용량 추출 (파일명): name_capacity() 결과 일치
- [ ] 용량 추출 (첫 사이클): 계산 결과 일치

#### ToyoDataLoader
- [ ] Raw data 로드: 전체 데이터 읽기 성공
- [ ] 사이클 경계 감지: Condition 기반 분할 정확
- [ ] 사이클 개수: 원본과 동일
- [ ] 각 사이클 데이터: 원본과 동일한 범위

#### CycleDataContainer
- [ ] 단일 조회: get_cycle() 정확
- [ ] 범위 조회: get_cycle_range() 병합 정확
- [ ] 리스트 조회: get_cycles() 정확
- [ ] 메타데이터: capacity, cycler_type 정확

---

## 확장 가능성

### 새로운 사이클러 추가

```python
# 새로운 사이클러 (예: CustomCycler) 추가

class CustomDataLoader(BaseDataLoader):
    """Custom 사이클러 로더"""

    def load_all_cycles(self, path, config):
        container = CycleDataContainer(path=path)
        container.cycler_type = "custom"

        # Custom 로직
        # ...

        return container

    @staticmethod
    def detect_cycler_type(path):
        # Custom 식별 로직
        custom_marker = Path(path) / "custom.dat"
        return custom_marker.exists()

# 팩토리에 등록
DataLoaderFactory.register_loader(CustomDataLoader)

# 이후 자동으로 사용 가능
loader = DataLoaderFactory.create_loader("path/to/custom/data")
```

---

## 결론

### 핵심 포인트
1. **CycleDataContainer**: 전체 사이클 1회 로드 후 O(1) 조회
2. **BaseDataLoader**: 확장 가능한 추상 클래스
3. **PNE/ToyoDataLoader**: 사이클러별 특화 구현
4. **DataLoaderFactory**: 자동 감지 및 로더 생성
5. **성능**: 기존 대비 ~25배 빠른 조회 속도

### 다음 단계
- 확장 기능 설계 (Toyo DCIR, Profile 연속성)
- 실제 코드 구현
- 크로스체크 검증

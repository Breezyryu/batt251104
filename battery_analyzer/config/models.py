"""Configuration dataclass models."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from battery_analyzer.config.enums import CapacityMode, DCIRMode, ProfileLayout


@dataclass
class PathConfig:
    """경로 설정

    Attributes:
        use_tsv: TSV 파일 사용 여부 (기본: True)
        tsv_file: TSV 파일 경로
        manual_paths: 수동 입력 경로 리스트
        folder_paths: 폴더 선택 경로 리스트
    """
    use_tsv: bool = True
    tsv_file: Optional[str] = None
    manual_paths: Optional[List[str]] = None
    folder_paths: Optional[List[str]] = None


@dataclass
class CapacityConfig:
    """용량 설정

    Attributes:
        mode: 용량 설정 모드 (AUTO_CRATE | MANUAL)
        c_rate: C-rate 기준값 (기본: 0.2)
        manual_capacity: 수동 입력 용량 (mAh, 기본: 58.0)
    """
    mode: CapacityMode = CapacityMode.AUTO_CRATE
    c_rate: float = 0.2
    manual_capacity: float = 58.0


@dataclass
class CycleConfig:
    """Cycle 분석 설정

    Attributes:
        cycle_numbers: 개별 사이클 번호 리스트 (예: [2, 3, 4, 8, 9])
        cycle_range: 연속 사이클 범위 (start, end) - DCIR/Continue용
        x_max: X축 최대값 (0=자동, 기본: 0)
        y_max: Y축 용량 비율 최대값 (기본: 1.10)
        y_min: Y축 용량 비율 최소값 (기본: 0.65)
        dcir_mode: DCIR 측정 모드 (기본: RSS)
        dcir_scale: DCIR 스케일 배율 (0=자동, 기본: 0)
    """
    cycle_numbers: Optional[List[int]] = None
    cycle_range: Optional[Tuple[int, int]] = None
    x_max: float = 0
    y_max: float = 1.10
    y_min: float = 0.65
    dcir_mode: DCIRMode = DCIRMode.RSS
    dcir_scale: float = 0


@dataclass
class ProfileConfig:
    """Profile 분석 설정

    Attributes:
        cycle_numbers: 개별 사이클 번호 리스트
        cycle_range: 연속 사이클 범위 (start, end)
        layout: 그래프 레이아웃 (BY_CYCLE | BY_CELL)
        voltage_min: 전압 Y축 최소값 (V, 기본: 2.5)
        voltage_max: 전압 Y축 최대값 (V, 기본: 4.7)
        voltage_gap: 전압 Y축 눈금 간격 (V, 기본: 0.1)
        smoothing: Smoothing 차수 (0=자동, 기본: 0)
        cutoff_crate: Cutoff C-rate 임계값 (기본: 0)
        dqdv_scale: dQ/dV 축 스케일 배율 (기본: 1.0)
        swap_dqdv_axes: dQ/dV X/Y축 교환 여부 (기본: False)
    """
    cycle_numbers: Optional[List[int]] = None
    cycle_range: Optional[Tuple[int, int]] = None
    layout: ProfileLayout = ProfileLayout.BY_CYCLE
    voltage_min: float = 2.5
    voltage_max: float = 4.7
    voltage_gap: float = 0.1
    smoothing: int = 0
    cutoff_crate: float = 0
    dqdv_scale: float = 1.0
    swap_dqdv_axes: bool = False


@dataclass
class ExportConfig:
    """내보내기 설정

    Attributes:
        save_excel: Excel 저장 여부 (기본: False)
        save_ect: ECT CSV 저장 여부 (기본: False)
        save_figure: 그래프 이미지 저장 여부 (기본: False)
        excel_filename: Excel 파일 경로
        ect_filename: ECT CSV 파일 경로
        figure_filename: 그래프 이미지 파일 경로
    """
    save_excel: bool = False
    save_ect: bool = False
    save_figure: bool = False
    excel_filename: Optional[str] = None
    ect_filename: Optional[str] = None
    figure_filename: Optional[str] = None


@dataclass
class AnalysisConfig:
    """전체 분석 설정 통합

    Attributes:
        path: 경로 설정
        capacity: 용량 설정
        cycle: Cycle 분석 설정 (옵션)
        profile: Profile 분석 설정 (옵션)
        export: 내보내기 설정
    """
    path: PathConfig
    capacity: CapacityConfig
    cycle: Optional[CycleConfig] = None
    profile: Optional[ProfileConfig] = None
    export: ExportConfig = field(default_factory=ExportConfig)

    def validate(self) -> None:
        """설정 검증

        Raises:
            ValueError: 설정이 유효하지 않은 경우
        """
        # 경로 검증
        if self.path.use_tsv and not self.path.tsv_file:
            raise ValueError("TSV 모드 활성화 시 TSV 파일 필요")

        # 용량 검증
        if self.capacity.mode == CapacityMode.AUTO_CRATE:
            if self.capacity.c_rate <= 0:
                raise ValueError("C-rate는 0보다 커야 함")
        elif self.capacity.mode == CapacityMode.MANUAL:
            if self.capacity.manual_capacity <= 0:
                raise ValueError("용량은 0보다 커야 함")

        # Cycle 사이클 번호 검증
        if self.cycle:
            if self.cycle.cycle_numbers:
                if not all(c > 0 for c in self.cycle.cycle_numbers):
                    raise ValueError("사이클 번호는 양수여야 함")
            if self.cycle.cycle_range:
                start, end = self.cycle.cycle_range
                if start <= 0 or end <= 0 or start > end:
                    raise ValueError("사이클 범위가 유효하지 않음")

        # Profile 파라미터 검증
        if self.profile:
            if self.profile.voltage_min >= self.profile.voltage_max:
                raise ValueError("전압 최소값이 최대값보다 작아야 함")
            if self.profile.cycle_numbers:
                if not all(c > 0 for c in self.profile.cycle_numbers):
                    raise ValueError("사이클 번호는 양수여야 함")
            if self.profile.cycle_range:
                start, end = self.profile.cycle_range
                if start <= 0 or end <= 0 or start > end:
                    raise ValueError("사이클 범위가 유효하지 않음")

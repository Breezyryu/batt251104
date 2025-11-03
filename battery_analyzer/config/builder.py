"""Configuration builder for converting GUI inputs to config objects."""

from typing import Any

from battery_analyzer.config.enums import CapacityMode, DCIRMode, ProfileLayout
from battery_analyzer.config.models import (
    AnalysisConfig,
    CapacityConfig,
    CycleConfig,
    ExportConfig,
    PathConfig,
    ProfileConfig,
)
from battery_analyzer.utils.parsers import convert_steplist, parse_cycle_range


class AnalysisConfigBuilder:
    """설정 빌더 - GUI 또는 딕셔너리에서 설정 생성

    Usage:
        >>> builder = AnalysisConfigBuilder()
        >>> config = (builder
        ...     .from_gui_widgets(gui)
        ...     .with_cycle_config(gui)
        ...     .build())
    """

    def __init__(self):
        """초기화"""
        self.config = AnalysisConfig(
            path=PathConfig(),
            capacity=CapacityConfig(),
            export=ExportConfig(),
        )

    def from_gui_widgets(self, gui: Any) -> "AnalysisConfigBuilder":
        """GUI 위젯에서 기본 설정 생성

        Args:
            gui: GUI 객체 (PyQt6 위젯 포함)

        Returns:
            AnalysisConfigBuilder: 빌더 인스턴스 (체이닝용)
        """
        # 경로 설정
        self.config.path = PathConfig(
            use_tsv=gui.chk_cyclepath.isChecked(),
            tsv_file=self._get_tsv_file(gui) if gui.chk_cyclepath.isChecked() else None,
            manual_paths=(
                gui.stepnum_2.toPlainText().split("\n")
                if gui.stepnum_2.toPlainText()
                else None
            ),
        )

        # 용량 설정
        if gui.inicaprate.isChecked():
            self.config.capacity = CapacityConfig(
                mode=CapacityMode.AUTO_CRATE, c_rate=float(gui.ratetext.text())
            )
        else:
            self.config.capacity = CapacityConfig(
                mode=CapacityMode.MANUAL,
                manual_capacity=float(gui.capacitytext.text()),
            )

        # 내보내기 설정
        self.config.export = ExportConfig(
            save_excel=gui.saveok.isChecked(),
            save_ect=gui.ect_saveok.isChecked(),
            save_figure=gui.figsaveok.isChecked(),
        )

        return self

    def with_cycle_config(self, gui: Any) -> "AnalysisConfigBuilder":
        """Cycle 분석 설정 추가

        Args:
            gui: GUI 객체

        Returns:
            AnalysisConfigBuilder: 빌더 인스턴스
        """
        # DCIR 모드 선택
        dcir_mode = DCIRMode.RSS
        if gui.dcirchk.isChecked():
            dcir_mode = DCIRMode.STANDARD
        elif gui.pulsedcir.isChecked():
            dcir_mode = DCIRMode.PULSE

        # 사이클 번호 파싱
        cycle_input = gui.stepnum.toPlainText()
        if "-" in cycle_input and " " not in cycle_input:
            # 연속 범위 (예: "3-5")
            cycle_range = parse_cycle_range(cycle_input)
            cycle_numbers = None
        else:
            # 개별 사이클 (예: "3 4 5 8-9")
            cycle_range = None
            cycle_numbers = convert_steplist(cycle_input)

        self.config.cycle = CycleConfig(
            cycle_numbers=cycle_numbers,
            cycle_range=cycle_range,
            x_max=float(gui.tcyclerng.text()),
            y_max=float(gui.tcyclerngyhl.text()),
            y_min=float(gui.tcyclerngyll.text()),
            dcir_mode=dcir_mode,
            dcir_scale=float(gui.dcirscale.text()),
        )

        return self

    def with_profile_config(self, gui: Any) -> "AnalysisConfigBuilder":
        """Profile 분석 설정 추가

        Args:
            gui: GUI 객체

        Returns:
            AnalysisConfigBuilder: 빌더 인스턴스
        """
        # 레이아웃 선택
        layout = (
            ProfileLayout.BY_CYCLE
            if gui.CycProfile.isChecked()
            else ProfileLayout.BY_CELL
        )

        # 사이클 번호 파싱
        cycle_input = gui.stepnum.toPlainText()
        if "-" in cycle_input and " " not in cycle_input:
            # 연속 범위
            cycle_range = parse_cycle_range(cycle_input)
            cycle_numbers = None
        else:
            # 개별 사이클
            cycle_range = None
            cycle_numbers = convert_steplist(cycle_input)

        self.config.profile = ProfileConfig(
            cycle_numbers=cycle_numbers,
            cycle_range=cycle_range,
            layout=layout,
            voltage_min=float(gui.volrngyhl.text()),
            voltage_max=float(gui.volrngyll.text()),
            voltage_gap=float(gui.volrnggap.text()),
            smoothing=int(gui.smooth.text()),
            cutoff_crate=float(gui.cutoff.text()),
            dqdv_scale=float(gui.dqdvscale.text()),
            swap_dqdv_axes=gui.chk_dqdv.isChecked(),
        )

        return self

    def build(self) -> AnalysisConfig:
        """설정 빌드 및 검증

        Returns:
            AnalysisConfig: 검증된 설정 객체

        Raises:
            ValueError: 설정이 유효하지 않은 경우
        """
        self.config.validate()
        return self.config

    @staticmethod
    def _get_tsv_file(gui: Any) -> str:
        """TSV 파일 경로 가져오기 (헬퍼 메서드)

        Args:
            gui: GUI 객체

        Returns:
            str: TSV 파일 경로
        """
        # GUI에서 TSV 파일 선택 다이얼로그 호출
        # 실제 구현은 GUI 프레임워크에 따라 달라짐
        return ""  # Placeholder

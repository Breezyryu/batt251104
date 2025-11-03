"""Enumeration types for configuration."""

from enum import Enum


class CapacityMode(Enum):
    """용량 설정 모드"""
    AUTO_CRATE = "auto_crate"  # C-rate 기반 자동 감지
    MANUAL = "manual"  # 수동 입력


class DCIRMode(Enum):
    """DCIR 측정 모드"""
    STANDARD = "standard"  # SOC100 10s 방전 펄스
    PULSE = "pulse"  # SOC5, 50 10s 방전 펄스
    RSS = "rss"  # SOC 30/50/70 충/방전 1s 펄스/RSS (기본값)


class ProfileLayout(Enum):
    """Profile 그래프 레이아웃"""
    BY_CYCLE = "by_cycle"  # 사이클 통합 (기본값)
    BY_CELL = "by_cell"  # 셀별 통합


class CyclerType(Enum):
    """사이클러 타입"""
    PNE = "pne"  # PNE Restore/SaveData*.csv
    TOYO = "toyo"  # Toyo raw data

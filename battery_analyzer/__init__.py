"""
Battery Data Analyzer
=====================

Compact battery test data analysis tool extracted from BatteryDataTool.py.

Modules:
    - config: Configuration dataclasses and enums
    - data: Data loading and container classes
    - analysis: Analysis strategies for Cycle and Profile
    - visualization: Graph generation
    - export: Excel, ECT, and figure export
    - extensions: Toyo DCIR and continuous profile support
    - utils: Utility functions
"""

__version__ = "1.0.0"
__author__ = "Battery Analysis Team"

from battery_analyzer.config import (
    AnalysisConfig,
    PathConfig,
    CapacityConfig,
    CycleConfig,
    ProfileConfig,
    ExportConfig,
    CapacityMode,
    DCIRMode,
    ProfileLayout,
)

__all__ = [
    "AnalysisConfig",
    "PathConfig",
    "CapacityConfig",
    "CycleConfig",
    "ProfileConfig",
    "ExportConfig",
    "CapacityMode",
    "DCIRMode",
    "ProfileLayout",
]

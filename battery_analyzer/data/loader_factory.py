"""Data loader factory for automatic cycler detection."""

from battery_analyzer.config.enums import CyclerType
from battery_analyzer.data.base_loader import BaseDataLoader
from battery_analyzer.data.pne_loader import PNEDataLoader
from battery_analyzer.data.toyo_loader import ToyoDataLoader
from battery_analyzer.utils.parsers import check_cycler


class DataLoaderFactory:
    """데이터 로더 팩토리

    설계:
        - Factory Pattern
        - 사이클러 타입 자동 감지
        - 적절한 로더 인스턴스 생성

    Usage:
        >>> loader = DataLoaderFactory.create_loader("/path/to/data")
        >>> df = loader.load_cycle("/path/to/data", 1)
    """

    @staticmethod
    def create_loader(data_path: str) -> BaseDataLoader:
        """데이터 로더 생성

        Args:
            data_path: 데이터 폴더 경로

        Returns:
            BaseDataLoader: PNEDataLoader 또는 ToyoDataLoader

        Examples:
            >>> loader = DataLoaderFactory.create_loader("/path/to/pne/data")
            >>> isinstance(loader, PNEDataLoader)
            True
            >>> loader = DataLoaderFactory.create_loader("/path/to/toyo/data")
            >>> isinstance(loader, ToyoDataLoader)
            True
        """
        # 사이클러 타입 감지
        cycler_type = check_cycler(data_path)

        # 로더 생성
        if cycler_type == CyclerType.PNE:
            return PNEDataLoader()
        elif cycler_type == CyclerType.TOYO:
            return ToyoDataLoader()
        else:
            raise ValueError(f"Unknown cycler type: {cycler_type}")

    @staticmethod
    def create_loader_by_type(cycler_type: CyclerType) -> BaseDataLoader:
        """사이클러 타입으로 로더 생성

        Args:
            cycler_type: 사이클러 타입 (PNE | TOYO)

        Returns:
            BaseDataLoader: 해당 로더 인스턴스

        Raises:
            ValueError: 알 수 없는 사이클러 타입
        """
        if cycler_type == CyclerType.PNE:
            return PNEDataLoader()
        elif cycler_type == CyclerType.TOYO:
            return ToyoDataLoader()
        else:
            raise ValueError(f"Unknown cycler type: {cycler_type}")

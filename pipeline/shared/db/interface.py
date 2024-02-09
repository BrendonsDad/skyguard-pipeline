from abc import ABCMeta, abstractmethod
from typing import Iterable, Set, Sequence

from shared.util import check_methods
from shared.struct import Asset


class DBInterface(metaclass=ABCMeta):
    """Interface for database interaction"""

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool:
        return check_methods(cls, subclass)

    @abstractmethod
    def __init__(self) -> None:
        """Initialize the DB"""
        raise NotImplementedError

    @abstractmethod
    def get_asset_by_name(self, name: str) -> Asset:
        """Get an Asset object"""
        raise NotImplementedError

    @abstractmethod
    def get_assets_by_name(self, names: Iterable[str]) -> Set[Asset]:
        """Get multiple Asset objects"""
        raise NotImplementedError

    @abstractmethod
    def get_asset_name_list(self) -> Sequence[str]:
        """Get a list of Asset ids"""
        raise NotImplementedError
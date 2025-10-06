from typing import Protocol

from src.domain.value_objects.company import Company


class CompanyQueryPort(Protocol):
    """
    Query port.

    """

    def __init__(self): ...

    def get(self) -> list[Company]: ...

from typing import Protocol

from src.domain.value_objects.company import Company


class CompanyCommandPort(Protocol):
    """
    Command port.

    """

    def __init__(self): ...

    def write(self, companies: list[Company]): ...

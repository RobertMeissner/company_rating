from typing import Protocol

from src.domain.entities.job import Job


class JobQueryPort(Protocol):
    """
    Query port.

    """

    def __init__(self): ...

    def get(self) -> list[Job]: ...

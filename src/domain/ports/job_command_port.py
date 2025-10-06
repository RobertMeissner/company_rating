from typing import Protocol

from src.domain.entities.job import Job


class JobCommandPort(Protocol):
    """
    Command port.

    """

    def __init__(self): ...

    def write(self, jobs: list[Job]): ...

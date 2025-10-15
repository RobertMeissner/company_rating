from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger

logger = get_logger(__name__)


def nan_to_none(value):
    return None if pd.isna(value) else value


def ensure_file_exists(filepath: str) -> None:
    """
    Create a file and its parent directories if they don't exist.

    Args:
        filepath: Path to the file to ensure exists
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.touch()
        logger.debug(f"Created file: {filepath}")

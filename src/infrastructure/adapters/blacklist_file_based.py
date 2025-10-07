from pathlib import Path


class BlacklistFileBasedAdapter:
    """File-based adapter for blacklist storage

    Implements BlacklistPort
    """

    def __init__(self, filename: str):
        self.filename = filename
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        path = Path(self.filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.touch()

    def get(self) -> list[str]:
        with open(self.filename, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]

    def add(self, entity: str) -> None:
        blacklist = set(self.get())
        blacklist.add(entity)
        self.write(sorted(blacklist))

    def remove(self, entity: str) -> None:
        blacklist = set(self.get())
        blacklist.discard(entity)
        self.write(sorted(blacklist))

    def write(self, entities: list[str]) -> None:
        with open(self.filename, "w", encoding="utf-8") as f:
            for name in entities:
                f.write(f"{name}\n")

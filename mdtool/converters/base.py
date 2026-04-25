from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class Converter(Protocol):
    name: str
    extensions: tuple[str, ...]

    def convert(self, path: Path) -> str: ...

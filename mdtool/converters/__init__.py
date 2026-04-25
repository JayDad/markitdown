from pathlib import Path

from .base import Converter
from .pptx import PptxConverter

_REGISTRY: list[Converter] = [PptxConverter()]


def supported_extensions() -> list[str]:
    out: list[str] = []
    for c in _REGISTRY:
        out.extend(c.extensions)
    return out


def convert_file(path: Path) -> str:
    ext = path.suffix.lower()
    for c in _REGISTRY:
        if ext in c.extensions:
            return c.convert(path)
    raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Union

ExcelInput = Union[str, Path, bytes, bytearray, BinaryIO]


def workbook_stream(source: ExcelInput) -> Union[str, Path, BytesIO]:
    if isinstance(source, (str, Path)):
        return source
    if isinstance(source, (bytes, bytearray)):
        return BytesIO(bytes(source))
    return source


def workbook_source_label(source: ExcelInput, default: str = "<memory>") -> str:
    if isinstance(source, Path):
        return str(source)
    if isinstance(source, str):
        return source
    return default

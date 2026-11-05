"""Хранение загруженных фото.

API зависит от протокола ImageStorage, а не от папки на диске: замена на S3
или другое хранилище — новый класс с тем же методом save().
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Protocol

from app.core.errors import ImageError

# Сигнатуры поддерживаемых форматов: тип определяем по содержимому, а не по имени файла.
_SIGNATURES: tuple[tuple[str, bytes, int], ...] = (
    ("jpg", b"\xff\xd8\xff", 0),
    ("png", b"\x89PNG\r\n\x1a\n", 0),
    ("gif", b"GIF87a", 0),
    ("gif", b"GIF89a", 0),
)


def detect_image_extension(data: bytes) -> str | None:
    for extension, signature, offset in _SIGNATURES:
        if data[offset : offset + len(signature)] == signature:
            return extension
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


class ImageStorage(Protocol):
    def save(self, data: bytes) -> str:
        """Сохраняет изображение и возвращает имя файла в хранилище."""
        ...


class LocalImageStorage:
    def __init__(self, directory: Path, max_bytes: int = 10 * 1024 * 1024) -> None:
        self.directory = directory
        self.max_bytes = max_bytes
        directory.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes) -> str:
        if not data:
            raise ImageError("Файл пустой.", code="empty_file")
        if len(data) > self.max_bytes:
            limit_mb = self.max_bytes // (1024 * 1024)
            raise ImageError(
                f"Файл больше {limit_mb} МБ. Уменьшите фото и загрузите снова.",
                code="file_too_large",
                http_status=413,
            )
        extension = detect_image_extension(data)
        if extension is None:
            raise ImageError("Это не изображение. Поддерживаются JPEG, PNG, WebP и GIF.", code="not_an_image")

        name = f"{uuid.uuid4().hex}.{extension}"
        (self.directory / name).write_bytes(data)
        return name

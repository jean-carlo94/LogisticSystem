from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, file: UploadFile, relative_path: str) -> str:
        ...

    @abstractmethod
    async def delete(self, relative_path: str) -> None:
        ...


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: str = "static/uploads"):
        self.base_dir = Path(base_dir)

    async def upload(self, file: UploadFile, relative_path: str) -> str:
        full_path = self.base_dir / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        content = await file.read()
        full_path.write_bytes(content)
        return relative_path

    async def delete(self, relative_path: str) -> None:
        full_path = self.base_dir / relative_path
        if full_path.exists():
            full_path.unlink()


def get_storage() -> StorageBackend:
    if settings.STORAGE_BACKEND == "s3":
        raise NotImplementedError("S3 storage backend not yet implemented")
    return LocalStorageBackend(settings.STORAGE_PATH)


def generate_filename(prefix: str, original_filename: str) -> str:
    ext = os.path.splitext(original_filename)[1] or ".jpg"
    return f"{prefix}_{uuid.uuid4().hex}{ext}"

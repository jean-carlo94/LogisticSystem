from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from app.core.config import settings


class StorageBackend(ABC):
    @abstractmethod
    async def upload(self, file: UploadFile, relative_path: str) -> str:
        ...

    @abstractmethod
    async def delete(self, relative_path: str) -> None:
        ...

    @abstractmethod
    def get_url(self, relative_path: str) -> str:
        ...


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: str = "static/uploads"):
        self.base_dir = Path(base_dir)

    async def upload(self, file: UploadFile, relative_path: str) -> str:
        full_path = self.base_dir / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise ValueError("El archivo excede el límite de 10MB")
        import aiofiles
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(content)
        return relative_path

    async def delete(self, relative_path: str) -> None:
        full_path = self.base_dir / relative_path
        if full_path.exists():
            full_path.unlink()

    def get_url(self, relative_path: str) -> str:
        return f"/static/{relative_path}"


class S3StorageBackend(StorageBackend):
    def __init__(
        self,
        endpoint_url: str,
        bucket: str,
        region: str,
        access_key: str,
        secret_key: str,
        public_url: str = "",
    ):
        self.endpoint_url = endpoint_url
        self.bucket = bucket
        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self.public_url = public_url.rstrip("/") if public_url else ""

    def _get_client(self):
        from aiobotocore.session import get_session

        session = get_session()
        return session.create_client(
            "s3",
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    async def upload(self, file: UploadFile, relative_path: str) -> str:
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            raise ValueError("El archivo excede el límite de 10MB")

        content_type = file.content_type or "application/octet-stream"

        async with self._get_client() as client:
            await client.put_object(
                Bucket=self.bucket,
                Key=relative_path,
                Body=content,
                ContentType=content_type,
            )
        return relative_path

    async def delete(self, relative_path: str) -> None:
        async with self._get_client() as client:
            await client.delete_object(
                Bucket=self.bucket,
                Key=relative_path,
            )

    def get_url(self, relative_path: str) -> str:
        if self.public_url:
            return f"{self.public_url}/{relative_path}"
        return f"{self.endpoint_url}/{self.bucket}/{relative_path}"


_storage_instance: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    global _storage_instance
    if _storage_instance is None:
        if settings.STORAGE_BACKEND == "s3":
            _storage_instance = S3StorageBackend(
                endpoint_url=settings.S3_ENDPOINT,
                bucket=settings.S3_BUCKET,
                region=settings.S3_REGION,
                access_key=settings.S3_ACCESS_KEY,
                secret_key=settings.S3_SECRET_KEY,
                public_url=settings.S3_PUBLIC_URL,
            )
        else:
            _storage_instance = LocalStorageBackend(settings.STORAGE_PATH)
    return _storage_instance


def get_image_url(image_path: str | None) -> str | None:
    if not image_path:
        return None
    return get_storage().get_url(image_path)


def generate_filename(prefix: str, original_filename: str) -> str:
    ext = os.path.splitext(original_filename)[1] or ".jpg"
    return f"{prefix}_{uuid.uuid4().hex}{ext}"

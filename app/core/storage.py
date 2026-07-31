import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import ValidationException

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/svg+xml",
}

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}

MAX_FILE_SIZE = 10 * 1024 * 1024


def validate_file(file: UploadFile) -> None:
    if file.content_type and file.content_type not in ALLOWED_IMAGE_TYPES:
        _ext = os.path.splitext(file.filename or "")[1].lower()
        if _ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationException("Tipo de archivo no permitido. Solo se aceptan imágenes (JPEG, PNG, WebP, GIF, SVG).")


class LocalStorageBackend:
    def __init__(self, base_dir: str = "static/uploads"):
        self.base_dir = Path(base_dir)

    async def upload(self, file: UploadFile, relative_path: str) -> str:
        validate_file(file)
        full_path = self.base_dir / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise ValidationException("El archivo excede el límite de 10MB")
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


_storage_instance: LocalStorageBackend | None = None


def get_storage() -> LocalStorageBackend:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = LocalStorageBackend(settings.STORAGE_PATH)
    return _storage_instance


def get_image_url(image_path: str | None) -> str | None:
    if not image_path:
        return None
    return get_storage().get_url(image_path)


def generate_filename(prefix: str, original_filename: str) -> str:
    ext = os.path.splitext(original_filename)[1] or ".jpg"
    return f"{prefix}_{uuid.uuid4().hex}{ext}"

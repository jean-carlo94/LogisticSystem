import asyncio
import logging
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings
from app.core.exceptions import ValidationException

logger = logging.getLogger(__name__)


class PDFRenderer(ABC):
    @abstractmethod
    async def render(self, html: str) -> bytes: ...


class WeasyPrintRenderer(PDFRenderer):
    async def render(self, html: str) -> bytes:
        from weasyprint import HTML
        doc = HTML(string=html)
        return doc.write_pdf()


class GotenbergRenderer(PDFRenderer):
    def __init__(self):
        self._semaphore = asyncio.Semaphore(settings.PDF_CONCURRENCY_LIMIT)

    async def render(self, html: str) -> bytes:
        async with self._semaphore:
            url = f"{settings.PDF_SERVICE_URL.rstrip('/')}/forms/chromium/convert/html"
            files = {"index.html": ("index.html", html.encode("utf-8"), "text/html")}
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(url, files=files)
                if resp.status_code != 200:
                    raise ValidationException(
                        f"Error del servicio PDF ({resp.status_code}): {resp.text[:500]}"
                    )
                return resp.content


class CustomPDFRenderer(PDFRenderer):
    def __init__(self):
        self._semaphore = asyncio.Semaphore(settings.PDF_CONCURRENCY_LIMIT)

    async def render(self, html: str) -> bytes:
        async with self._semaphore:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    settings.PDF_SERVICE_URL,
                    json={"html": html},
                )
                if resp.status_code != 200:
                    raise ValidationException(
                        f"Error del servicio PDF ({resp.status_code}): {resp.text[:500]}"
                    )
                return resp.content


_pdf_renderer: PDFRenderer | None = None


def get_pdf_renderer() -> PDFRenderer:
    global _pdf_renderer
    if _pdf_renderer is None:
        backend = settings.PDF_RENDERER.lower()
        if backend == "gotenberg":
            _pdf_renderer = GotenbergRenderer()
        elif backend == "custom":
            _pdf_renderer = CustomPDFRenderer()
        else:
            _pdf_renderer = WeasyPrintRenderer()
    return _pdf_renderer

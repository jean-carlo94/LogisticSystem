import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self._clients: dict[str, list[float]] = defaultdict(list)

    def _clean(self, client: str, now: float) -> None:
        cutoff = now - self.window
        self._clients[client] = [t for t in self._clients[client] if t > cutoff]

    def is_allowed(self, client: str) -> bool:
        now = time.time()
        self._clean(client, now)
        return len(self._clients[client]) < self.max_requests

    def hit(self, client: str) -> None:
        self._clients[client].append(time.time())


_rate_limiter = RateLimiter(settings.RATE_LIMIT_REQUESTS, settings.RATE_LIMIT_WINDOW)


async def rate_limit_middleware(request: Request, call_next):
    client = request.client.host if request.client else "unknown"
    if not _rate_limiter.is_allowed(client):
        return JSONResponse(status_code=429, content={"detail": "Demasiadas solicitudes. Intenta de nuevo mas tarde."})
    _rate_limiter.hit(client)
    return await call_next(request)

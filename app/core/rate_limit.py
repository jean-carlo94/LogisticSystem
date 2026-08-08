import time

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self._clients: dict[str, list[float]] = {}

    def _clean(self, client: str, now: float) -> None:
        cutoff = now - self.window
        self._clients[client] = [t for t in self._clients[client] if t > cutoff]
        if not self._clients[client]:
            del self._clients[client]

    def is_allowed(self, client: str) -> bool:
        if self.max_requests <= 0:
            return True
        now = time.time()
        if client not in self._clients:
            self._clients[client] = []
        self._clean(client, now)
        return client not in self._clients or len(self._clients[client]) < self.max_requests

    def hit(self, client: str) -> None:
        if self.max_requests <= 0:
            return
        if client not in self._clients:
            self._clients[client] = []
        self._clients[client].append(time.time())
        if len(self._clients) > 50_000:
            now = time.time()
            cutoff = now - self.window
            stale = [k for k, v in self._clients.items() if not v]
            for k in stale:
                del self._clients[k]
            for k in list(self._clients):
                self._clients[k] = [t for t in self._clients[k] if t > cutoff]
                if not self._clients[k]:
                    del self._clients[k]


_rate_limiter = RateLimiter(settings.RATE_LIMIT_REQUESTS, settings.RATE_LIMIT_WINDOW)

forgot_password_limiter = RateLimiter(5, 60)

activate_limiter = RateLimiter(10, 60)


async def rate_limit_middleware(request: Request, call_next):
    client = request.client.host if request.client else "unknown"
    if not _rate_limiter.is_allowed(client):
        return JSONResponse(status_code=429, content={"detail": "Demasiadas solicitudes. Intenta de nuevo mas tarde."})
    _rate_limiter.hit(client)
    return await call_next(request)

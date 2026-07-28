from __future__ import annotations

import math
from typing import Generic, TypeVar

from fastapi import Depends, Query, Request
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def of(cls, items: list[T], total: int, page: int, size: int) -> "PaginatedResponse[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=max(1, math.ceil(total / size)) if total > 0 else 0,
        )


RESERVED_PARAMS = {"page", "size"}


def get_pagination(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> dict[str, int]:
    return {"page": page, "size": size}


def get_filters(request: Request) -> dict[str, str]:
    params = dict(request.query_params)
    for key in RESERVED_PARAMS:
        params.pop(key, None)
    return {k: v for k, v in params.items() if v != ""}


PaginationParams = Depends(get_pagination)
FilterParams = Depends(get_filters)

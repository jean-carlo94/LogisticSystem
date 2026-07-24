from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Generic, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel

T = TypeVar("T")


@dataclass
class PaginatedResult(Generic[T]):
    items: list[T] = field(default_factory=list)
    total: int = 0
    page: int = 1
    size: int = 20
    pages: int = 0

    @classmethod
    def of(cls, items: list[T], total: int, page: int, size: int) -> "PaginatedResult[T]":
        return cls(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=max(1, math.ceil(total / size)) if total > 0 else 0,
        )


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


def get_pagination(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
) -> dict[str, int]:
    return {"page": page, "size": size}


PaginationParams = Depends(get_pagination)

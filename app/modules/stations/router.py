from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query, status

from app.core.pagination import FilterParams, PaginatedResponse, PaginationParams
from app.core.security import require_cash_register, require_permission
from app.modules.stations.deps import get_station_service
from app.modules.stations.schema import (
    StationCreate, StationUpdate, StationResponse, StationDetailResponse,
    SessionOpenRequest, SessionItemsCreate, SessionItemUpdate,
    StationSessionResponse, SessionItemResponse,
)
from app.modules.stations.service import StationService
from app.core.permissions import PermissionCode

if TYPE_CHECKING:
    from app.modules.users.model import User

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("/", response_model=PaginatedResponse[StationResponse])
async def list_stations(
    pag: dict = PaginationParams,
    code: str | None = Query(default=None, description="Código único"),
    filters: dict = FilterParams,
    service: StationService = Depends(get_station_service),
    _perm: "User" = Depends(require_permission(PermissionCode.STATIONS_VIEW)),
):
    merged = dict(filters)
    if code is not None:
        merged["code"] = code
    return await service.get_all(
        page=pag["page"], size=pag["size"], filters=merged or None
    )


@router.post(
    "/", response_model=StationResponse, status_code=status.HTTP_201_CREATED
)
async def create_station(
    data: StationCreate,
    service: StationService = Depends(get_station_service),
    user: "User" = Depends(require_permission(PermissionCode.STATIONS_CREATE)),
):
    return await service.create(data, user.id)


@router.get("/{station_id}", response_model=StationDetailResponse)
async def get_station(
    station_id: int,
    service: StationService = Depends(get_station_service),
    _perm: "User" = Depends(require_permission(PermissionCode.STATIONS_VIEW)),
):
    return await service.get_by_id(station_id)


@router.put("/{station_id}", response_model=StationResponse)
async def update_station(
    station_id: int,
    data: StationUpdate,
    service: StationService = Depends(get_station_service),
    user: "User" = Depends(require_permission(PermissionCode.STATIONS_EDIT)),
):
    return await service.update(station_id, data, user.id)


@router.delete("/{station_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_station(
    station_id: int,
    service: StationService = Depends(get_station_service),
    user: "User" = Depends(require_permission(PermissionCode.STATIONS_DELETE)),
):
    await service.delete(station_id, user.id)


@router.post(
    "/{station_id}/open",
    response_model=StationSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def open_session(
    station_id: int,
    data: SessionOpenRequest = SessionOpenRequest(),
    service: StationService = Depends(get_station_service),
    user: "User" = Depends(require_permission(PermissionCode.STATIONS_OPEN_CLOSE)),
):
    return await service.open_session(station_id, data, user.id)


@router.post("/{station_id}/close", response_model=StationSessionResponse)
async def close_session(
    station_id: int,
    service: StationService = Depends(get_station_service),
    user: "User" = Depends(require_permission(PermissionCode.STATIONS_OPEN_CLOSE)),
    cash_register_id: int | None = Depends(require_cash_register),
):
    return await service.close_session(station_id, user.id, cash_register_id)


@router.post("/{station_id}/cancel", response_model=StationSessionResponse)
async def cancel_session(
    station_id: int,
    service: StationService = Depends(get_station_service),
    user: "User" = Depends(require_permission(PermissionCode.STATIONS_OPEN_CLOSE)),
):
    return await service.cancel_session(station_id, user.id)


@router.get("/{station_id}/items", response_model=list[SessionItemResponse])
async def get_session_items(
    station_id: int,
    service: StationService = Depends(get_station_service),
    _perm: "User" = Depends(require_permission(PermissionCode.STATIONS_VIEW)),
):
    return await service.get_session_items(station_id)


@router.post(
    "/{station_id}/items",
    response_model=list[SessionItemResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_items(
    station_id: int,
    data: SessionItemsCreate,
    service: StationService = Depends(get_station_service),
    user: "User" = Depends(require_permission(PermissionCode.STATIONS_MANAGE_ITEMS)),
):
    return await service.add_items(station_id, data, user.id)


@router.put(
    "/{station_id}/items/{item_id}",
    response_model=SessionItemResponse,
)
async def update_item(
    station_id: int,
    item_id: int,
    data: SessionItemUpdate,
    service: StationService = Depends(get_station_service),
    user: "User" = Depends(require_permission(PermissionCode.STATIONS_MANAGE_ITEMS)),
):
    return await service.update_item(station_id, item_id, data, user.id)


@router.delete(
    "/{station_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_item(
    station_id: int,
    item_id: int,
    service: StationService = Depends(get_station_service),
    user: "User" = Depends(require_permission(PermissionCode.STATIONS_MANAGE_ITEMS)),
):
    await service.cancel_item(station_id, item_id, user.id)


@router.post(
    "/{station_id}/items/{item_id}/prepare",
    response_model=SessionItemResponse,
)
async def prepare_item(
    station_id: int,
    item_id: int,
    service: StationService = Depends(get_station_service),
    user: "User" = Depends(require_permission(PermissionCode.STATIONS_MANAGE_ITEMS)),
):
    return await service.transition_item(station_id, item_id, user.id)


@router.post(
    "/{station_id}/items/{item_id}/ready",
    response_model=SessionItemResponse,
)
async def ready_item(
    station_id: int,
    item_id: int,
    service: StationService = Depends(get_station_service),
    user: "User" = Depends(require_permission(PermissionCode.STATIONS_MANAGE_ITEMS)),
):
    return await service.transition_item(station_id, item_id, user.id)


@router.post(
    "/{station_id}/items/{item_id}/deliver",
    response_model=SessionItemResponse,
)
async def deliver_item(
    station_id: int,
    item_id: int,
    service: StationService = Depends(get_station_service),
    user: "User" = Depends(require_permission(PermissionCode.STATIONS_MANAGE_ITEMS)),
):
    return await service.transition_item(station_id, item_id, user.id)


@router.post(
    "/{station_id}/transfer/{target_id}",
    response_model=StationSessionResponse,
)
async def transfer_session(
    station_id: int,
    target_id: int,
    service: StationService = Depends(get_station_service),
    user: "User" = Depends(require_permission(PermissionCode.STATIONS_OPEN_CLOSE)),
):
    return await service.transfer_session(station_id, target_id, user.id)

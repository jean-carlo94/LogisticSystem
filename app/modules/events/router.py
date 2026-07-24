from fastapi import APIRouter, Depends

from app.core.exceptions import NotFoundException
from app.core.pagination import PaginatedResponse, PaginationParams
from app.core.security import require_permission
from app.modules.events.deps import get_event_service
from app.modules.events.schema import EventResponse
from app.modules.events.service import EventService
from app.core.permissions import PermissionCode

router = APIRouter(tags=["events"])


@router.get("/events/", response_model=PaginatedResponse[EventResponse])
async def list_events(
    pag: dict = PaginationParams,
    service: EventService = Depends(get_event_service),
    _perm = Depends(require_permission(PermissionCode.EVENTS_READ)),
) -> PaginatedResponse[EventResponse]:
    return await service.get_all(page=pag["page"], size=pag["size"])


@router.get("/events/{event_id}", response_model=EventResponse)
async def retrieve_event(
    event_id: int,
    service: EventService = Depends(get_event_service),
    _perm = Depends(require_permission(PermissionCode.EVENTS_READ)),
) -> EventResponse:
    event = await service.get_by_id(event_id)
    if not event:
        raise NotFoundException("Evento no encontrado")
    return event


@router.get(
    "/{entity_type}/{entity_id}/events/",
    response_model=PaginatedResponse[EventResponse],
)
async def list_entity_events(
    entity_type: str,
    entity_id: int,
    pag: dict = PaginationParams,
    service: EventService = Depends(get_event_service),
    _perm = Depends(require_permission(PermissionCode.EVENTS_READ)),
) -> PaginatedResponse[EventResponse]:
    return await service.get_by_entity(entity_type, entity_id, page=pag["page"], size=pag["size"])

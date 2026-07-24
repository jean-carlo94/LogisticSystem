from fastapi import APIRouter, Depends, Query

from app.core.exceptions import NotFoundException
from app.core.pagination import PaginatedResponse
from app.core.security import get_current_user
from app.modules.events.deps import get_event_service
from app.modules.events.schema import EventResponse
from app.modules.events.service import EventService

router = APIRouter(tags=["events"])


@router.get("/events/", response_model=PaginatedResponse[EventResponse])
async def list_events(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    service: EventService = Depends(get_event_service),
    _user = Depends(get_current_user),
) -> PaginatedResponse[EventResponse]:
    return await service.get_all(page=page, size=size)


@router.get("/events/{event_id}", response_model=EventResponse)
async def retrieve_event(
    event_id: int,
    service: EventService = Depends(get_event_service),
    _user = Depends(get_current_user),
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
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    service: EventService = Depends(get_event_service),
    _user = Depends(get_current_user),
) -> PaginatedResponse[EventResponse]:
    return await service.get_by_entity(entity_type, entity_id, page=page, size=size)

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.pagination import PaginatedResponse
from app.modules.events.deps import get_event_service
from app.modules.events.schema import EventResponse
from app.modules.events.service import EventService

router = APIRouter(tags=["events"])


@router.get("/events/", response_model=PaginatedResponse[EventResponse])
def list_events(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    service: EventService = Depends(get_event_service),
) -> PaginatedResponse[EventResponse]:
    return service.get_all(page=page, size=size)


@router.get("/events/{event_id}", response_model=EventResponse)
def retrieve_event(
    event_id: int,
    service: EventService = Depends(get_event_service),
) -> EventResponse:
    event = service.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evento no encontrado")
    return event


@router.get(
    "/{entity_type}/{entity_id}/events/",
    response_model=PaginatedResponse[EventResponse],
)
def list_entity_events(
    entity_type: str,
    entity_id: int,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    service: EventService = Depends(get_event_service),
) -> PaginatedResponse[EventResponse]:
    return service.get_by_entity(entity_type, entity_id, page=page, size=size)

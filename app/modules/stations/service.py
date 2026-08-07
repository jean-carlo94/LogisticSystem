from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginatedResponse
from app.core.tenant import current_tenant_id
from app.modules.stations.model import (
    Station, StationSession, StationSessionItem,
    StationStatus, SessionStatus, SessionItemStatus,
)
from app.modules.stations.repository import (
    StationRepository,
    StationSessionRepository,
    StationSessionItemRepository,
)
from app.modules.stations.schema import (
    StationCreate, StationUpdate,
    SessionItemsCreate, SessionItemUpdate,
    SessionOpenRequest,
    SessionItemResponse,
    StationDetailResponse,
    StationSessionResponse,
)
from app.modules.shelves.repository import ShelfItemRepository

if TYPE_CHECKING:
    from app.modules.sales.service import SaleService
    from app.modules.customers.service import CustomerService

_TRANSITIONS = {
    SessionItemStatus.CREATED: SessionItemStatus.PREPARING,
    SessionItemStatus.PREPARING: SessionItemStatus.READY,
    SessionItemStatus.READY: SessionItemStatus.DELIVERED,
}


class StationService:
    def __init__(
        self,
        station_repo: StationRepository,
        session_repo: StationSessionRepository,
        item_repo: StationSessionItemRepository,
        shelf_item_repo: ShelfItemRepository,
        audit: AuditLogger,
        sale_service: SaleService,
        customer_service: CustomerService,
    ):
        self.station_repo = station_repo
        self.session_repo = session_repo
        self.item_repo = item_repo
        self.shelf_item_repo = shelf_item_repo
        self.audit = audit
        self.sale_service = sale_service
        self.customer_service = customer_service

    async def get_all(
        self, page: int = 1, size: int = 20, filters: dict | None = None
    ) -> PaginatedResponse:
        skip = (page - 1) * size
        items, total = await self.station_repo.get_all(
            skip=skip, limit=size, filters=filters
        )
        return PaginatedResponse.of(list(items), total, page, size)

    async def get_by_id(self, station_id: int) -> StationDetailResponse:
        station = await self.station_repo.get_by_id(station_id)
        if not station:
            raise NotFoundException("Estación no encontrada")

        active_session = await self.session_repo.get_active_by_station(station_id)
        session_response = None
        if active_session:
            items = await self.item_repo.get_items_by_session(active_session.id)
            session_response = await self._build_session_response(
                active_session, items
            )

        return StationDetailResponse(
            id=station.id,
            code=station.code,
            name=station.name,
            area=station.area,
            capacity=station.capacity,
            status=station.status.value,
            created_at=station.created_at,
            updated_at=station.updated_at,
            active_session=session_response,
        )

    async def create(self, data: StationCreate, user_id: int) -> Station:
        if current_tenant_id.get() is None:
            raise ValidationException("Debe especificar un tenant (use header X-Tenant)")

        existing = await self.station_repo.find_by_code(data.code)
        if existing:
            raise ConflictException("El código de estación ya existe")

        station = await self.station_repo.create(**data.model_dump())
        await self.audit.log_create("Station", station.id, user_id, station)
        return station

    async def update(
        self, station_id: int, data: StationUpdate, user_id: int
    ) -> Station:
        station = await self.station_repo.get_by_id(station_id)
        if not station:
            raise NotFoundException("Estación no encontrada")

        update_data = data.model_dump(exclude_unset=True)

        if "code" in update_data and update_data["code"] != station.code:
            existing = await self.station_repo.find_by_code(update_data["code"])
            if existing and existing.id != station_id:
                raise ConflictException("El código de estación ya existe")

        await self.station_repo.update(station, **update_data)
        await self.audit.log_update("Station", station.id, user_id, update_data)
        return station

    async def delete(self, station_id: int, user_id: int) -> None:
        station = await self.station_repo.get_by_id(station_id)
        if not station:
            raise NotFoundException("Estación no encontrada")

        active = await self.session_repo.get_active_by_station(station_id)
        if active:
            raise ConflictException("No se puede eliminar una estación con sesión abierta")

        await self.audit.log_delete("Station", station.id, user_id, station)
        await self.station_repo.delete(station)

    async def open_session(
        self, station_id: int, data: SessionOpenRequest, user_id: int,
        cash_register_id: int | None = None,
    ) -> StationSessionResponse:
        station = await self.station_repo.get_by_id(station_id)
        if not station:
            raise NotFoundException("Estación no encontrada")

        if station.status == StationStatus.MAINTENANCE:
            raise ConflictException("Estación en mantenimiento")

        active = await self.session_repo.get_active_by_station(station_id)
        if active:
            raise ConflictException("La estación ya tiene una sesión abierta")

        customer_data = data.model_dump()
        customer = None
        if any([customer_data.get("customer_email"), customer_data.get("customer_document")]):
            customer = await self.customer_service.find_or_create(customer_data, user_id)

        session = await self.session_repo.create(
            station_id=station_id,
            customer_id=customer.id if customer else None,
            customer_name=data.customer_name,
            customer_email=data.customer_email,
            customer_phone=data.customer_phone,
            customer_document=data.customer_document,
            customer_address=data.customer_address,
            created_by=user_id,
            cash_register_id=cash_register_id,
        )

        await self.station_repo.update(station, status=StationStatus.OCCUPIED)
        await self.audit.log_create("StationSession", session.id, user_id, session)

        return await self._build_session_response(session, [])

    async def close_session(
        self, station_id: int, user_id: int
    ) -> StationSessionResponse:
        session = await self.session_repo.get_active_by_station(station_id)
        if not session:
            raise NotFoundException("No hay sesión abierta en esta estación")

        items = await self.item_repo.get_items_by_session(session.id)
        chargeable = [i for i in items if i.status != SessionItemStatus.CANCELLED]

        if chargeable:
            from app.modules.sales.schema import SaleCreate, SaleItemCreate
            sale_items = [
                SaleItemCreate(
                    product_id=it.product_id,
                    quantity=it.quantity,
                    unit_price=it.unit_price,
                )
                for it in chargeable
            ]
            sale_data = SaleCreate(
                customer_name=session.customer_name,
                customer_email=session.customer_email,
                customer_phone=session.customer_phone,
                customer_document=session.customer_document,
                customer_address=session.customer_address,
                items=sale_items,
            )

            prev_tenant = current_tenant_id.get()
            sale_detail = await self.sale_service.create(
                sale_data, user_id, session.cash_register_id
            )
            current_tenant_id.set(prev_tenant)

            total = sum(it.subtotal for it in chargeable)
            await self.session_repo.update(
                session,
                sale_id=sale_detail.id,
                total=total,
                status=SessionStatus.CLOSED,
                closed_at=datetime.utcnow(),
            )
        else:
            await self.session_repo.update(
                session,
                status=SessionStatus.CLOSED,
                closed_at=datetime.utcnow(),
            )

        station = await self.station_repo.get_by_id(station_id)
        await self.station_repo.update(station, status=StationStatus.AVAILABLE)

        await self.audit.log_update(
            "StationSession", session.id, user_id,
            {"status": "CLOSED"},
        )

        updated_items = await self.item_repo.get_items_by_session(session.id)
        return await self._build_session_response(session, updated_items)

    async def cancel_session(
        self, station_id: int, user_id: int
    ) -> StationSessionResponse:
        session = await self.session_repo.get_active_by_station(station_id)
        if not session:
            raise NotFoundException("No hay sesión abierta en esta estación")

        await self.session_repo.update(
            session,
            status=SessionStatus.CANCELLED,
            closed_at=datetime.utcnow(),
        )

        station = await self.station_repo.get_by_id(station_id)
        await self.station_repo.update(station, status=StationStatus.AVAILABLE)

        await self.audit.log_update(
            "StationSession", session.id, user_id,
            {"status": "CANCELLED"},
        )

        items = await self.item_repo.get_items_by_session(session.id)
        return await self._build_session_response(session, items)

    async def get_session_items(self, station_id: int) -> list[SessionItemResponse]:
        session = await self.session_repo.get_active_by_station(station_id)
        if not session:
            return []

        items = await self.item_repo.get_items_by_session(session.id)
        return await self._build_item_responses(items)

    async def add_items(
        self, station_id: int, data: SessionItemsCreate, user_id: int
    ) -> list[SessionItemResponse]:
        session = await self.session_repo.get_active_by_station(station_id)
        if not session:
            raise NotFoundException("No hay sesión abierta en esta estación")

        product_ids = [i.product_id for i in data.items]
        products = await self.shelf_item_repo.get_products_by_ids(product_ids)
        products_map = {p.id: p for p in products}

        new_items = []
        for item_in in data.items:
            product = products_map.get(item_in.product_id)
            if not product:
                raise NotFoundException(
                    f"Producto {item_in.product_id} no encontrado"
                )

            subtotal = round(item_in.quantity * product.price, 2)
            unit_price = product.price

            item = await self.item_repo.create(
                session_id=session.id,
                product_id=item_in.product_id,
                quantity=item_in.quantity,
                unit_price=unit_price,
                subtotal=subtotal,
                notes=item_in.notes,
            )
            await self.audit.log_create(
                "StationSessionItem", item.id, user_id, item
            )
            new_items.append(item)

        return await self._build_item_responses(new_items)

    async def update_item(
        self, station_id: int, item_id: int, data: SessionItemUpdate, user_id: int
    ) -> SessionItemResponse:
        session = await self.session_repo.get_active_by_station(station_id)
        if not session:
            raise NotFoundException("No hay sesión abierta en esta estación")

        item = await self.item_repo.get_item_by_id(item_id)
        if not item or item.session_id != session.id:
            raise NotFoundException("Ítem no encontrado en esta sesión")

        if item.status != SessionItemStatus.CREATED:
            raise ConflictException(
                f"Solo se pueden modificar ítems en estado CREATED, "
                f"actual: {item.status.value}"
            )

        update_data = {}
        if data.quantity is not None:
            product = await self.shelf_item_repo.get_product_by_id(item.product_id)
            if product:
                update_data["quantity"] = data.quantity
                update_data["subtotal"] = round(data.quantity * item.unit_price, 2)
        if data.notes is not None:
            update_data["notes"] = data.notes

        if update_data:
            await self.item_repo.update(item, **update_data)
            await self.audit.log_update(
                "StationSessionItem", item.id, user_id, update_data
            )

        return (await self._build_item_responses([item]))[0]

    async def cancel_item(
        self, station_id: int, item_id: int, user_id: int
    ) -> None:
        session = await self.session_repo.get_active_by_station(station_id)
        if not session:
            raise NotFoundException("No hay sesión abierta en esta estación")

        item = await self.item_repo.get_item_by_id(item_id)
        if not item or item.session_id != session.id:
            raise NotFoundException("Ítem no encontrado en esta sesión")

        await self.item_repo.update(item, status=SessionItemStatus.CANCELLED)
        await self.audit.log_update(
            "StationSessionItem", item.id, user_id,
            {"status": "CANCELLED"},
        )

    async def transition_item(
        self, station_id: int, item_id: int, user_id: int
    ) -> SessionItemResponse:
        session = await self.session_repo.get_active_by_station(station_id)
        if not session:
            raise NotFoundException("No hay sesión abierta en esta estación")

        item = await self.item_repo.get_item_by_id(item_id)
        if not item or item.session_id != session.id:
            raise NotFoundException("Ítem no encontrado en esta sesión")

        if item.status == SessionItemStatus.CANCELLED:
            raise ConflictException("No se puede cambiar el estado de un ítem cancelado")

        if item.status == SessionItemStatus.DELIVERED:
            raise ConflictException("El ítem ya fue entregado")

        next_status = _TRANSITIONS.get(item.status)
        if not next_status:
            raise ConflictException(
                f"El ítem en estado '{item.status.value}' no puede cambiar de estado"
            )

        await self.item_repo.update(item, status=next_status)
        await self.audit.log_update(
            "StationSessionItem", item.id, user_id,
            {"status": next_status.value, "previous_status": item.status.value},
        )

        return (await self._build_item_responses([item]))[0]

    async def transfer_session(
        self, station_id: int, target_id: int, user_id: int
    ) -> StationSessionResponse:
        session = await self.session_repo.get_active_by_station(station_id)
        if not session:
            raise NotFoundException("No hay sesión abierta en la estación origen")

        target = await self.station_repo.get_by_id(target_id)
        if not target:
            raise NotFoundException("Estación destino no encontrada")

        if target.status != StationStatus.AVAILABLE:
            raise ConflictException("La estación destino no está disponible")

        active_target = await self.session_repo.get_active_by_station(target_id)
        if active_target:
            raise ConflictException("La estación destino ya tiene una sesión abierta")

        source_station = await self.station_repo.get_by_id(station_id)
        await self.station_repo.update(source_station, status=StationStatus.AVAILABLE)
        await self.station_repo.update(target, status=StationStatus.OCCUPIED)

        await self.session_repo.update(session, station_id=target_id)

        await self.audit.log_update(
            "StationSession", session.id, user_id,
            {"station_id": target_id, "previous_station_id": station_id},
        )

        items = await self.item_repo.get_items_by_session(session.id)
        return await self._build_session_response(session, items)

    async def _build_session_response(
        self, session: StationSession, items: list[StationSessionItem]
    ) -> StationSessionResponse:
        item_responses = await self._build_item_responses(items)
        return StationSessionResponse(
            id=session.id,
            station_id=session.station_id,
            customer_id=session.customer_id,
            customer_name=session.customer_name,
            total=session.total,
            status=session.status.value,
            sale_id=session.sale_id,
            cash_register_id=session.cash_register_id,
            created_by=session.created_by,
            opened_at=session.opened_at,
            closed_at=session.closed_at,
            items=item_responses,
        )

    async def _build_item_responses(
        self, items: list[StationSessionItem]
    ) -> list[SessionItemResponse]:
        if not items:
            return []

        product_ids = list(set(i.product_id for i in items))
        products_map = {}
        if product_ids:
            products = await self.shelf_item_repo.get_products_by_ids(product_ids)
            products_map = {p.id: p for p in products}

        return [
            SessionItemResponse(
                id=item.id,
                session_id=item.session_id,
                product_id=item.product_id,
                product_name=products_map[item.product_id].name
                if item.product_id in products_map else "?",
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                status=item.status.value,
                notes=item.notes,
            )
            for item in items
        ]

from __future__ import annotations

from app.core.audit import AuditLogger
from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.core.pagination import PaginatedResponse
from app.core.tenant import current_tenant_id
from app.modules.customers.service import CustomerService
from app.modules.products.repository import ProductRepository
from app.modules.sales.model import SaleStatus
from app.modules.sales.model import Sale
from app.modules.sales.repository import SaleItemRepository, SaleRepository
from app.modules.sales.schema import (
    SaleCreate, SaleItemResponse, SaleDetailResponse, SaleCancelResponse,
    ReceiptResponse, ReceiptItemResponse, ReceiptTaxLine,
)
from app.modules.shelves.repository import ShelfItemRepository, ShelfRepository
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.schema import PaymentResponse
from app.modules.tenants.repository import TenantRepository


class SaleService:
    def __init__(
        self,
        sale_repo: SaleRepository,
        sale_item_repo: SaleItemRepository,
        shelf_item_repo: ShelfItemRepository,
        shelf_repo: ShelfRepository,
        product_repo: ProductRepository,
        customer_service: CustomerService,
        audit: AuditLogger,
        payment_repo: PaymentRepository,
        tenant_repo: TenantRepository,
    ):
        self.sale_repo = sale_repo
        self.sale_item_repo = sale_item_repo
        self.shelf_item_repo = shelf_item_repo
        self.shelf_repo = shelf_repo
        self.product_repo = product_repo
        self.customer_service = customer_service
        self.audit = audit
        self.payment_repo = payment_repo
        self.tenant_repo = tenant_repo

    async def get_all(
        self, page: int = 1, size: int = 20, filters: dict | None = None
    ) -> PaginatedResponse[Sale]:
        skip = (page - 1) * size
        items, total = await self.sale_repo.get_all(
            skip=skip, limit=size, filters=filters
        )
        return PaginatedResponse.of(list(items), total, page, size)

    async def get_by_id(self, sale_id: int) -> SaleDetailResponse:
        return await self._build_detail(sale_id)

    async def cancel(self, sale_id: int, user_id: int) -> SaleCancelResponse:
        sale = await self.sale_repo.get_by_id(sale_id)
        if not sale:
            raise NotFoundException("Venta no encontrada")

        if sale.status == SaleStatus.CANCELLED:
            raise ConflictException("La venta ya está cancelada")

        if sale.payment_status == "PAID":
            raise ConflictException(
                "No se puede cancelar una venta ya pagada. Use devolución/reembolso"
            )

        items = await self.sale_item_repo.get_items_by_sale(sale_id)

        for item in items:
            product = await self.product_repo.get_by_id(item.product_id)
            if product:
                new_stock = product.stock + item.quantity
                await self.product_repo.update(product, stock=new_stock)
                await self.audit.log_update(
                    "Product", product.id, user_id,
                    {"stock": new_stock, "action": "cancel_sale", "sale_id": sale_id},
                )

            if item.shelf_id is not None:
                shelf_items = await self.shelf_item_repo.get_items_by_product(item.product_id)
                existing = next(
                    (si for si in shelf_items if si.shelf_id == item.shelf_id), None
                )
                if existing:
                    new_qty = existing.quantity + item.quantity
                    await self.shelf_item_repo.update(existing, quantity=new_qty)
                else:
                    await self.shelf_item_repo.create(
                        shelf_id=item.shelf_id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                    )
                await self.audit.log_create(
                    "ShelfItem", sale_id, user_id,
                    {"action": "restore_from_cancel", "shelf_id": item.shelf_id,
                     "product_id": item.product_id, "quantity": item.quantity},
                )

        await self.sale_repo.update(sale, status=SaleStatus.CANCELLED, payment_status="REFUNDED")
        await self.audit.log_update(
            "Sale", sale.id, user_id,
            {"status": "CANCELLED", "previous_status": "COMPLETED"},
        )

        return SaleCancelResponse(
            id=sale.id,
            status="CANCELLED",
            payment_status="REFUNDED",
            message="Venta cancelada. Stock restaurado.",
        )

    async def get_receipt(self, sale_id: int, user_id: int) -> ReceiptResponse:
        sale = await self.sale_repo.get_by_id(sale_id)
        if not sale:
            raise NotFoundException("Venta no encontrada")

        items = await self.sale_item_repo.get_items_by_sale(sale_id)
        product_ids = list(set(i.product_id for i in items))
        products_map = {}
        taxes_map = {}
        if product_ids:
            products = await self.shelf_item_repo.get_products_by_ids(product_ids)
            products_map = {p.id: p for p in products}
            taxes_map = await self.product_repo.get_products_taxes_batch(product_ids)

        subtotal_total = 0.0
        tax_total = 0.0
        receipt_items = []
        for item in items:
            product = products_map.get(item.product_id)
            tax_lines = []
            taxes = taxes_map.get(item.product_id, [])
            for tax in taxes:
                line_tax = round(item.subtotal * tax.rate / 100, 2)
                tax_lines.append(ReceiptTaxLine(
                    name=tax.name,
                    rate=tax.rate,
                    amount=line_tax,
                ))
            subtotal_total += item.subtotal
            tax_total += item.tax_amount
            receipt_items.append(ReceiptItemResponse(
                product_name=product.name if product else "?",
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
                tax_amount=item.tax_amount,
                taxes=tax_lines,
            ))

        payments_db = await self.payment_repo.get_by_sale(sale_id)
        payments = [
            PaymentResponse.model_validate(p).model_dump() for p in payments_db
        ]

        tenant = await self.tenant_repo.get_by_id(sale.tenant_id)

        return ReceiptResponse(
            sale_id=sale.id,
            store_name=tenant.name if tenant else "",
            store_slug=tenant.slug if tenant else "",
            customer_name=sale.customer_name,
            items=receipt_items,
            subtotal=round(subtotal_total, 2),
            tax_total=round(tax_total, 2),
            total=sale.total,
            payments=payments,
            status=sale.status.value,
            payment_status=sale.payment_status,
            created_by=sale.created_by,
            created_at=sale.created_at.isoformat() if sale.created_at else "",
        )

    async def create(self, data: SaleCreate, user_id: int) -> SaleDetailResponse:
        if not data.items:
            raise ValidationException("La venta debe tener al menos un producto")
        if current_tenant_id.get() is None:
            raise ValidationException("Debe especificar un tenant (use header X-Tenant)")

        customer_data = data.model_dump()
        customer = None
        if any([customer_data.get("customer_email"), customer_data.get("customer_document"), customer_data.get("customer_phone")]):
            customer = await self.customer_service.find_or_create(
                customer_data, user_id
            )

        product_ids = [i.product_id for i in data.items]
        products_map = await self.product_repo.lock_products_for_update(product_ids)

        shelf_items = await self.shelf_item_repo.get_items_by_product_ids(product_ids)
        shelf_items_map = {(si.shelf_id, si.product_id): si for si in shelf_items}

        total = 0.0
        items_deducted = []

        taxes_map = await self.product_repo.get_products_taxes_batch(product_ids)

        for item_in in data.items:
            product = products_map.get(item_in.product_id)
            if not product:
                raise NotFoundException(
                    f"Producto {item_in.product_id} no encontrado"
                )

            if product.stock < item_in.quantity:
                raise ConflictException(
                    f"Stock insuficiente en inventario para '{product.name}': "
                    f"hay {product.stock}, solicitados {item_in.quantity}"
                )

            shelf_item = None
            if item_in.shelf_id is not None:
                shelf_item = shelf_items_map.get((item_in.shelf_id, item_in.product_id))
                if not shelf_item:
                    raise NotFoundException(
                        f"Producto {item_in.product_id} no asignado a la estantería "
                        f"{item_in.shelf_id}"
                    )
                if shelf_item.quantity < item_in.quantity:
                    raise ConflictException(
                        f"Stock insuficiente en estantería {item_in.shelf_id} para "
                        f"'{product.name}': hay {shelf_item.quantity}, "
                        f"solicitados {item_in.quantity}"
                    )

            subtotal = round(item_in.quantity * item_in.unit_price, 2)
            taxes = taxes_map.get(item_in.product_id, [])
            tax_amount = 0.0
            for tax in taxes:
                tax_amount += round(subtotal * tax.rate / 100, 2)
            tax_amount = round(tax_amount, 2)

            total += subtotal + tax_amount

            if shelf_item:
                new_shelf_qty = shelf_item.quantity - item_in.quantity
                if new_shelf_qty == 0:
                    await self.shelf_item_repo.delete(shelf_item)
                    await self.audit.log_delete(
                        "ShelfItem", shelf_item.id, user_id, shelf_item
                    )
                else:
                    await self.shelf_item_repo.update(shelf_item, quantity=new_shelf_qty)
                    await self.audit.log_update(
                        "ShelfItem", shelf_item.id, user_id,
                        {"quantity": new_shelf_qty},
                    )

            original_stock = product.stock
            new_stock = product.stock - item_in.quantity
            await self.product_repo.update(product, stock=new_stock)
            await self.audit.log_update(
                "Product", product.id, user_id,
                {"stock": new_stock, "previous_stock": original_stock},
            )

            items_deducted.append({
                "product": product,
                "shelf_id": item_in.shelf_id,
                "quantity": item_in.quantity,
                "unit_price": item_in.unit_price,
                "subtotal": subtotal,
                "tax_amount": tax_amount,
            })

        sale = await self.sale_repo.create(
            customer_name=data.customer_name,
            customer_email=data.customer_email,
            customer_phone=data.customer_phone,
            customer_document=data.customer_document,
            customer_address=data.customer_address,
            customer_id=customer.id if customer else None,
            total=round(total, 2),
            status=SaleStatus.COMPLETED,
            notes=data.notes,
            created_by=user_id,
        )

        for it in items_deducted:
            item = await self.sale_item_repo.create(
                sale_id=sale.id,
                product_id=it["product"].id,
                shelf_id=it["shelf_id"],
                quantity=it["quantity"],
                unit_price=it["unit_price"],
                subtotal=it["subtotal"],
                tax_amount=it["tax_amount"],
            )
            await self.audit.log_create("SaleItem", item.id, user_id, item)

        await self.audit.log_create("Sale", sale.id, user_id, sale)

        return await self._build_detail(sale.id)

    async def _build_detail(self, sale_id: int) -> SaleDetailResponse:
        sale = await self.sale_repo.get_by_id(sale_id)
        if not sale:
            raise NotFoundException("Venta no encontrada")

        items = await self.sale_item_repo.get_items_by_sale(sale_id)

        product_ids = list(set(i.product_id for i in items))
        shelf_ids = list(set(i.shelf_id for i in items if i.shelf_id is not None))

        products_map = {}
        if product_ids:
            products = await self.shelf_item_repo.get_products_by_ids(product_ids)
            products_map = {p.id: p for p in products}

        shelves_map = {}
        if shelf_ids:
            shelves = await self.shelf_repo.get_shelves_by_ids(shelf_ids)
            shelves_map = {s.id: s for s in shelves}

        item_responses = []
        for item in items:
            product = products_map.get(item.product_id)
            shelf = shelves_map.get(item.shelf_id) if item.shelf_id is not None else None
            item_responses.append(
                SaleItemResponse(
                    id=item.id,
                    product_id=item.product_id,
                    product_name=product.name if product else "?",
                    shelf_id=item.shelf_id,
                    shelf_code=shelf.code if shelf else None,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                    tax_amount=item.tax_amount,
                )
            )

        return SaleDetailResponse(
            id=sale.id,
            customer_name=sale.customer_name,
            customer_email=sale.customer_email,
            customer_phone=sale.customer_phone,
            customer_document=sale.customer_document,
            customer_address=sale.customer_address,
            customer_id=sale.customer_id,
            total=sale.total,
            status=sale.status,
            payment_status=sale.payment_status,
            notes=sale.notes,
            created_by=sale.created_by,
            created_at=sale.created_at,
            items=item_responses,
        )

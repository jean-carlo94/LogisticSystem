from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.audit import AuditLogger
from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.core.pdf import get_pdf_renderer
from app.core.templates import render_template_string, validate_template_syntax
from app.modules.invoice_templates.default_template import DEFAULT_INVOICE_TEMPLATE
from app.modules.invoice_templates.model import InvoiceTemplate
from app.modules.invoice_templates.repository import InvoiceTemplateRepository
from app.modules.invoice_templates.schema import (
    InvoiceTemplateResponse, InvoiceTemplateUpdate, TemplateVariable,
)

if TYPE_CHECKING:
    from app.modules.payments.repository import PaymentRepository
    from app.modules.sales.repository import SaleItemRepository, SaleRepository
    from app.modules.shelves.repository import ShelfItemRepository
    from app.modules.tenants.repository import TenantRepository

logger = logging.getLogger(__name__)

TEMPLATE_VARIABLES: list[TemplateVariable] = [
    TemplateVariable(name="tenant_name", description="Nombre del negocio", category="tenant"),
    TemplateVariable(name="tenant_slug", description="Slug del tenant", category="tenant"),
    TemplateVariable(name="tenant_business_id", description="ID fiscal / RUT del negocio", category="tenant"),
    TemplateVariable(name="tenant_logo_url", description="URL del logo del negocio", category="tenant"),
    TemplateVariable(name="invoice_number", description="Número de factura (ID de venta)", category="sale"),
    TemplateVariable(name="invoice_date", description="Fecha y hora completa de la venta", category="sale"),
    TemplateVariable(name="invoice_date_short", description="Fecha de la venta (YYYY-MM-DD)", category="sale"),
    TemplateVariable(name="status", description="Estado de la venta (COMPLETED/CANCELLED)", category="sale"),
    TemplateVariable(name="payment_status", description="Estado de pago (PENDING/PAID/PARTIALLY_PAID/REFUNDED)", category="sale"),
    TemplateVariable(name="notes", description="Notas de la venta", category="sale"),
    TemplateVariable(name="customer_name", description="Nombre del cliente", category="customer"),
    TemplateVariable(name="customer_document", description="Documento/RUT del cliente", category="customer"),
    TemplateVariable(name="customer_email", description="Email del cliente", category="customer"),
    TemplateVariable(name="customer_phone", description="Teléfono del cliente", category="customer"),
    TemplateVariable(name="customer_address", description="Dirección del cliente", category="customer"),
    TemplateVariable(name="{% for item in items %}", description="Bucle de items de la venta", category="items"),
    TemplateVariable(name="item.product_name", description="Nombre del producto", category="items"),
    TemplateVariable(name="item.quantity", description="Cantidad", category="items"),
    TemplateVariable(name="item.unit_price", description="Precio unitario", category="items"),
    TemplateVariable(name="item.subtotal", description="Subtotal de línea", category="items"),
    TemplateVariable(name="item.tax_amount", description="Impuesto de línea", category="items"),
    TemplateVariable(name="{% for payment in payments %}", description="Bucle de pagos", category="payments"),
    TemplateVariable(name="payment.method", description="Método de pago (CASH/CARD/TRANSFER/WALLET/OTHER)", category="payments"),
    TemplateVariable(name="payment.amount", description="Monto del pago", category="payments"),
    TemplateVariable(name="payment.reference", description="Referencia del pago", category="payments"),
    TemplateVariable(name="subtotal", description="Subtotal antes de impuestos", category="sale"),
    TemplateVariable(name="tax_total", description="Total de impuestos", category="sale"),
    TemplateVariable(name="total", description="Total de la factura", category="sale"),
    TemplateVariable(name="auto_print", description="true si se activa window.print() al cargar", category="meta"),
]


class InvoiceTemplateService:
    def __init__(
        self,
        template_repo: InvoiceTemplateRepository,
        sale_repo: "SaleRepository",
        sale_item_repo: "SaleItemRepository",
        shelf_item_repo: "ShelfItemRepository",
        payment_repo: "PaymentRepository",
        tenant_repo: "TenantRepository",
        audit: AuditLogger,
    ):
        self.template_repo = template_repo
        self.sale_repo = sale_repo
        self.sale_item_repo = sale_item_repo
        self.shelf_item_repo = shelf_item_repo
        self.payment_repo = payment_repo
        self.tenant_repo = tenant_repo
        self.audit = audit

    async def get_template(self) -> InvoiceTemplateResponse:
        tid = self.template_repo._tenant_id
        if tid is None:
            raise ValidationException("Debe especificar un tenant")
        tmpl = await self.template_repo.get_by_tenant(tid)
        if not tmpl:
            tmpl = await self.template_repo.create(
                tenant_id=tid, html_content=DEFAULT_INVOICE_TEMPLATE
            )
        return InvoiceTemplateResponse.model_validate(tmpl)

    async def update_template(
        self, data: InvoiceTemplateUpdate, user_id: int
    ) -> InvoiceTemplateResponse:
        tid = self.template_repo._tenant_id
        if tid is None:
            raise ValidationException("Debe especificar un tenant")
        validate_template_syntax(data.html_content)
        tmpl = await self.template_repo.get_by_tenant(tid)
        if not tmpl:
            tmpl = await self.template_repo.create(
                tenant_id=tid, html_content=data.html_content
            )
            await self.audit.log_create("InvoiceTemplate", tmpl.id, user_id, tmpl)
        else:
            await self.template_repo.update(tmpl, html_content=data.html_content)
            await self.audit.log_update(
                "InvoiceTemplate", tmpl.id, user_id,
                {"action": "template_updated"},
            )
        return InvoiceTemplateResponse.model_validate(tmpl)

    @staticmethod
    def get_variables() -> list[TemplateVariable]:
        return list(TEMPLATE_VARIABLES)

    async def render_preview(self, sale_id: int | None = None) -> str:
        if sale_id:
            return await self.render_invoice_html(sale_id, auto_print=False)
        tmpl = await self._get_template_html()
        return render_template_string(tmpl, self._dummy_context())

    async def render_invoice_html(self, sale_id: int, auto_print: bool = False) -> str:
        context = await self._build_context(sale_id)
        context["auto_print"] = auto_print
        tmpl = await self._get_template_html()
        return render_template_string(tmpl, context)

    async def render_invoice_pdf(
        self, sale_id: int, regenerate: bool = False
    ) -> tuple[bytes, str]:
        sale = await self.sale_repo.get_by_id(sale_id)
        if not sale:
            raise NotFoundException("Venta no encontrada")

        if not regenerate and sale.invoice_pdf_path:
            pdf_bytes = await self._read_pdf_bytes(sale.invoice_pdf_path)
            if pdf_bytes is not None:
                filename = os.path.basename(sale.invoice_pdf_path)
                return pdf_bytes, filename

        html = await self.render_invoice_html(sale_id)
        renderer = get_pdf_renderer()
        pdf_bytes = await renderer.render(html)

        filename = f"factura_{sale.id}.pdf"
        relative_path = f"invoices/{sale.tenant_id}/{filename}"
        full_path = Path(settings.STORAGE_PATH) / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        import aiofiles
        async with aiofiles.open(full_path, "wb") as f:
            await f.write(pdf_bytes)

        await self.sale_repo.update(sale, invoice_pdf_path=relative_path)
        return pdf_bytes, filename

    async def _get_template_html(self) -> str:
        tid = self.template_repo._tenant_id
        if tid is None:
            raise ValidationException("Debe especificar un tenant")
        tmpl = await self.template_repo.get_by_tenant(tid)
        return tmpl.html_content if tmpl else DEFAULT_INVOICE_TEMPLATE

    async def _build_context(self, sale_id: int) -> dict:
        from app.core.storage import get_image_url

        sale = await self.sale_repo.get_by_id(sale_id)
        if not sale:
            raise NotFoundException("Venta no encontrada")

        items = await self.sale_item_repo.get_items_by_sale(sale_id)
        product_ids = list(set(i.product_id for i in items))
        products_map: dict = {}
        if product_ids:
            products = await self.shelf_item_repo.get_products_by_ids(product_ids)
            products_map = {p.id: p for p in products}

        payments_db = await self.payment_repo.get_by_sale(sale_id)
        payments = [
            {
                "method": p.method.value if hasattr(p.method, "value") else str(p.method),
                "amount": p.amount,
                "reference": p.reference,
            }
            for p in payments_db
        ]

        tenant = await self.tenant_repo.get_by_id(sale.tenant_id)

        context_items = []
        subtotal = 0.0
        for item in items:
            product = products_map.get(item.product_id)
            context_items.append({
                "product_name": product.name if product else "?",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal,
                "tax_amount": item.tax_amount,
            })
            subtotal += item.subtotal

        tax_total = round(sale.total - subtotal, 2) if subtotal else 0.0

        created_at = sale.created_at
        invoice_date = created_at.isoformat() if created_at else ""
        invoice_date_short = created_at.strftime("%Y-%m-%d") if created_at else ""

        return {
            "tenant_name": tenant.name if tenant else "",
            "tenant_slug": tenant.slug if tenant else "",
            "tenant_business_id": tenant.business_id if tenant else "",
            "tenant_logo_url": get_image_url(tenant.logo_path) if tenant and tenant.logo_path else "",
            "invoice_number": sale.id,
            "invoice_date": invoice_date,
            "invoice_date_short": invoice_date_short,
            "status": sale.status.value if hasattr(sale.status, "value") else str(sale.status),
            "payment_status": sale.payment_status,
            "customer_name": sale.customer_name,
            "customer_document": sale.customer_document or "",
            "customer_email": sale.customer_email or "",
            "customer_phone": sale.customer_phone or "",
            "customer_address": sale.customer_address or "",
            "notes": sale.notes or "",
            "items": context_items,
            "subtotal": round(subtotal, 2),
            "tax_total": tax_total,
            "total": sale.total,
            "payments": payments,
        }

    @staticmethod
    def _dummy_context() -> dict:
        return {
            "tenant_name": "Mi Negocio Demo",
            "tenant_slug": "demo",
            "tenant_business_id": "12345678-9",
            "tenant_logo_url": "",
            "invoice_number": 1001,
            "invoice_date": datetime.utcnow().isoformat(),
            "invoice_date_short": datetime.utcnow().strftime("%Y-%m-%d"),
            "status": "COMPLETED",
            "payment_status": "PAID",
            "customer_name": "Cliente Ejemplo",
            "customer_document": "11111111-1",
            "customer_email": "cliente@ejemplo.com",
            "customer_phone": "+56912345678",
            "customer_address": "Calle Falsa 123",
            "notes": "Gracias por su compra.",
            "items": [
                {"product_name": "Producto A", "quantity": 2, "unit_price": 1500.0, "subtotal": 3000.0, "tax_amount": 570.0},
                {"product_name": "Producto B", "quantity": 1, "unit_price": 5000.0, "subtotal": 5000.0, "tax_amount": 950.0},
            ],
            "subtotal": 8000.0,
            "tax_total": 1520.0,
            "total": 9520.0,
            "payments": [
                {"method": "CASH", "amount": 5000.0, "reference": None},
                {"method": "CARD", "amount": 4520.0, "reference": "Tx-ABC123"},
            ],
        }

    async def _read_pdf_bytes(self, relative_path: str) -> bytes | None:
        full_path = Path(settings.STORAGE_PATH) / relative_path
        if not full_path.exists():
            return None
        import aiofiles
        async with aiofiles.open(full_path, "rb") as f:
            return await f.read()

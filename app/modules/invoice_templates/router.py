from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, Response

from app.core.permissions import PermissionCode
from app.core.security import require_permission
from app.modules.invoice_templates.deps import get_invoice_template_service
from app.modules.invoice_templates.schema import (
    InvoiceTemplateResponse,
    InvoiceTemplateUpdate,
    TemplatePreviewRequest,
    TemplateVariable,
)
from app.modules.invoice_templates.service import InvoiceTemplateService

if TYPE_CHECKING:
    from app.modules.users.model import User

logger = logging.getLogger(__name__)

template_router = APIRouter(prefix="/invoice-templates", tags=["invoice_templates"])
invoice_router = APIRouter(prefix="/sales", tags=["invoice_templates"])


@template_router.get("/", response_model=InvoiceTemplateResponse)
async def get_template(
    service: InvoiceTemplateService = Depends(get_invoice_template_service),
    _perm: "User" = Depends(require_permission(PermissionCode.INVOICE_TEMPLATES_VIEW)),
):
    return await service.get_template()


@template_router.put("/", response_model=InvoiceTemplateResponse)
async def update_template(
    data: InvoiceTemplateUpdate,
    service: InvoiceTemplateService = Depends(get_invoice_template_service),
    user: "User" = Depends(require_permission(PermissionCode.INVOICE_TEMPLATES_EDIT)),
):
    return await service.update_template(data, user.id)


@template_router.get("/variables", response_model=list[TemplateVariable])
async def get_variables(
    _perm: "User" = Depends(require_permission(PermissionCode.INVOICE_TEMPLATES_VIEW)),
):
    return InvoiceTemplateService.get_variables()


@template_router.post("/preview", response_class=HTMLResponse)
async def preview_template(
    body: TemplatePreviewRequest = TemplatePreviewRequest(),
    service: InvoiceTemplateService = Depends(get_invoice_template_service),
    _perm: "User" = Depends(require_permission(PermissionCode.INVOICE_TEMPLATES_VIEW)),
):
    html = await service.render_preview(body.sale_id)
    return HTMLResponse(content=html)


@invoice_router.get("/{sale_id}/invoice/html", response_class=HTMLResponse)
async def invoice_html(
    sale_id: int,
    auto_print: bool = Query(default=False, description="Activar window.print() al cargar"),
    service: InvoiceTemplateService = Depends(get_invoice_template_service),
    _perm: "User" = Depends(require_permission(PermissionCode.SALES_VIEW_INVOICE)),
):
    html = await service.render_invoice_html(sale_id, auto_print=auto_print)
    return HTMLResponse(content=html)


@invoice_router.get("/{sale_id}/invoice/pdf")
async def invoice_pdf(
    sale_id: int,
    regenerate: bool = Query(default=False, description="Forzar regeneración"),
    service: InvoiceTemplateService = Depends(get_invoice_template_service),
    _perm: "User" = Depends(require_permission(PermissionCode.SALES_VIEW_INVOICE)),
):
    pdf_bytes, filename = await service.render_invoice_pdf(sale_id, regenerate=regenerate)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )

from datetime import datetime

from pydantic import BaseModel, Field


class InvoiceTemplateUpdate(BaseModel):
    html_content: str = Field(..., min_length=1, max_length=200_000)


class InvoiceTemplateResponse(BaseModel):
    id: int
    tenant_id: int
    html_content: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateVariable(BaseModel):
    name: str
    description: str
    category: str


class TemplatePreviewRequest(BaseModel):
    sale_id: int | None = None

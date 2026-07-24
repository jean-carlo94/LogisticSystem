from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.audit import AuditLogger, get_audit_logger
from app.modules.products.repository import ProductRepository
from app.modules.products.service import ProductService


def get_product_repository(db: Session = Depends(get_db)) -> ProductRepository:
    return ProductRepository(db)


def get_product_service(
    product_repo: ProductRepository = Depends(get_product_repository),
    audit: AuditLogger = Depends(get_audit_logger),
) -> ProductService:
    return ProductService(product_repo, audit)

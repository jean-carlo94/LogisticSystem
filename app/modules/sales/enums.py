from enum import Enum


class SaleStatus(str, Enum):
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

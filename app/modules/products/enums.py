from enum import Enum


class ProductState(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    NO_STOCK = "NO_STOCK"
    DISCONTINUED = "DISCONTINUED"

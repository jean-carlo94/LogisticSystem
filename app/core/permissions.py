from enum import Enum


class PermissionCode(str, Enum):
    PRODUCTS_CREATE = "products_create"
    PRODUCTS_READ = "products_read"
    PRODUCTS_UPDATE = "products_update"
    PRODUCTS_DELETE = "products_delete"
    EVENTS_READ = "events_read"
    ROLES_MANAGE = "roles_manage"
    USERS_MANAGE = "users_manage"
    SHELVES_CREATE = "shelves_create"
    SHELVES_READ = "shelves_read"
    SHELVES_UPDATE = "shelves_update"
    SHELVES_DELETE = "shelves_delete"

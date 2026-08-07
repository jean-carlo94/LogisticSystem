from enum import Enum


class PermissionCode(str, Enum):
    # Products
    PRODUCTS_VIEW = "products_view"
    PRODUCTS_CREATE = "products_create"
    PRODUCTS_EDIT = "products_edit"
    PRODUCTS_DELETE = "products_delete"
    PRODUCTS_UPLOAD_IMAGE = "products_upload_image"

    # Shelves
    SHELVES_VIEW = "shelves_view"
    SHELVES_CREATE = "shelves_create"
    SHELVES_EDIT = "shelves_edit"
    SHELVES_DELETE = "shelves_delete"
    SHELVES_ASSIGN_PRODUCTS = "shelves_assign_products"

    # Categories
    CATEGORIES_VIEW = "categories_view"
    CATEGORIES_CREATE = "categories_create"
    CATEGORIES_EDIT = "categories_edit"
    CATEGORIES_DELETE = "categories_delete"

    # Sales
    SALES_VIEW = "sales_view"
    SALES_CREATE = "sales_create"
    SALES_CANCEL = "sales_cancel"
    SALES_VIEW_INVOICE = "sales_view_invoice"

    # Orders
    ORDERS_VIEW = "orders_view"
    ORDERS_CREATE = "orders_create"
    ORDERS_EDIT = "orders_edit"
    ORDERS_CHANGE_STATE = "orders_change_state"

    # Stations
    STATIONS_VIEW = "stations_view"
    STATIONS_CREATE = "stations_create"
    STATIONS_EDIT = "stations_edit"
    STATIONS_DELETE = "stations_delete"
    STATIONS_OPEN_CLOSE = "stations_open_close"
    STATIONS_MANAGE_ITEMS = "stations_manage_items"

    # Cash Register
    CASH_REGISTER_VIEW = "cash_register_view"
    CASH_REGISTER_OPEN_CLOSE = "cash_register_open_close"
    CASH_REGISTER_MANAGE_REGISTERS = "cash_register_manage_registers"

    # Taxes
    TAXES_VIEW = "taxes_view"
    TAXES_CREATE = "taxes_create"
    TAXES_EDIT = "taxes_edit"
    TAXES_DELETE = "taxes_delete"

    # Customers
    CUSTOMERS_VIEW = "customers_view"
    CUSTOMERS_CREATE = "customers_create"
    CUSTOMERS_EDIT = "customers_edit"

    # Payments
    PAYMENTS_VIEW = "payments_view"
    PAYMENTS_CREATE = "payments_create"

    # Payment Methods
    PAYMENT_METHODS_VIEW = "payment_methods_view"
    PAYMENT_METHODS_CREATE = "payment_methods_create"
    PAYMENT_METHODS_EDIT = "payment_methods_edit"
    PAYMENT_METHODS_DELETE = "payment_methods_delete"

    # Users
    USERS_VIEW = "users_view"
    USERS_CREATE = "users_create"
    USERS_EDIT = "users_edit"
    USERS_DELETE = "users_delete"
    USERS_ASSIGN_ROLES = "users_assign_roles"
    USERS_SET_PIN = "users_set_pin"
    USERS_UPLOAD_IMAGE = "users_upload_image"

    # Roles
    ROLES_VIEW = "roles_view"
    ROLES_CREATE = "roles_create"
    ROLES_EDIT = "roles_edit"
    ROLES_DELETE = "roles_delete"
    ROLES_ASSIGN_PERMISSIONS = "roles_assign_permissions"

    # Tenants
    TENANTS_VIEW = "tenants_view"
    TENANTS_CREATE = "tenants_create"
    TENANTS_EDIT = "tenants_edit"
    TENANTS_DELETE = "tenants_delete"

    # Events
    EVENTS_VIEW = "events_view"

    # API Keys
    API_KEYS_VIEW = "api_keys_view"
    API_KEYS_CREATE = "api_keys_create"
    API_KEYS_EDIT = "api_keys_edit"
    API_KEYS_DELETE = "api_keys_delete"

    # Tenant Config
    TENANT_CONFIG_VIEW = "tenant_config_view"
    TENANT_CONFIG_EDIT = "tenant_config_edit"

    # Invoice Templates
    INVOICE_TEMPLATES_VIEW = "invoice_templates_view"
    INVOICE_TEMPLATES_EDIT = "invoice_templates_edit"

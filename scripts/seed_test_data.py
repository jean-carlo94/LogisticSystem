"""Seed test environment with 3 tenants.

Usage:
  pip install httpx
  # Clean DB first:
  docker compose down -v && docker compose up --build -d
  # Wait a few seconds, then:
  python scripts/seed_test_data.py [--base-url http://localhost:8000/api/v1]
"""

import asyncio
import sys
import httpx

BASE_URL = "http://localhost:8000/api/v1"
PLATFORM_EMAIL = "admin@alunatechnologies.com"
PLATFORM_PASSWORD = "admin123"
PASSWORD = "admin123"
OPER_PASSWORD = "oper123"
VIEW_PASSWORD = "view123"

import os
PLATFORM_EMAIL = os.environ.get("ADMIN_EMAIL", PLATFORM_EMAIL)
PLATFORM_PASSWORD = os.environ.get("ADMIN_PASSWORD", PLATFORM_PASSWORD)
PASSWORD = os.environ.get("SEED_ADMIN_PASSWORD", PASSWORD)
OPER_PASSWORD = os.environ.get("SEED_OPER_PASSWORD", OPER_PASSWORD)
VIEW_PASSWORD = os.environ.get("SEED_VIEW_PASSWORD", VIEW_PASSWORD)


async def api_post(client, path, data, token=None, expected=201):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = await client.post(f"{BASE_URL}{path}", json=data, headers=headers)
    if r.status_code != expected:
        print(f"  FAIL {path}: {r.status_code} {r.text[:200]}")
        return None
    if r.status_code == 204:
        return True
    return r.json()


async def api_put(client, path, data, token=None, expected=200):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = await client.put(f"{BASE_URL}{path}", json=data, headers=headers)
    if r.status_code != expected:
        print(f"  FAIL PUT {path}: {r.status_code} {r.text[:200]}")
        return None
    return r.json()


async def api_get(client, path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = await client.get(f"{BASE_URL}{path}", headers=headers)
    if r.status_code != 200:
        print(f"  FAIL GET {path}: {r.status_code} {r.text[:200]}")
        return None
    return r.json()


async def login(client, email, password):
    r = await client.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        print(f"  LOGIN FAIL for {email}: {r.status_code} {r.text[:200]}")
        sys.exit(1)
    return r.json()["access_token"]


async def create_user(client, token, email, password, first_name, last_name=""):
    result = await api_post(client, "/users/", {
        "email": email, "password": password,
        "first_name": first_name, "last_name": last_name,
    }, token=token)
    if result:
        await api_put(client, f"/users/{result['id']}", {"is_active": True}, token=token)
    return result


async def get_role_id(client, token, name):
    data = await api_get(client, f"/roles/?name={name}&size=50", token=token)
    if not data or not data.get("items"):
        print(f"  Role '{name}' not found")
        return None
    return data["items"][0]["id"]


async def assign_role(client, token, user_id, role_id):
    return await api_post(client, f"/users/{user_id}/roles", {"role_id": role_id}, token=token, expected=204)


async def create_category(client, token, name, description=""):
    return await api_post(client, "/categories/", {"name": name, "description": description}, token=token)


async def create_tax(client, token, name, rate, description=""):
    return await api_post(client, "/taxes/", {"name": name, "rate": rate, "description": description}, token=token)


async def create_product(client, token, name, price, stock, category_ids, tax_ids=None, barcode=None):
    payload = {"name": name, "price": price, "stock": stock}
    if category_ids:
        payload["category_ids"] = category_ids
    if tax_ids:
        payload["tax_ids"] = tax_ids
    if barcode:
        payload["barcode"] = barcode
    return await api_post(client, "/products/", payload, token=token)


async def create_shelf(client, token, name, code, aisle, row, level, max_weight=0, width=0, height=0, depth=0):
    return await api_post(client, "/shelves/", {
        "name": name, "code": code, "aisle": aisle, "row": row, "level": level,
        "max_weight_kg": max_weight, "width_cm": width, "height_cm": height, "depth_cm": depth,
    }, token=token)


async def add_shelf_item(client, token, shelf_id, product_id, quantity):
    return await api_post(client, f"/shelves/{shelf_id}/items", {
        "product_id": product_id, "quantity": quantity,
    }, token=token)


async def create_station(client, token, code, name="", area="", capacity=1):
    return await api_post(client, "/stations/", {
        "code": code, "name": name, "area": area, "capacity": capacity,
    }, token=token)


async def open_cash_register(client, token, name, opening_amount):
    return await api_post(client, "/cash-register/open", {
        "name": name, "opening_amount": opening_amount,
    }, token=token)


# ═══════════════════════════════════════════
#  TENANT DATA
# ═══════════════════════════════════════════

RESTAURANT_PRODUCTS = [
    # Categoría: Entradas
    ("Ceviche clásico", 8900, 30, "Entradas"),
    ("Empanadas de pino", 2500, 50, "Entradas"),
    ("Sopa del día", 4500, 20, "Entradas"),
    ("Tabla de quesos", 7900, 15, "Entradas"),
    # Categoría: Platos Principales
    ("Lomo salteado", 12900, 25, "Platos Principales"),
    ("Salmón a la parrilla", 14900, 20, "Platos Principales"),
    ("Risotto de hongos", 9900, 25, "Platos Principales"),
    ("Pollo al horno", 10900, 30, "Platos Principales"),
    ("Fetuccini Alfredo", 8900, 30, "Platos Principales"),
    # Categoría: Bebidas
    ("Agua mineral 500ml", 1500, 100, "Bebidas"),
    ("Coca-Cola 350ml", 2000, 80, "Bebidas"),
    ("Limonada natural", 3500, 40, "Bebidas"),
    ("Jugo de naranja natural", 4000, 30, "Bebidas"),
    # Categoría: Postres
    ("Tiramisú", 5900, 15, "Postres"),
    ("Crème brûlée", 4900, 12, "Postres"),
    ("Helado artesanal", 3500, 25, "Postres"),
    ("Brownie con helado", 6500, 18, "Postres"),
    # Categoría: Cócteles
    ("Pisco Sour", 5500, 40, "Cócteles"),
    ("Mojito clásico", 5000, 35, "Cócteles"),
    ("Margarita", 6000, 30, "Cócteles"),
]

RESTAURANT_CATEGORIES = ["Entradas", "Platos Principales", "Bebidas", "Postres", "Cócteles"]
RESTAURANT_STATIONS = [f"MESA-{i:02d}" for i in range(1, 11)] + ["DELIVERY"]


HARDWARE_CATEGORIES = [
    "Herramientas Manuales", "Herramientas Eléctricas", "Tornillería",
    "Materiales de Construcción", "Pinturas", "Electricidad", "Plomería", "Seguridad",
]

HARDWARE_PRODUCTS = [
    # Herramientas Manuales
    ("Martillo carpintero 16oz", 8900, 40, "Herramientas Manuales", "HW-001"),
    ("Destornillador Phillips #2", 3500, 60, "Herramientas Manuales", "HW-002"),
    ("Destornillador plano 6mm", 3000, 60, "Herramientas Manuales", "HW-003"),
    ("Llave inglesa 10\"", 12900, 30, "Herramientas Manuales", "HW-004"),
    ("Serrucho carpintero 18\"", 8500, 20, "Herramientas Manuales", "HW-005"),
    ("Alicate universal 8\"", 5500, 45, "Herramientas Manuales", "HW-006"),
    ("Juego llaves Allen 9 piezas", 4900, 50, "Herramientas Manuales", "HW-007"),
    ("Cinta métrica 5 metros", 2500, 70, "Herramientas Manuales", "HW-008"),
    ("Nivel de burbuja 40cm", 4500, 30, "Herramientas Manuales", "HW-009"),
    ("Espátula acero 4\"", 2000, 80, "Herramientas Manuales", "HW-010"),
    ("Lima metálica plana 8\"", 3200, 40, "Herramientas Manuales", "HW-011"),
    ("Llave de tubo 13mm", 4200, 35, "Herramientas Manuales", "HW-012"),
    ("Pinza de presión 10\"", 6500, 25, "Herramientas Manuales", "HW-013"),
    ("Cincel acero 12mm", 2800, 50, "Herramientas Manuales", "HW-014"),
    # Herramientas Eléctricas
    ("Taladro percutor 650W", 49900, 15, "Herramientas Eléctricas", "HE-001"),
    ("Sierra circular 7¼\" 1200W", 79900, 8, "Herramientas Eléctricas", "HE-002"),
    ("Amoladora angular 4½\" 850W", 35900, 12, "Herramientas Eléctricas", "HE-003"),
    ("Lijadora orbital 300W", 29900, 10, "Herramientas Eléctricas", "HE-004"),
    ("Pistola de calor 2000W", 19900, 18, "Herramientas Eléctricas", "HE-005"),
    ("Soldadora inverter 130A", 129900, 5, "Herramientas Eléctricas", "HE-006"),
    ("Rotomartillo SDS 800W", 69900, 6, "Herramientas Eléctricas", "HE-007"),
    ("Atornillador eléctrico 3.6V", 24900, 20, "Herramientas Eléctricas", "HE-008"),
    ("Sierra caladora 500W", 39900, 7, "Herramientas Eléctricas", "HE-009"),
    ("Esmeril de banco 6\" 250W", 45900, 5, "Herramientas Eléctricas", "HE-010"),
    ("Hidrolavadora 1400W", 89900, 8, "Herramientas Eléctricas", "HE-011"),
    ("Compresor 24L 1.5HP", 99900, 4, "Herramientas Eléctricas", "HE-012"),
    # Tornillería
    ("Tornillo madera 4x40 caja 100u", 1800, 200, "Tornillería", "TO-001"),
    ("Tornillo drywall 6x1\" caja 100u", 1500, 150, "Tornillería", "TO-002"),
    ("Tuerca M8 galvanizada", 150, 500, "Tornillería", "TO-003"),
    ("Tuerca M10 inoxidable", 250, 400, "Tornillería", "TO-004"),
    ("Arandela plana M8", 50, 800, "Tornillería", "TO-005"),
    ("Arandela grower M10", 80, 600, "Tornillería", "TO-006"),
    ("Perno coche M8x40 c/ tuerca", 300, 300, "Tornillería", "TO-007"),
    ("Tirafondos 10x80mm", 400, 200, "Tornillería", "TO-008"),
    ("Clavos 2\" bolsa 500g", 2200, 100, "Tornillería", "TO-009"),
    ("Remaches aluminio 4x8 caja 100u", 1900, 80, "Tornillería", "TO-010"),
    ("Abrazadera metálica 1½\"", 350, 250, "Tornillería", "TO-011"),
    ("Tarugo plástico 8mm bolsa 50u", 1200, 120, "Tornillería", "TO-012"),
    ("Golilla plana 3/8\"", 60, 700, "Tornillería", "TO-013"),
    # Materiales de Construcción
    ("Cemento Portland 25kg", 4500, 80, "Materiales de Construcción", "MC-001"),
    ("Yeso construcción 1kg", 1200, 150, "Materiales de Construcción", "MC-002"),
    ("Arena fina saco 20kg", 2800, 60, "Materiales de Construcción", "MC-003"),
    ("Ladrillo fiscal 7x14x28", 350, 500, "Materiales de Construcción", "MC-004"),
    ("Cerámica 60x60cm m²", 8500, 50, "Materiales de Construcción", "MC-005"),
    ("Pegamento cerámico 25kg", 6500, 40, "Materiales de Construcción", "MC-006"),
    ("Fragüe blanco 1kg", 1800, 80, "Materiales de Construcción", "MC-007"),
    ("Malla construcción 2x3m", 5500, 30, "Materiales de Construcción", "MC-008"),
    ("Panel yeso-cartón 1.20x2.40m", 8900, 25, "Materiales de Construcción", "MC-009"),
    ("Barrilla 12mm x 6m", 4500, 60, "Materiales de Construcción", "MC-010"),
    ("Perfil metálico 40mm x 3m", 3800, 70, "Materiales de Construcción", "MC-011"),
    ("Madera pino 2x4\" x 3.2m", 5500, 45, "Materiales de Construcción", "MC-012"),
    ("Mortero seco saco 30kg", 3800, 40, "Materiales de Construcción", "MC-013"),
    # Pinturas
    ("Látex blanco 5L", 15500, 40, "Pinturas", "PI-001"),
    ("Látex blanco 20L", 45000, 20, "Pinturas", "PI-002"),
    ("Látex color 5L", 18500, 35, "Pinturas", "PI-003"),
    ("Esmalte sintético blanco 1L", 7500, 50, "Pinturas", "PI-004"),
    ("Esmalte sintético negro 1L", 7500, 45, "Pinturas", "PI-005"),
    ("Barniz marino 1L", 9500, 30, "Pinturas", "PI-006"),
    ("Aguarrás 1L", 2500, 80, "Pinturas", "PI-007"),
    ("Anticorrosivo rojo 1L", 8500, 35, "Pinturas", "PI-008"),
    ("Impermeabilizante 5L", 22000, 20, "Pinturas", "PI-009"),
    ("Brocha cerda 3\"", 3500, 60, "Pinturas", "PI-010"),
    ("Rodillo lana 22cm", 4500, 50, "Pinturas", "PI-011"),
    ("Cinta enmascarar 24mm x 40m", 2800, 90, "Pinturas", "PI-012"),
    # Electricidad
    ("Cable 2.5mm rollo 100m", 19800, 30, "Electricidad", "EL-001"),
    ("Cable 4mm rollo 100m", 28000, 25, "Electricidad", "EL-002"),
    ("Enchufe Schuko 16A", 3500, 80, "Electricidad", "EL-003"),
    ("Interruptor simple 10A", 2500, 100, "Electricidad", "EL-004"),
    ("Tomacorriente doble 16A", 4500, 70, "Electricidad", "EL-005"),
    ("Cinta aislante 19mm x 20m", 1500, 120, "Electricidad", "EL-006"),
    ("Disyuntor 25A bipolar", 8900, 30, "Electricidad", "EL-007"),
    ("Foco LED 12W E27", 2800, 150, "Electricidad", "EL-008"),
    ("Tubo fluorescente LED 18W", 5500, 60, "Electricidad", "EL-009"),
    ("Canaleta plástica 20x10mm x 2m", 2200, 50, "Electricidad", "EL-010"),
    ("Multímetro digital", 15900, 20, "Electricidad", "EL-011"),
    ("Puesta a tierra varilla 1.5m", 8500, 25, "Electricidad", "EL-012"),
    # Plomería
    ("Tubería PVC 50mm x 3m", 7500, 40, "Plomería", "PL-001"),
    ("Codo PVC 50mm 90°", 850, 100, "Plomería", "PL-002"),
    ("Tee PVC 50mm", 1200, 80, "Plomería", "PL-003"),
    ("Pegamento PVC 250ml", 3500, 50, "Plomería", "PL-004"),
    ("Cinta teflón 12mm x 10m", 800, 150, "Plomería", "PL-005"),
    ("Llave de paso ½\"", 4500, 60, "Plomería", "PL-006"),
    ("Flexible WC 40cm", 3200, 40, "Plomería", "PL-007"),
    ("Sifón lavamanos 1¼\"", 2800, 35, "Plomería", "PL-008"),
    ("Grifo monomando cocina", 28900, 15, "Plomería", "PL-009"),
    ("Ducha eléctrica 5500W", 49900, 10, "Plomería", "PL-010"),
    ("Tanque sanitario completo", 35900, 12, "Plomería", "PL-011"),
    ("Soldador estaño 60W", 5500, 25, "Plomería", "PL-012"),
    # Seguridad
    ("Casco de seguridad", 4500, 50, "Seguridad", "SE-001"),
    ("Guantes de trabajo", 2500, 80, "Seguridad", "SE-002"),
    ("Lentes de protección", 3500, 60, "Seguridad", "SE-003"),
    ("Mascarilla N95 caja 10u", 12000, 30, "Seguridad", "SE-004"),
    ("Tapones auditivos caja 50p", 8500, 25, "Seguridad", "SE-005"),
    ("Chaleco reflectante", 7500, 40, "Seguridad", "SE-006"),
    ("Arnés de seguridad", 45000, 8, "Seguridad", "SE-007"),
    ("Botas de seguridad N°42", 35000, 20, "Seguridad", "SE-008"),
    ("Extintor CO2 5kg", 35000, 10, "Seguridad", "SE-009"),
    ("Señalética salida emergencia", 5500, 15, "Seguridad", "SE-010"),
    ("Candado laminado 40mm", 4500, 50, "Seguridad", "SE-011"),
    ("Cadena eslabonada 8mm x 1m", 3500, 30, "Seguridad", "SE-012"),
]

HARDWARE_SHELVES = [
    {"name": "Estantería A - Herramientas", "code": "A-01", "aisle": "A", "row": 1, "level": 3, "max_weight_kg": 300, "width_cm": 200, "height_cm": 50, "depth_cm": 40},
    {"name": "Estantería B - Tornillería", "code": "B-01", "aisle": "B", "row": 1, "level": 3, "max_weight_kg": 200, "width_cm": 200, "height_cm": 40, "depth_cm": 30},
    {"name": "Estantería C - Materiales", "code": "C-01", "aisle": "C", "row": 1, "level": 2, "max_weight_kg": 500, "width_cm": 200, "height_cm": 60, "depth_cm": 50},
    {"name": "Estantería D - Pinturas", "code": "D-01", "aisle": "D", "row": 1, "level": 3, "max_weight_kg": 250, "width_cm": 200, "height_cm": 50, "depth_cm": 40},
    {"name": "Estantería E - Electricidad", "code": "E-01", "aisle": "E", "row": 1, "level": 3, "max_weight_kg": 150, "width_cm": 200, "height_cm": 40, "depth_cm": 30},
    {"name": "Estantería F - Plomería y Seguridad", "code": "F-01", "aisle": "F", "row": 1, "level": 3, "max_weight_kg": 200, "width_cm": 200, "height_cm": 50, "depth_cm": 40},
]


HOTEL_PRODUCTS = [
    # Minibar
    ("Agua mineral 500ml", 1500, 200, "Minibar"),
    ("Refresco lata 350ml", 2000, 150, "Minibar"),
    ("Cerveza artesanal 330ml", 4500, 100, "Minibar"),
    ("Snack mix 150g", 3500, 80, "Minibar"),
    # Room Service
    ("Desayuno continental", 8500, 50, "Room Service"),
    ("Club sandwich", 7500, 40, "Room Service"),
    ("Ensalada César", 6500, 35, "Room Service"),
    ("Burger clásica", 9500, 45, "Room Service"),
    ("Cena 3 tiempos", 18500, 25, "Room Service"),
    # Amenities
    ("Kit amenities estándar", 5000, 120, "Amenities"),
    ("Bata de baño", 15000, 60, "Amenities"),
    ("Pantuflas desechables", 3500, 150, "Amenities"),
    # Bebidas
    ("Café espresso", 2500, 200, "Bebidas"),
    ("Té variedad", 2000, 180, "Bebidas"),
    ("Chocolate caliente", 3000, 100, "Bebidas"),
]

HOTEL_CATEGORIES = ["Minibar", "Room Service", "Amenities", "Bebidas"]


# ═══════════════════════════════════════════
#  SEED FUNCTIONS
# ═══════════════════════════════════════════

async def seed_restaurant(client, token):
    print("\n── Restaurante ──")

    operator_id = None
    viewer_id = None
    cajero_id = None

    # Users
    op = await create_user(client, token, "mesero@restaurante.demo", OPER_PASSWORD, "Carlos", "Mesero")
    vw = await create_user(client, token, "viewer@restaurante.demo", VIEW_PASSWORD, "Viewer", "Rest")
    cj = await create_user(client, token, "cajero@restaurante.demo", OPER_PASSWORD, "Laura", "Cajera")
    if op:
        operator_id = op["id"]
    if vw:
        viewer_id = vw["id"]
    if cj:
        cajero_id = cj["id"]
    print(f"  Users: admin + 3 extras")

    op_role = await get_role_id(client, token, "Operator")
    vw_role = await get_role_id(client, token, "Viewer")
    if operator_id and op_role:
        await assign_role(client, token, operator_id, op_role)
    if cajero_id and op_role:
        await assign_role(client, token, cajero_id, op_role)
    if viewer_id and vw_role:
        await assign_role(client, token, viewer_id, vw_role)
    print("  Roles assigned")

    # Categories
    cat_ids = {}
    for name in RESTAURANT_CATEGORIES:
        r = await create_category(client, token, name)
        if r:
            cat_ids[name] = r["id"]
    print(f"  Categories: {len(cat_ids)}")

    # Tax
    tax = await create_tax(client, token, "IVA 19%", 19.0)
    tax_ids = [tax["id"]] if tax else []
    print("  Tax: IVA 19%")

    # Products
    count = 0
    for i, (name, price, stock, cat) in enumerate(RESTAURANT_PRODUCTS, 1):
        cat_id = cat_ids.get(cat)
        bc = f"REST-{i:03d}"
        r = await create_product(client, token, name, price, stock, [cat_id] if cat_id else [], tax_ids, bc)
        if r:
            count += 1
    print(f"  Products: {count}")

    # Stations
    st_count = 0
    for code in RESTAURANT_STATIONS:
        area = "DELIVERY" if code == "DELIVERY" else "SALÓN"
        name = f"Delivery" if code == "DELIVERY" else f"Mesa {code.split('-')[1]}"
        r = await create_station(client, token, code, name, area, 4 if code != "DELIVERY" else 1)
        if r:
            st_count += 1
    print(f"  Stations: {st_count}")

    # Cash register
    await open_cash_register(client, token, "Caja Restaurante", 50000)
    print("  Cash register: open")


async def seed_hardware(client, token):
    print("\n── Ferretería ──")

    operator_id = None
    viewer_id = None
    cajero1_id = None

    # Users
    op = await create_user(client, token, "vendedor@ferreteria.demo", OPER_PASSWORD, "Pedro", "Vendedor")
    vw = await create_user(client, token, "viewer@ferreteria.demo", VIEW_PASSWORD, "Viewer", "Ferre")
    cj1 = await create_user(client, token, "cajero1@ferreteria.demo", OPER_PASSWORD, "Ana", "Cajera")
    if op:
        operator_id = op["id"]
    if vw:
        viewer_id = vw["id"]
    if cj1:
        cajero1_id = cj1["id"]
    print(f"  Users: admin + 3 extras")

    op_role = await get_role_id(client, token, "Operator")
    vw_role = await get_role_id(client, token, "Viewer")
    if operator_id and op_role:
        await assign_role(client, token, operator_id, op_role)
    if cajero1_id and op_role:
        await assign_role(client, token, cajero1_id, op_role)
    if viewer_id and vw_role:
        await assign_role(client, token, viewer_id, vw_role)
    print("  Roles assigned")

    # Categories
    cat_ids = {}
    for name in HARDWARE_CATEGORIES:
        r = await create_category(client, token, name)
        if r:
            cat_ids[name] = r["id"]
    print(f"  Categories: {len(cat_ids)}")

    # Tax
    tax = await create_tax(client, token, "IVA 19%", 19.0)
    tax_ids = [tax["id"]] if tax else []
    print("  Tax: IVA 19%")

    # Products
    product_ids = {}  # index → id
    count = 0
    for i, (name, price, stock, cat, barcode) in enumerate(HARDWARE_PRODUCTS, 1):
        cat_id = cat_ids.get(cat)
        r = await create_product(client, token, name, price, stock, [cat_id] if cat_id else [], tax_ids, barcode)
        if r:
            count += 1
            product_ids[i - 1] = r["id"]
    print(f"  Products: {count}")

    # Shelves
    shelf_ids = []
    for cfg in HARDWARE_SHELVES:
        r = await create_shelf(client, token, cfg["name"], cfg["code"], cfg["aisle"],
                               cfg["row"], cfg["level"], cfg["max_weight_kg"],
                               cfg["width_cm"], cfg["height_cm"], cfg["depth_cm"])
        if r:
            shelf_ids.append(r["id"])
    print(f"  Shelves: {len(shelf_ids)}")

    # Assign products to shelves (small quantities to not exceed stock)
    if shelf_ids and product_ids:
        shelf_assignments = allocate_products_to_shelves(product_ids, shelf_ids)
        assigned = 0
        for prod_idx, shelf_idx in shelf_assignments:
            qty = 2 + (prod_idx % 4)  # 2-5 units per shelf item
            r = await add_shelf_item(client, token, shelf_ids[shelf_idx], product_ids[prod_idx], qty)
            if r is not None:
                assigned += 1
        print(f"  Shelf items: {assigned}")
    else:
        print("  Shelf items: skipped (missing shelves or products)")

    # Cash registers (admin + cajero1)
    await open_cash_register(client, token, "Caja Principal", 100000)
    cj1_token = await login(client, "cajero1@ferreteria.demo", OPER_PASSWORD)
    await open_cash_register(client, cj1_token, "Caja Secundaria", 50000)
    print("  Cash registers: 2 open")


def allocate_products_to_shelves(product_ids, shelf_ids):
    """Distribute ALL product indices across shelf indices (round-robin)."""
    n_shelves = len(shelf_ids)
    return [(i, i % n_shelves) for i in range(len(product_ids))]


async def seed_hotel(client, token):
    print("\n── Hotel ──")

    operator_id = None
    viewer_id = None

    # Users
    op = await create_user(client, token, "recepcionista@hotel.demo", OPER_PASSWORD, "María", "Recepción")
    vw = await create_user(client, token, "viewer@hotel.demo", VIEW_PASSWORD, "Viewer", "Hotel")
    cj1 = await create_user(client, token, "cajero-recepcion@hotel.demo", OPER_PASSWORD, "Lucía", "Cajera Recepción")
    cj2 = await create_user(client, token, "cajero-bar@hotel.demo", OPER_PASSWORD, "Diego", "Cajero Bar")
    cj3 = await create_user(client, token, "cajero-noche@hotel.demo", OPER_PASSWORD, "Andrés", "Cajero Nocturno")
    cajeros = [cj1, cj2, cj3]
    if op:
        operator_id = op["id"]
    if vw:
        viewer_id = vw["id"]
    print(f"  Users: admin + 5 extras")

    op_role = await get_role_id(client, token, "Operator")
    vw_role = await get_role_id(client, token, "Viewer")
    if operator_id and op_role:
        await assign_role(client, token, operator_id, op_role)
    for cj in cajeros:
        if cj and op_role:
            await assign_role(client, token, cj["id"], op_role)
    if viewer_id and vw_role:
        await assign_role(client, token, viewer_id, vw_role)
    print("  Roles assigned")

    # Categories
    cat_ids = {}
    for name in HOTEL_CATEGORIES:
        r = await create_category(client, token, name)
        if r:
            cat_ids[name] = r["id"]
    print(f"  Categories: {len(cat_ids)}")

    # Tax
    tax = await create_tax(client, token, "IVA 19%", 19.0)
    tax_ids = [tax["id"]] if tax else []
    print("  Tax: IVA 19%")

    # Products
    count = 0
    for i, (name, price, stock, cat) in enumerate(HOTEL_PRODUCTS, 1):
        cat_id = cat_ids.get(cat)
        bc = f"HTL-{i:03d}"
        r = await create_product(client, token, name, price, stock, [cat_id] if cat_id else [], tax_ids, bc)
        if r:
            count += 1
    print(f"  Products: {count}")

    # Stations (rooms)
    st_count = 0
    for i in range(101, 121):
        code = f"HAB-{i}"
        cap = 2 if i % 2 == 0 else 4
        r = await create_station(client, token, code, f"Habitación {i}", "HABITACIONES", cap)
        if r:
            st_count += 1
    print(f"  Stations: {st_count}")

    # Cash registers (admin + cajeros)
    await open_cash_register(client, token, "Caja Recepción", 200000)
    cj1_token = await login(client, "cajero-recepcion@hotel.demo", OPER_PASSWORD)
    await open_cash_register(client, cj1_token, "Caja Bar", 50000)
    cj2_token = await login(client, "cajero-bar@hotel.demo", OPER_PASSWORD)
    await open_cash_register(client, cj2_token, "Caja Restaurante", 50000)
    cj3_token = await login(client, "cajero-noche@hotel.demo", OPER_PASSWORD)
    await open_cash_register(client, cj3_token, "Caja Turno Noche", 30000)
    print("  Cash registers: 4 open")


# ═══════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════

async def main():
    global BASE_URL, PLATFORM_EMAIL, PLATFORM_PASSWORD
    if len(sys.argv) > 1 and sys.argv[1] == "--base-url" and len(sys.argv) > 2:
        BASE_URL = sys.argv[2]
    # Allow env override for platform creds
    import os as _os
    global PLATFORM_EMAIL, PLATFORM_PASSWORD
    PLATFORM_EMAIL = _os.environ.get("ADMIN_EMAIL", PLATFORM_EMAIL)
    PLATFORM_PASSWORD = _os.environ.get("ADMIN_PASSWORD", PLATFORM_PASSWORD)

    print(f"Base URL: {BASE_URL}")
    timeout = httpx.Timeout(30.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        print("\n── Platform login ──")
        platform_token = await login(client, PLATFORM_EMAIL, PLATFORM_PASSWORD)
        print("  OK")

        # ═════════════════════════════════════
        #  Create tenants
        # ═════════════════════════════════════

        print("\n── Creating tenants ──")

        r = await api_post(client, "/tenants/", {
            "name": "Restaurante Demo", "slug": "restaurante-demo",
            "admin_email": "admin@restaurante.demo", "admin_password": PASSWORD,
        }, token=platform_token)
        print(f"  Restaurante: {'OK' if r else 'FAIL'}")

        r = await api_post(client, "/tenants/", {
            "name": "Ferretería Demo", "slug": "ferreteria-demo",
            "admin_email": "admin@ferreteria.demo", "admin_password": PASSWORD,
        }, token=platform_token)
        print(f"  Ferretería: {'OK' if r else 'FAIL'}")

        r = await api_post(client, "/tenants/", {
            "name": "Hotel Demo", "slug": "hotel-demo",
            "admin_email": "admin@hotel.demo", "admin_password": PASSWORD,
        }, token=platform_token)
        print(f"  Hotel: {'OK' if r else 'FAIL'}")

        # ═════════════════════════════════════
        #  Seed each tenant
        # ═════════════════════════════════════

        # Restaurante
        token = await login(client, "admin@restaurante.demo", PASSWORD)
        await seed_restaurant(client, token)

        # Ferretería
        token = await login(client, "admin@ferreteria.demo", PASSWORD)
        await seed_hardware(client, token)

        # Hotel
        token = await login(client, "admin@hotel.demo", PASSWORD)
        await seed_hotel(client, token)

    print("\n── Done ──")


if __name__ == "__main__":
    asyncio.run(main())

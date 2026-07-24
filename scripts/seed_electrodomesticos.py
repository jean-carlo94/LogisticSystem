"""
Seed de prueba: 200 electrodomésticos, 200 estanterías, 200 usuarios.
Ejecutar: python scripts/seed_electrodomesticos.py
"""
import asyncio
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.core.config import settings
from app.core.database import _get_sessionmaker
from app.core.security import hash_password
from app.modules.products.model import Product
from app.modules.products.enums import ProductState
from app.modules.shelves.model import Shelf, ShelfItem
from app.modules.users.model import User
from app.modules.roles.model import Permission, Role, RolePermission, UserRole

PRODUCTOS = [
    {"name": "Refrigerador Samsung 400L", "price": 599990, "weight_kg": 75.0, "width_cm": 70, "height_cm": 180, "depth_cm": 70},
    {"name": "Refrigerador LG 350L", "price": 499990, "weight_kg": 68.0, "width_cm": 65, "height_cm": 175, "depth_cm": 65},
    {"name": "Refrigerador Mabe 300L", "price": 399990, "weight_kg": 60.0, "width_cm": 60, "height_cm": 170, "depth_cm": 60},
    {"name": "Lavadora Samsung 20kg", "price": 459990, "weight_kg": 70.0, "width_cm": 65, "height_cm": 110, "depth_cm": 65},
    {"name": "Lavadora LG 18kg", "price": 399990, "weight_kg": 65.0, "width_cm": 60, "height_cm": 105, "depth_cm": 60},
    {"name": "Lavadora Mabe 16kg", "price": 349990, "weight_kg": 60.0, "width_cm": 58, "height_cm": 100, "depth_cm": 58},
    {"name": "Secadora Samsung 18kg", "price": 429990, "weight_kg": 50.0, "width_cm": 60, "height_cm": 85, "depth_cm": 60},
    {"name": "Secadora LG 16kg", "price": 379990, "weight_kg": 45.0, "width_cm": 58, "height_cm": 80, "depth_cm": 55},
    {"name": "Lavasecadora Electrolux 12kg", "price": 549990, "weight_kg": 72.0, "width_cm": 60, "height_cm": 85, "depth_cm": 55},
    {"name": "TV Samsung 65\" QLED", "price": 899990, "weight_kg": 25.0, "width_cm": 145, "height_cm": 85, "depth_cm": 6},
    {"name": "TV LG 55\" OLED", "price": 799990, "weight_kg": 19.0, "width_cm": 123, "height_cm": 72, "depth_cm": 5},
    {"name": "TV Sony 75\" Bravia", "price": 1299990, "weight_kg": 35.0, "width_cm": 168, "height_cm": 97, "depth_cm": 7},
    {"name": "TV Xiaomi 50\" 4K", "price": 349990, "weight_kg": 10.0, "width_cm": 112, "height_cm": 65, "depth_cm": 4},
    {"name": "TV Hisense 43\"", "price": 229990, "weight_kg": 8.0, "width_cm": 96, "height_cm": 56, "depth_cm": 3},
    {"name": "Microondas Samsung 32L", "price": 89990, "weight_kg": 14.0, "width_cm": 52, "height_cm": 30, "depth_cm": 40},
    {"name": "Microondas LG 28L", "price": 69990, "weight_kg": 12.0, "width_cm": 48, "height_cm": 28, "depth_cm": 38},
    {"name": "Microondas Panasonic 25L", "price": 59990, "weight_kg": 11.0, "width_cm": 45, "height_cm": 26, "depth_cm": 35},
    {"name": "Horno eléctrico 45L", "price": 79990, "weight_kg": 18.0, "width_cm": 55, "height_cm": 35, "depth_cm": 45},
    {"name": "Horno empotrable 60cm", "price": 149990, "weight_kg": 32.0, "width_cm": 60, "height_cm": 60, "depth_cm": 55},
    {"name": "Cocina a gas 4 quemadores", "price": 199990, "weight_kg": 45.0, "width_cm": 60, "height_cm": 90, "depth_cm": 60},
    {"name": "Encimera inducción 4 puestos", "price": 299990, "weight_kg": 10.0, "width_cm": 60, "height_cm": 5, "depth_cm": 52},
    {"name": "Campana extractora 60cm", "price": 89990, "weight_kg": 8.0, "width_cm": 60, "height_cm": 15, "depth_cm": 50},
    {"name": "Licuadora Oster 1.5L", "price": 39990, "weight_kg": 3.0, "width_cm": 20, "height_cm": 35, "depth_cm": 18},
    {"name": "Licuadora Philips 2L", "price": 49990, "weight_kg": 3.5, "width_cm": 22, "height_cm": 38, "depth_cm": 20},
    {"name": "Batidora KitchenAid 4.8L", "price": 299990, "weight_kg": 12.0, "width_cm": 36, "height_cm": 35, "depth_cm": 22},
    {"name": "Cafetera espresso Breville", "price": 199990, "weight_kg": 7.0, "width_cm": 31, "height_cm": 33, "depth_cm": 28},
    {"name": "Cafetera goteo Moulinex", "price": 29990, "weight_kg": 2.5, "width_cm": 22, "height_cm": 30, "depth_cm": 18},
    {"name": "Cafetera Nespresso Inissia", "price": 69990, "weight_kg": 2.4, "width_cm": 12, "height_cm": 23, "depth_cm": 32},
    {"name": "Tostadora Oster 2 ranuras", "price": 24990, "weight_kg": 1.5, "width_cm": 28, "height_cm": 20, "depth_cm": 18},
    {"name": "Freidora aire Philips 4.1L", "price": 89990, "weight_kg": 5.5, "width_cm": 36, "height_cm": 30, "depth_cm": 36},
    {"name": "Freidora aire Oster 3.5L", "price": 49990, "weight_kg": 4.5, "width_cm": 30, "height_cm": 28, "depth_cm": 30},
    {"name": "Arrocera Imusa 3L", "price": 29990, "weight_kg": 2.5, "width_cm": 26, "height_cm": 25, "depth_cm": 26},
    {"name": "Olla arrocera Oster 1.8L", "price": 22990, "weight_kg": 2.0, "width_cm": 22, "height_cm": 22, "depth_cm": 22},
    {"name": "Olla presión eléctrica 6L", "price": 69990, "weight_kg": 5.0, "width_cm": 32, "height_cm": 32, "depth_cm": 30},
    {"name": "Plancha a vapor Philips", "price": 24990, "weight_kg": 1.2, "width_cm": 15, "height_cm": 25, "depth_cm": 12},
    {"name": "Aspiradora Samsung 2000W", "price": 89990, "weight_kg": 6.0, "width_cm": 28, "height_cm": 25, "depth_cm": 40},
    {"name": "Aspiradora robot Xiaomi", "price": 199990, "weight_kg": 3.5, "width_cm": 35, "height_cm": 10, "depth_cm": 35},
    {"name": "Aspiradora escoba Dyson V11", "price": 449990, "weight_kg": 2.9, "width_cm": 25, "height_cm": 125, "depth_cm": 25},
    {"name": "Ventilador pedestal 45cm", "price": 34990, "weight_kg": 6.0, "width_cm": 45, "height_cm": 130, "depth_cm": 45},
    {"name": "Ventilador torre 80cm", "price": 49990, "weight_kg": 5.0, "width_cm": 20, "height_cm": 80, "depth_cm": 20},
    {"name": "Calefactor eléctrico 2000W", "price": 39990, "weight_kg": 3.0, "width_cm": 20, "height_cm": 40, "depth_cm": 15},
    {"name": "Aire acondicionado split 12000BTU", "price": 349990, "weight_kg": 35.0, "width_cm": 85, "height_cm": 30, "depth_cm": 22},
    {"name": "Aire acondicionado portátil 10000BTU", "price": 249990, "weight_kg": 28.0, "width_cm": 44, "height_cm": 70, "depth_cm": 36},
    {"name": "Calefont a gas 10L", "price": 119990, "weight_kg": 12.0, "width_cm": 33, "height_cm": 55, "depth_cm": 18},
    {"name": "Termo eléctrico 50L", "price": 129990, "weight_kg": 22.0, "width_cm": 45, "height_cm": 60, "depth_cm": 45},
    {"name": "Purificador de aire Xiaomi", "price": 89990, "weight_kg": 5.0, "width_cm": 24, "height_cm": 52, "depth_cm": 24},
    {"name": "Deshumidificador 20L", "price": 99990, "weight_kg": 13.0, "width_cm": 35, "height_cm": 50, "depth_cm": 25},
    {"name": "Estufa halógena 1200W", "price": 19990, "weight_kg": 2.5, "width_cm": 30, "height_cm": 50, "depth_cm": 20},
    {"name": "Hervidor eléctrico 1.7L", "price": 15990, "weight_kg": 1.0, "width_cm": 16, "height_cm": 24, "depth_cm": 16},
    {"name": "Sandwichera 2 puestos", "price": 14990, "weight_kg": 1.8, "width_cm": 24, "height_cm": 10, "depth_cm": 24},
]

NOMBRES = ["Carlos", "María", "José", "Ana", "Luis", "Isabel", "Pedro", "Carmen", "Juan", "Laura",
           "Miguel", "Sofía", "Diego", "Valentina", "Andrés", "Gabriela", "Fernando", "Daniela",
           "Ricardo", "Paula"]
APELLIDOS = ["García", "López", "Martínez", "Rodríguez", "Hernández", "González", "Pérez", "Sánchez",
             "Ramírez", "Torres", "Flores", "Rivera", "Morales", "Ortiz", "Vargas", "Rojas", "Castro",
             "Díaz", "Álvarez", "Romero"]
CIUDADES = ["Santiago", "Valparaíso", "Concepción", "Antofagasta", "Viña del Mar", "La Serena",
            "Temuco", "Rancagua", "Iquique", "Puerto Montt"]
PAISES = ["Chile", "Argentina", "Perú", "Colombia", "Ecuador", "Uruguay", "Paraguay", "Bolivia",
          "México", "Brasil"]


async def run():
    db = _get_sessionmaker()()

    try:
        permissions = (await db.scalars(select(Permission))).all()
        roles = (await db.scalars(select(Role))).all()
        role_map = {r.name: r for r in roles}
        perm_map = {p.code: p for p in permissions}

        print(f"Permisos: {len(permissions)} | Roles: {len(roles)}")
        print(f"Roles disponibles: {list(role_map.keys())}")

        # ──────────────────────────────────────────────────
        # 200 PRODUCTOS (44 templates repetidos con variaciones)
        # ──────────────────────────────────────────────────
        print("\nCreando 200 productos...")
        baraja = []
        for i in range(200):
            t = PRODUCTOS[i % len(PRODUCTOS)]
            variacion = random.choice(["", " Serie Pro", f" Gen{i//44+1}", "", " Plus"])
            nombre = t["name"] + variacion if random.random() > 0.3 else t["name"]
            precio = t["price"] + random.randint(-5000, 15000)
            stock = random.randint(0, 80)
            barcode = f"ELEC{str(i+1).zfill(6)}" if random.random() > 0.15 else None
            baraja.append(Product(
                name=nombre,
                description=f"Electrodoméstico {t['name'].split()[0]}",
                price=max(1, precio),
                stock=stock,
                state=ProductState.ACTIVE if stock > 0 else ProductState.NO_STOCK,
                barcode=barcode,
                weight_kg=t["weight_kg"] + random.uniform(-0.5, 0.5),
                width_cm=t["width_cm"] + random.randint(-2, 2),
                height_cm=t["height_cm"] + random.randint(-2, 2),
                depth_cm=t["depth_cm"] + random.randint(-2, 2),
            ))

        random.shuffle(baraja)
        db.add_all(baraja)
        await db.flush()
        print(f"  ✓ {len(baraja)} productos creados")

        # ──────────────────────────────────────────────────
        # 200 ESTANTERÍAS (warehouse shelving)
        # ──────────────────────────────────────────────────
        print("Creando 200 estanterías...")
        aisles = [chr(65 + i) for i in range(10)]  # A-J
        sizes = [
            {"type": "Grande", "w": 200, "h": 250, "d": 80, "kg": 1000},
            {"type": "Mediana", "w": 150, "h": 200, "d": 60, "kg": 600},
            {"type": "Pequeña", "w": 100, "h": 150, "d": 50, "kg": 300},
            {"type": "Palet", "w": 120, "h": 200, "d": 120, "kg": 800},
            {"type": "Vertical", "w": 60, "h": 220, "d": 60, "kg": 400},
        ]
        shelves_created = []
        used_codes = set()
        for i in range(200):
            aisle = random.choice(aisles)
            row = random.randint(1, 30)
            level = random.randint(1, 6)
            s = random.choice(sizes)
            
            # generar code único
            code = f"{aisle}-{str(row).zfill(2)}-{str(level).zfill(2)}"
            suffix = 0
            while code in used_codes:
                suffix += 1
                code = f"{aisle}-{str(row).zfill(2)}-{str(level).zfill(2)}-{suffix}"
            used_codes.add(code)
            shelves_created.append(Shelf(
                name=f"Estante {s['type']} {code}",
                code=code,
                aisle=aisle,
                row=row,
                level=level,
                max_weight_kg=s["kg"] + random.randint(-50, 100),
                width_cm=s["w"] + random.randint(-10, 10),
                height_cm=s["h"] + random.randint(-10, 10),
                depth_cm=s["d"] + random.randint(-5, 5),
            ))

        db.add_all(shelves_created)
        await db.flush()
        shelf_ids = [s.id for s in shelves_created]
        print(f"  ✓ {len(shelves_created)} estanterías creadas")

        # ──────────────────────────────────────────────────
        # 200 USUARIOS con roles variados
        # ──────────────────────────────────────────────────
        print("Creando 200 usuarios...")
        roles_dist = ["Operator"] * 120 + ["Viewer"] * 60 + ["Admin"] * 10 + ["Operator"] * 10
        random.shuffle(roles_dist)

        users_created = []
        user_roles_created = []
        for i in range(200):
            nombre = random.choice(NOMBRES)
            apellido = random.choice(APELLIDOS)
            users_created.append(User(
                email=f"{nombre.lower()}.{apellido.lower()}{i+1}@bodega.com",
                hashed_password=hash_password("pass1234"),
                first_name=nombre,
                last_name=apellido,
                phone=f"+56{random.randint(9,9)}{str(random.randint(10000000,99999999))}",
                city=random.choice(CIUDADES),
                country=random.choice(PAISES),
                is_active=random.random() > 0.05,
                is_super_admin=(roles_dist[i] == "Admin" and i < 5),
            ))

        db.add_all(users_created)
        await db.flush()

        for i, user in enumerate(users_created):
            role_name = roles_dist[i]
            user_roles_created.append(UserRole(user_id=user.id, role_id=role_map[role_name].id))

        db.add_all(user_roles_created)
        await db.flush()

        # conteo por rol
        conteo = {}
        for rn in roles_dist:
            conteo[rn] = conteo.get(rn, 0) + 1
        print(f"  ✓ {len(users_created)} usuarios creados: {conteo}")

        # ──────────────────────────────────────────────────
        # Asignar ~100 productos a estanterías aleatorias
        # ──────────────────────────────────────────────────
        print("\nAsignando productos a estanterías...")
        items_ok = 0
        for _ in range(150):
            product = random.choice(baraja)
            shelf = random.choice(shelves_created)

            # validación rápida: dimensiones individuales
            if (shelf.width_cm > 0 and product.width_cm > shelf.width_cm) or \
               (shelf.height_cm > 0 and product.height_cm > shelf.height_cm) or \
               (shelf.depth_cm > 0 and product.depth_cm > shelf.depth_cm):
                continue

            qty = random.randint(1, 10)
            if shelf.max_weight_kg > 0 and (product.weight_kg * qty) > shelf.max_weight_kg:
                qty = max(1, int(shelf.max_weight_kg / product.weight_kg))

            db.add(ShelfItem(shelf_id=shelf.id, product_id=product.id, quantity=qty))
            items_ok += 1

        await db.flush()
        print(f"  ✓ {items_ok} asignaciones creadas")

        await db.commit()
        print(f"\n✅ Seed completado. Resumen:")
        print(f"   {len(baraja)} productos")
        print(f"   {len(shelves_created)} estanterías")
        print(f"   {len(users_created)} usuarios")
        print(f"   {items_ok} asignaciones producto-estantería")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(run())

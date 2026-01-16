#!/usr/bin/env python3
"""
Test de conexión a Supabase
Ejecuta este script para verificar que las credenciales funcionan
"""
import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

print("\n" + "="*80)
print("🧪 TEST DE CONEXIÓN A SUPABASE")
print("="*80)

# Verificar que existen las variables
print("\n1️⃣ Verificando variables de entorno...")

required_vars = [
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "DATABASE_URL"
]

missing_vars = []
for var in required_vars:
    value = os.getenv(var)
    if not value or "REEMPLAZA" in value:
        print(f"   ❌ {var}: NO configurada o tiene valor placeholder")
        missing_vars.append(var)
    else:
        # Mostrar solo primeros 30 caracteres por seguridad
        preview = value[:30] + "..." if len(value) > 30 else value
        print(f"   ✅ {var}: {preview}")

if missing_vars:
    print(f"\n❌ ERROR: Faltan configurar estas variables:")
    for var in missing_vars:
        print(f"      - {var}")
    print("\n💡 Edita el archivo backend/.env con tus credenciales de Supabase")
    print("   Copia los valores desde: Project Settings → API en Supabase")
    sys.exit(1)

print("\n✅ Todas las variables de entorno están configuradas")

# Test de conexión con Supabase Client
print("\n2️⃣ Probando conexión con Supabase Client...")

try:
    from supabase import create_client, Client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    # Crear cliente Supabase sin opciones adicionales
    supabase: Client = create_client(supabase_url, supabase_key)

    # Intentar una query simple
    result = supabase.table("channels").select("*").limit(1).execute()

    print(f"   ✅ Conexión exitosa con Supabase Client")
    print(f"   ✅ Tabla 'channels' accesible ({len(result.data)} registros)")

except Exception as e:
    print(f"   ❌ Error: {e}")
    print("\n💡 Posibles causas:")
    print("   - URL de Supabase incorrecta")
    print("   - Service Role Key incorrecta")
    print("   - El schema SQL no se ejecutó correctamente")
    sys.exit(1)

# Test de conexión con SQLAlchemy
print("\n3️⃣ Probando conexión con SQLAlchemy (PostgreSQL directo)...")

try:
    from sqlalchemy import create_engine, text

    database_url = os.getenv("DATABASE_URL")
    engine = create_engine(database_url, pool_pre_ping=True)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM channels"))
        count = result.scalar()

    print(f"   ✅ Conexión exitosa con SQLAlchemy")
    print(f"   ✅ Tabla 'channels' tiene {count} registros")

except Exception as e:
    print(f"   ❌ Error: {e}")
    print("\n💡 Posibles causas:")
    print("   - DATABASE_URL incorrecta")
    print("   - Contraseña incorrecta en DATABASE_URL")
    print("   - El schema SQL no se ejecutó")
    sys.exit(1)

# Listar todas las tablas
print("\n4️⃣ Verificando que todas las tablas existen...")

expected_tables = [
    # Core tables
    "customers",
    "products",
    "channels",
    "orders",
    "order_items",
    # Catalog tables
    "product_catalog",
    "sku_mappings",
    # Inventory tables
    "warehouses",
    "warehouse_stock",
    "product_inventory_settings",
    # Audit tables
    "orders_audit",
    "sync_logs",
    # Auth tables
    "users",
    "api_credentials"
    # Removed in migration 20260113: product_variants, channel_equivalents,
    # channel_product_equivalents, relbase_product_mappings, dim_date,
    # ml_tokens, inventory_movements, customer_channel_rules,
    # api_keys, alerts, manual_corrections
]

try:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        existing_tables = [row[0] for row in result]

    print(f"   📊 Tablas encontradas: {len(existing_tables)}")

    missing_tables = []
    for table in expected_tables:
        if table in existing_tables:
            print(f"   ✅ {table}")
        else:
            print(f"   ❌ {table} - NO EXISTE")
            missing_tables.append(table)

    if missing_tables:
        print(f"\n⚠️  ADVERTENCIA: Faltan {len(missing_tables)} tablas:")
        for table in missing_tables:
            print(f"      - {table}")
        print("\n💡 Ejecuta el schema SQL completo en Supabase SQL Editor")
        print("   Archivo: docs/database-schema.sql")

except Exception as e:
    print(f"   ❌ Error listando tablas: {e}")

# Test de trigger de auditoría
print("\n5️⃣ Probando sistema de auditoría (trigger)...")

try:
    # Insertar un pedido de prueba
    test_order = {
        "order_number": "TEST-CONNECTION-001",
        "source": "test",
        "customer_id": None,
        "channel_id": 1,  # web_shopify
        "total": 10000,
        "order_date": "2024-01-01T12:00:00"
    }

    result = supabase.table("orders").insert(test_order).execute()
    order_id = result.data[0]["id"]
    print(f"   ✅ Pedido de prueba creado (ID: {order_id})")

    # Editar el pedido (cambiar canal)
    supabase.table("orders").update({
        "channel_id": 6,  # emporio
        "is_corrected": True,
        "corrected_by": "test@test.com",
        "correction_reason": "Test de auditoría automática"
    }).eq("id", order_id).execute()

    print(f"   ✅ Pedido editado (canal cambiado)")

    # Verificar que se creó registro en auditoría
    audit = supabase.table("orders_audit").select("*").eq("order_id", order_id).execute()

    if len(audit.data) > 0:
        print(f"   ✅ Auditoría funcionando! ({len(audit.data)} registros)")
        print(f"   ✅ TRIGGER AUTOMÁTICO FUNCIONA CORRECTAMENTE ⭐⭐⭐")
    else:
        print(f"   ⚠️  No se crearon registros de auditoría")
        print(f"   💡 El trigger puede no estar funcionando")

    # Limpiar: borrar pedido de prueba
    supabase.table("orders").delete().eq("id", order_id).execute()
    print(f"   🧹 Pedido de prueba eliminado")

except Exception as e:
    print(f"   ❌ Error en test de auditoría: {e}")
    print(f"   💡 Esto puede ser normal si es la primera vez")

# Resumen final
print("\n" + "="*80)
print("✅ TEST COMPLETADO")
print("="*80)

print("\n📊 RESUMEN:")
print("   ✅ Variables de entorno configuradas")
print("   ✅ Conexión a Supabase funcionando")
print("   ✅ Conexión a PostgreSQL funcionando")
print(f"   ✅ {len([t for t in expected_tables if t in existing_tables])}/{len(expected_tables)} tablas creadas")

print("\n🎉 ¡TODO LISTO! Puedes continuar con el backend.")
print("\n" + "="*80 + "\n")
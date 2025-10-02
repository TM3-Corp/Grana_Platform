-- ============================================================================
-- GRANA DATABASE SCHEMA - PostgreSQL (Supabase)
-- Single Source of Truth con Auditoría Completa
-- ============================================================================

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- TABLA: customers (Clientes consolidados)
-- ============================================================================
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(255),              -- ID del sistema origen
    source VARCHAR(50),                    -- 'shopify', 'relbase', 'walmart', etc.
    rut VARCHAR(20) UNIQUE,                -- RUT chileno
    name VARCHAR(255) NOT NULL,            -- Razón social
    name_fantasy VARCHAR(255),             -- Nombre de fantasía
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    city VARCHAR(100),
    commune VARCHAR(100),
    type_customer VARCHAR(50),             -- 'company', 'person'
    is_active BOOLEAN DEFAULT true,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Índices
    CONSTRAINT customers_external_source_unique UNIQUE (external_id, source)
);

CREATE INDEX idx_customers_rut ON customers(rut);
CREATE INDEX idx_customers_source ON customers(source);
CREATE INDEX idx_customers_name ON customers(name);

-- ============================================================================
-- TABLA: products (Catálogo unificado de productos)
-- ============================================================================
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    external_id VARCHAR(255),              -- ID del sistema origen
    source VARCHAR(50),                    -- 'shopify', 'relbase', etc.
    sku VARCHAR(100) UNIQUE NOT NULL,      -- SKU único interno
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    brand VARCHAR(100),

    -- Unidades y conversión
    unit VARCHAR(50),                      -- 'unidad', 'caja', 'kg'
    units_per_box INTEGER,                 -- Para conversión B2B

    -- Precios
    cost_price DECIMAL(12,2),              -- Costo
    sale_price DECIMAL(12,2),              -- Precio venta

    -- Stock
    current_stock INTEGER DEFAULT 0,
    min_stock INTEGER DEFAULT 10,          -- Para alertas

    -- Metadata
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_products_source ON products(source);
CREATE INDEX idx_products_category ON products(category);

-- ============================================================================
-- TABLA: channels (Canales de venta - EDITABLES)
-- ============================================================================
CREATE TABLE channels (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,      -- 'web', 'retail_walmart', 'emporio'
    name VARCHAR(100) NOT NULL,            -- Nombre display
    description TEXT,
    type VARCHAR(50),                      -- 'ecommerce', 'retail', 'direct'
    is_active BOOLEAN DEFAULT true,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Datos iniciales de canales
INSERT INTO channels (code, name, type) VALUES
    ('web_shopify', 'Tienda Web Shopify', 'ecommerce'),
    ('marketplace_ml', 'MercadoLibre', 'marketplace'),
    ('retail_walmart', 'Walmart Chile B2B', 'retail'),
    ('retail_cencosud', 'Cencosud/Jumbo B2B', 'retail'),
    ('retail_smu', 'SMU (Unimarc, Alvi) B2B', 'retail'),
    ('emporio', 'Emporio/Tiendas Locales', 'direct'),
    ('direct', 'Venta Directa', 'direct'),
    ('otro', 'Otro Canal', 'other');

-- ============================================================================
-- TABLA: orders (Pedidos - SINGLE SOURCE OF TRUTH) ⭐
-- ============================================================================
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,

    -- Identificación
    external_id VARCHAR(255),              -- ID del sistema origen
    order_number VARCHAR(100) NOT NULL,    -- Número de pedido interno
    source VARCHAR(50) NOT NULL,           -- 'shopify', 'walmart', 'mercadolibre'

    -- Relaciones
    customer_id INTEGER REFERENCES customers(id),
    channel_id INTEGER REFERENCES channels(id), -- ⭐ EDITABLE

    -- Montos
    subtotal DECIMAL(12,2),
    tax_amount DECIMAL(12,2),              -- IVA 19%
    shipping_cost DECIMAL(12,2),
    discount_amount DECIMAL(12,2),
    total DECIMAL(12,2) NOT NULL,          -- ⭐ EDITABLE

    -- Estados
    status VARCHAR(50) DEFAULT 'pending',  -- 'pending', 'processing', 'completed', 'cancelled'
    payment_status VARCHAR(50),            -- 'pending', 'paid', 'failed'
    fulfillment_status VARCHAR(50),        -- 'pending', 'shipped', 'delivered'

    -- Fechas
    order_date TIMESTAMP NOT NULL,
    payment_date TIMESTAMP,
    shipped_date TIMESTAMP,
    delivered_date TIMESTAMP,

    -- Facturación SII (Relbase)
    invoice_number VARCHAR(100),           -- Número de factura/boleta
    invoice_type VARCHAR(50),              -- 'factura', 'boleta'
    invoice_date TIMESTAMP,
    invoice_status VARCHAR(50),            -- 'pending', 'emitted', 'accepted', 'rejected'

    -- Correcciones manuales ⭐⭐⭐
    is_corrected BOOLEAN DEFAULT FALSE,    -- Si fue editado manualmente
    correction_reason TEXT,                -- Por qué se corrigió
    corrected_by VARCHAR(100),             -- Email de quien corrigió
    corrected_at TIMESTAMP,

    -- Notas
    customer_notes TEXT,
    internal_notes TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Constraints
    CONSTRAINT orders_external_source_unique UNIQUE (external_id, source)
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_channel ON orders(channel_id);
CREATE INDEX idx_orders_source ON orders(source);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_orders_is_corrected ON orders(is_corrected);
CREATE INDEX idx_orders_order_number ON orders(order_number);

-- ============================================================================
-- TABLA: order_items (Items de cada pedido)
-- ============================================================================
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER REFERENCES products(id),

    -- Datos del producto al momento de la venta
    product_sku VARCHAR(100),
    product_name VARCHAR(255),

    -- Cantidades
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(12,2) NOT NULL,
    subtotal DECIMAL(12,2) NOT NULL,
    tax_amount DECIMAL(12,2),
    total DECIMAL(12,2) NOT NULL,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);

-- ============================================================================
-- TABLA: orders_audit (Auditoría completa) ⭐⭐⭐
-- Esta es LA MÁS IMPORTANTE para Macarena
-- ============================================================================
CREATE TABLE orders_audit (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,

    -- Qué cambió
    field_changed VARCHAR(100) NOT NULL,   -- 'channel_id', 'total', 'customer_id'
    old_value TEXT,                        -- Valor anterior
    new_value TEXT,                        -- Valor nuevo

    -- Quién y cuándo
    changed_by VARCHAR(100) NOT NULL,      -- Email de quien hizo el cambio
    changed_at TIMESTAMP DEFAULT NOW(),

    -- Por qué
    reason TEXT,                           -- Explicación del cambio

    -- Contexto
    change_type VARCHAR(50),               -- 'manual_correction', 'system_update', 'sync'
    ip_address VARCHAR(50),                -- IP desde donde se hizo el cambio
    user_agent TEXT                        -- Browser/cliente
);

CREATE INDEX idx_orders_audit_order ON orders_audit(order_id);
CREATE INDEX idx_orders_audit_changed_at ON orders_audit(changed_at);
CREATE INDEX idx_orders_audit_changed_by ON orders_audit(changed_by);

-- ============================================================================
-- TABLA: manual_corrections (Registro de correcciones manuales)
-- ============================================================================
CREATE TABLE manual_corrections (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),

    correction_type VARCHAR(50) NOT NULL,  -- 'channel', 'amount', 'customer', 'date'
    description TEXT NOT NULL,

    corrected_by VARCHAR(100) NOT NULL,
    corrected_at TIMESTAMP DEFAULT NOW(),

    -- Para referencia
    audit_entries INTEGER[]                -- IDs de orders_audit relacionados
);

CREATE INDEX idx_manual_corrections_order ON manual_corrections(order_id);
CREATE INDEX idx_manual_corrections_date ON manual_corrections(corrected_at);

-- ============================================================================
-- TABLA: inventory_movements (Movimientos de inventario)
-- ============================================================================
CREATE TABLE inventory_movements (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    order_id INTEGER REFERENCES orders(id),  -- NULL si no es por venta

    movement_type VARCHAR(50) NOT NULL,    -- 'sale', 'purchase', 'adjustment', 'return'
    quantity INTEGER NOT NULL,             -- Positivo=entrada, Negativo=salida

    stock_before INTEGER,
    stock_after INTEGER,

    reason TEXT,

    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_inventory_movements_product ON inventory_movements(product_id);
CREATE INDEX idx_inventory_movements_type ON inventory_movements(movement_type);

-- ============================================================================
-- TABLA: sync_logs (Logs de sincronización con APIs)
-- ============================================================================
CREATE TABLE sync_logs (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,           -- 'shopify', 'walmart', 'cencosud'
    sync_type VARCHAR(50) NOT NULL,        -- 'orders', 'products', 'customers'

    status VARCHAR(50) NOT NULL,           -- 'success', 'failed', 'partial'
    records_processed INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,

    error_message TEXT,
    details JSONB,                         -- Información adicional

    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds INTEGER
);

CREATE INDEX idx_sync_logs_source ON sync_logs(source);
CREATE INDEX idx_sync_logs_started_at ON sync_logs(started_at);

-- ============================================================================
-- TABLA: alerts (Alertas de inventario y ventas)
-- ============================================================================
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    alert_type VARCHAR(50) NOT NULL,       -- 'low_stock', 'out_of_stock', 'sales_drop'
    severity VARCHAR(20) NOT NULL,         -- 'info', 'warning', 'critical'

    related_entity_type VARCHAR(50),       -- 'product', 'order', 'customer'
    related_entity_id INTEGER,

    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,

    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    resolved_by VARCHAR(100),

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_alerts_type ON alerts(alert_type);
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_is_resolved ON alerts(is_resolved);

-- ============================================================================
-- TRIGGER: Auto-update updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- TRIGGER: Auto-audit de cambios en orders ⭐⭐⭐
-- ============================================================================
CREATE OR REPLACE FUNCTION audit_order_changes()
RETURNS TRIGGER AS $$
BEGIN
    -- Solo auditar si hay cambios reales
    IF (OLD.channel_id IS DISTINCT FROM NEW.channel_id) THEN
        INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, changed_by, change_type)
        VALUES (NEW.id, 'channel_id', OLD.channel_id::text, NEW.channel_id::text,
                COALESCE(NEW.corrected_by, 'system'),
                CASE WHEN NEW.is_corrected THEN 'manual_correction' ELSE 'system_update' END);
    END IF;

    IF (OLD.total IS DISTINCT FROM NEW.total) THEN
        INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, changed_by, change_type)
        VALUES (NEW.id, 'total', OLD.total::text, NEW.total::text,
                COALESCE(NEW.corrected_by, 'system'),
                CASE WHEN NEW.is_corrected THEN 'manual_correction' ELSE 'system_update' END);
    END IF;

    IF (OLD.customer_id IS DISTINCT FROM NEW.customer_id) THEN
        INSERT INTO orders_audit (order_id, field_changed, old_value, new_value, changed_by, change_type)
        VALUES (NEW.id, 'customer_id', OLD.customer_id::text, NEW.customer_id::text,
                COALESCE(NEW.corrected_by, 'system'),
                CASE WHEN NEW.is_corrected THEN 'manual_correction' ELSE 'system_update' END);
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_order_changes_trigger AFTER UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION audit_order_changes();

-- ============================================================================
-- TRIGGER: Actualizar stock automáticamente
-- ============================================================================
CREATE OR REPLACE FUNCTION update_product_stock()
RETURNS TRIGGER AS $$
BEGIN
    -- Al crear un order_item, reducir stock
    IF (TG_OP = 'INSERT') THEN
        UPDATE products
        SET current_stock = current_stock - NEW.quantity
        WHERE id = NEW.product_id;

        -- Registrar movimiento de inventario
        INSERT INTO inventory_movements (product_id, order_id, movement_type, quantity, stock_after)
        VALUES (NEW.product_id, NEW.order_id, 'sale', -NEW.quantity,
                (SELECT current_stock FROM products WHERE id = NEW.product_id));

        -- Crear alerta si stock bajo
        INSERT INTO alerts (alert_type, severity, related_entity_type, related_entity_id, title, message)
        SELECT 'low_stock', 'warning', 'product', p.id,
               'Stock bajo: ' || p.name,
               'El producto ' || p.name || ' tiene solo ' || p.current_stock || ' unidades'
        FROM products p
        WHERE p.id = NEW.product_id AND p.current_stock < p.min_stock;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_product_stock_trigger AFTER INSERT ON order_items
    FOR EACH ROW EXECUTE FUNCTION update_product_stock();

-- ============================================================================
-- VISTAS ÚTILES
-- ============================================================================

-- Vista: Pedidos con toda la info consolidada
CREATE VIEW v_orders_full AS
SELECT
    o.id,
    o.order_number,
    o.source,
    o.order_date,
    o.total,
    o.status,
    o.is_corrected,

    c.name AS customer_name,
    c.rut AS customer_rut,

    ch.name AS channel_name,
    ch.type AS channel_type,

    o.invoice_number,
    o.invoice_status,

    o.created_at,
    o.updated_at
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id
LEFT JOIN channels ch ON o.channel_id = ch.id;

-- Vista: Ventas por canal
CREATE VIEW v_sales_by_channel AS
SELECT
    ch.code AS channel_code,
    ch.name AS channel_name,
    ch.type AS channel_type,
    COUNT(o.id) AS total_orders,
    SUM(o.total) AS total_sales,
    AVG(o.total) AS avg_order_value,
    MIN(o.order_date) AS first_order,
    MAX(o.order_date) AS last_order
FROM orders o
JOIN channels ch ON o.channel_id = ch.id
WHERE o.status != 'cancelled'
GROUP BY ch.code, ch.name, ch.type;

-- Vista: Productos con bajo stock
CREATE VIEW v_low_stock_products AS
SELECT
    p.id,
    p.sku,
    p.name,
    p.current_stock,
    p.min_stock,
    p.category,
    (p.min_stock - p.current_stock) AS units_needed
FROM products p
WHERE p.current_stock < p.min_stock
    AND p.is_active = true
ORDER BY (p.min_stock - p.current_stock) DESC;

-- ============================================================================
-- COMENTARIOS EN TABLAS (para documentación)
-- ============================================================================
COMMENT ON TABLE orders IS 'Tabla principal de pedidos - Single Source of Truth editable y auditable';
COMMENT ON TABLE orders_audit IS 'Auditoría completa de todos los cambios en pedidos - CRÍTICO para Macarena';
COMMENT ON TABLE manual_corrections IS 'Registro de correcciones manuales realizadas por usuarios';
COMMENT ON COLUMN orders.is_corrected IS 'Indica si el pedido fue editado manualmente por Macarena o equipo';
COMMENT ON COLUMN orders.correction_reason IS 'Razón por la cual se corrigió manualmente el pedido';

-- ============================================================================
-- FIN DEL SCHEMA
-- ============================================================================
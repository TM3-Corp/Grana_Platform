-- Migration 011: Create customer_channel_rules table
-- Business Intelligence Layer: Maps customers to correct channels when RelBase has errors
-- This allows the platform to display corrected channel assignments without modifying RelBase

CREATE TABLE IF NOT EXISTS customer_channel_rules (
    id SERIAL PRIMARY KEY,
    customer_external_id VARCHAR(50) NOT NULL,  -- RelBase customer_id (e.g., '1997707')
    channel_external_id INTEGER NOT NULL,       -- RelBase channel_id (e.g., 3768)
    channel_name VARCHAR(100) NOT NULL,          -- Human-readable name (e.g., 'CORPORATIVO')
    rule_reason TEXT NOT NULL,                   -- Why this rule exists (business context)
    priority INTEGER DEFAULT 1,                  -- Higher priority rules override lower ones
    is_active BOOLEAN DEFAULT TRUE,              -- Can temporarily disable rules
    created_by VARCHAR(100),                     -- Who created this rule
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for fast lookups
CREATE INDEX idx_customer_external_id ON customer_channel_rules(customer_external_id);
CREATE INDEX idx_channel_external_id ON customer_channel_rules(channel_external_id);
CREATE INDEX idx_is_active ON customer_channel_rules(is_active);

-- Create composite index for common query pattern (lookup by customer + active status)
CREATE INDEX idx_customer_active_lookup ON customer_channel_rules(customer_external_id, is_active);

-- Create partial unique index: one customer can only have one active rule per priority level
CREATE UNIQUE INDEX unique_active_customer_rule ON customer_channel_rules(customer_external_id, priority)
    WHERE is_active = TRUE;

-- Comments for documentation
COMMENT ON TABLE customer_channel_rules IS 'Business rules to correct customer channel assignments when RelBase data has errors or omissions';
COMMENT ON COLUMN customer_channel_rules.customer_external_id IS 'RelBase customer_id (external ID from API)';
COMMENT ON COLUMN customer_channel_rules.channel_external_id IS 'RelBase channel_id that should be used for this customer';
COMMENT ON COLUMN customer_channel_rules.rule_reason IS 'Business justification for why this customer belongs to this channel';
COMMENT ON COLUMN customer_channel_rules.priority IS 'Priority level for rule application (higher number = higher priority)';
COMMENT ON COLUMN customer_channel_rules.is_active IS 'Whether this rule is currently being applied';

-- Insert initial rules based on analysis of $408.8M in uncategorized orders
-- These 3 customers account for 96% of orders without channel_id

-- Rule 1: NEWREST INFLIGHT (customer_id 1997707) → CORPORATIVO (channel_id 3768)
-- $186M in sales, airline catering company = corporate channel
INSERT INTO customer_channel_rules
    (customer_external_id, channel_external_id, channel_name, rule_reason, priority, created_by)
VALUES
    ('1997707', 3768, 'CORPORATIVO',
     'Newrest Inflight es una empresa de catering aeronáutico. Sus ventas corresponden al canal CORPORATIVO (servicios de alimentación a aerolíneas). Representa $186M (45%) de órdenes sin canal asignado en RelBase.',
     1, 'migration_011');

-- Rule 2: CENCOSUD RETAIL (customer_id 596810) → RETAIL (channel_id 1459)
-- $160M in sales, supermarket chain = retail channel
INSERT INTO customer_channel_rules
    (customer_external_id, channel_external_id, channel_name, rule_reason, priority, created_by)
VALUES
    ('596810', 1459, 'RETAIL',
     'Cencosud Retail S.A. es una cadena de supermercados. Sus ventas corresponden al canal RETAIL (puntos de venta al consumidor final). Representa $160M (39%) de órdenes sin canal asignado en RelBase.',
     1, 'migration_011');

-- Rule 3: Walmart Chile (customer_id 2358971) → RETAIL (channel_id 1459)
-- $45.9M in sales, supermarket chain = retail channel
INSERT INTO customer_channel_rules
    (customer_external_id, channel_external_id, channel_name, rule_reason, priority, created_by)
VALUES
    ('2358971', 1459, 'RETAIL',
     'Walmart Chile S.A. es una cadena de supermercados. Sus ventas corresponden al canal RETAIL (puntos de venta al consumidor final). Representa $45.9M (11%) de órdenes sin canal asignado en RelBase.',
     1, 'migration_011');

-- Verification query (not executed in migration, but useful for testing)
-- SELECT
--     ccr.customer_external_id,
--     c.name as customer_name,
--     ccr.channel_external_id,
--     ccr.channel_name,
--     ccr.rule_reason,
--     COUNT(o.id) as affected_orders,
--     SUM(o.total_amount) as total_amount
-- FROM customer_channel_rules ccr
-- LEFT JOIN customers c ON c.external_id = ccr.customer_external_id AND c.source = 'relbase'
-- LEFT JOIN orders o ON o.customer_id = c.id AND o.channel_id IS NULL
-- WHERE ccr.is_active = TRUE
-- GROUP BY ccr.customer_external_id, c.name, ccr.channel_external_id, ccr.channel_name, ccr.rule_reason;

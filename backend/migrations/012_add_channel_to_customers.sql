-- Migration 012: Add channel assignment to customers table
-- This allows admin to override RelBase channel assignments
-- Priority: Customer assigned channel > RelBase channel > NULL

-- Add channel fields to customers table
ALTER TABLE customers
ADD COLUMN assigned_channel_id INTEGER,            -- RelBase channel_id (e.g., 1459, 3768)
ADD COLUMN assigned_channel_name VARCHAR(100),     -- Human-readable name (e.g., 'RETAIL')
ADD COLUMN channel_assigned_by VARCHAR(100),       -- Who assigned this (admin email, 'migration', etc.)
ADD COLUMN channel_assigned_at TIMESTAMP;          -- When was it assigned

-- Add comment for documentation
COMMENT ON COLUMN customers.assigned_channel_id IS 'Admin-assigned channel ID. Takes priority over RelBase channel_id when displaying data.';
COMMENT ON COLUMN customers.assigned_channel_name IS 'Human-readable channel name for the assigned channel.';
COMMENT ON COLUMN customers.channel_assigned_by IS 'Who assigned this channel (admin email, migration script, etc.)';
COMMENT ON COLUMN customers.channel_assigned_at IS 'When the channel was assigned to this customer.';

-- Create index for fast lookups by channel
CREATE INDEX idx_customers_assigned_channel ON customers(assigned_channel_id) WHERE assigned_channel_id IS NOT NULL;

-- Pre-populate the 3 main customers that were causing $391.9M to be uncategorized

-- Customer 1: NEWREST INFLIGHT → CORPORATIVO
-- Airline catering company, $186M in sales
UPDATE customers
SET assigned_channel_id = 3768,
    assigned_channel_name = 'CORPORATIVO',
    channel_assigned_by = 'migration_012',
    channel_assigned_at = NOW()
WHERE external_id = '1997707'
  AND source = 'relbase'
  AND assigned_channel_id IS NULL;  -- Only if not already assigned

-- Customer 2: CENCOSUD RETAIL → RETAIL
-- Supermarket chain, $160M in sales
UPDATE customers
SET assigned_channel_id = 1459,
    assigned_channel_name = 'RETAIL',
    channel_assigned_by = 'migration_012',
    channel_assigned_at = NOW()
WHERE external_id = '596810'
  AND source = 'relbase'
  AND assigned_channel_id IS NULL;

-- Customer 3: WALMART CHILE → RETAIL
-- Supermarket chain, $45.9M in sales
UPDATE customers
SET assigned_channel_id = 1459,
    assigned_channel_name = 'RETAIL',
    channel_assigned_by = 'migration_012',
    channel_assigned_at = NOW()
WHERE external_id = '2358971'
  AND source = 'relbase'
  AND assigned_channel_id IS NULL;

-- Verification query (not executed, but useful for testing)
-- Shows customers with assigned channels and how many orders would be affected
/*
SELECT
    c.id,
    c.external_id,
    c.name,
    c.assigned_channel_name,
    c.channel_assigned_at,
    COUNT(o.id) as affected_orders,
    SUM(o.total_amount) as total_affected_amount
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
WHERE c.assigned_channel_id IS NOT NULL
  AND c.source = 'relbase'
GROUP BY c.id, c.external_id, c.name, c.assigned_channel_name, c.channel_assigned_at
ORDER BY total_affected_amount DESC;
*/

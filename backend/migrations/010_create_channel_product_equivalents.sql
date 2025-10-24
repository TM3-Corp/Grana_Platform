-- Migration 010: Create channel_product_equivalents table
-- This table maps channel-specific SKUs to official catalog SKUs

CREATE TABLE IF NOT EXISTS channel_product_equivalents (
    id SERIAL PRIMARY KEY,
    channel_product_sku VARCHAR(100) NOT NULL,
    official_product_sku VARCHAR(100) NOT NULL,
    channel VARCHAR(50) NOT NULL,  -- 'shopify', 'mercadolibre', 'relbase'
    confidence_score DECIMAL(3,2) DEFAULT 1.0,  -- 0.0 to 1.0
    mapping_method VARCHAR(50),  -- 'manual', 'exact_match', 'fuzzy_match', 'description_parse'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint: one channel product can only map to one official SKU per channel
    CONSTRAINT unique_channel_product UNIQUE (channel_product_sku, channel),

    -- Foreign key to official products (optional, for referential integrity)
    CONSTRAINT fk_official_product FOREIGN KEY (official_product_sku)
        REFERENCES products(sku) ON DELETE CASCADE
);

-- Create indexes for fast lookups
CREATE INDEX idx_channel_product_sku ON channel_product_equivalents(channel_product_sku);
CREATE INDEX idx_official_product_sku ON channel_product_equivalents(official_product_sku);
CREATE INDEX idx_channel ON channel_product_equivalents(channel);

-- Create composite index for common query pattern
CREATE INDEX idx_channel_product_lookup ON channel_product_equivalents(channel, channel_product_sku);

COMMENT ON TABLE channel_product_equivalents IS 'Maps channel-specific product SKUs to official catalog SKUs';
COMMENT ON COLUMN channel_product_equivalents.confidence_score IS 'Confidence in the mapping (1.0 = exact match, < 1.0 = fuzzy/inferred)';
COMMENT ON COLUMN channel_product_equivalents.mapping_method IS 'How the mapping was created (manual, exact_match, fuzzy_match, etc.)';

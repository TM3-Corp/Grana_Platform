-- Migration: Create api_keys table for API key authentication
-- Date: 2024-12-17
-- Description: Adds API key management for external integrations

-- Create api_keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(255) NOT NULL,           -- SHA-256 hash of the API key
    name VARCHAR(255) NOT NULL,               -- Human-readable name (e.g., "Shopify Integration")
    user_id INTEGER REFERENCES users(id),     -- Owner of the API key
    permissions JSONB DEFAULT '[]'::jsonb,    -- Array of permissions (e.g., ["read:orders", "write:products"])
    rate_limit INTEGER DEFAULT 100,           -- Requests per minute
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),

    -- Ensure key_hash is unique
    CONSTRAINT api_keys_key_hash_unique UNIQUE (key_hash)
);

-- Create index for fast key lookups
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_is_active ON api_keys(is_active);

-- Add comments
COMMENT ON TABLE api_keys IS 'API keys for external integrations and programmatic access';
COMMENT ON COLUMN api_keys.key_hash IS 'SHA-256 hash of the API key (never store raw key)';
COMMENT ON COLUMN api_keys.permissions IS 'JSON array of permission strings like ["read:orders", "write:products"]';
COMMENT ON COLUMN api_keys.rate_limit IS 'Maximum requests per minute for this key';

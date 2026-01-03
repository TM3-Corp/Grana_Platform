-- Migration 028: Create API Credentials table for external service tokens
-- Purpose: Store OAuth tokens (like MercadoLibre) persistently so they survive container restarts
-- Author: Claude Code
-- Date: 2026-01-03

-- Create api_credentials table for storing external service tokens
CREATE TABLE IF NOT EXISTS api_credentials (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(50) NOT NULL UNIQUE,  -- 'mercadolibre', 'shopify', etc.
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,
    additional_data JSONB DEFAULT '{}',  -- For service-specific data (seller_id, app_id, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for quick lookups
CREATE INDEX IF NOT EXISTS idx_api_credentials_service ON api_credentials(service_name);

-- Insert initial MercadoLibre credentials (will be updated by the app on first token refresh)
-- Note: These are placeholder values - actual tokens will be populated from env vars on first run
INSERT INTO api_credentials (service_name, additional_data)
VALUES (
    'mercadolibre',
    '{"seller_id": "2506482242", "app_id": "7459152470029980"}'::jsonb
)
ON CONFLICT (service_name) DO NOTHING;

-- Add trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_api_credentials_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_api_credentials_updated_at ON api_credentials;
CREATE TRIGGER trigger_api_credentials_updated_at
    BEFORE UPDATE ON api_credentials
    FOR EACH ROW
    EXECUTE FUNCTION update_api_credentials_updated_at();

COMMENT ON TABLE api_credentials IS 'Stores OAuth tokens for external services (MercadoLibre, etc.) persistently';
COMMENT ON COLUMN api_credentials.service_name IS 'Unique identifier for the service (mercadolibre, shopify, etc.)';
COMMENT ON COLUMN api_credentials.access_token IS 'Current access token for API calls';
COMMENT ON COLUMN api_credentials.refresh_token IS 'Token used to get new access tokens';
COMMENT ON COLUMN api_credentials.token_expires_at IS 'When the current access token expires';
COMMENT ON COLUMN api_credentials.additional_data IS 'Service-specific data like seller_id, app_id, etc.';

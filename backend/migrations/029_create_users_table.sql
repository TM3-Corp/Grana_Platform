-- Migration 029: Create users table for authentication
-- Date: 2026-01-15
-- Purpose: Create the users table required for the auth system
-- Dependencies: None

-- ============================================================================
-- STEP 1: Create users table
-- ============================================================================

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

COMMENT ON TABLE users IS 'User accounts for platform authentication';
COMMENT ON COLUMN users.email IS 'Unique email address for login';
COMMENT ON COLUMN users.password_hash IS 'bcrypt hashed password';
COMMENT ON COLUMN users.role IS 'User role: admin, user, viewer';
COMMENT ON COLUMN users.is_active IS 'Whether the user account is active';

-- ============================================================================
-- STEP 2: Create trigger for updated_at
-- ============================================================================

CREATE OR REPLACE FUNCTION update_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_users_updated_at ON users;
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_users_updated_at();

-- ============================================================================
-- STEP 3: Seed initial admin users
-- Passwords are bcrypt hashed (cost factor 12)
-- paul@tm3.ai password: Grana2025!
-- macarena@grana.cl password: Grana2025!
-- ============================================================================

-- Note: These hashes are generated with bcrypt cost factor 12
-- In production, users should change their passwords immediately

INSERT INTO users (email, password_hash, name, role, is_active)
VALUES
    ('paul@tm3.ai', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4eVcvFMJqSqDxPiy', 'Paul', 'admin', true),
    ('macarena@grana.cl', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4eVcvFMJqSqDxPiy', 'Macarena Vicuna', 'admin', true)
ON CONFLICT (email) DO UPDATE SET
    name = EXCLUDED.name,
    role = EXCLUDED.role,
    is_active = EXCLUDED.is_active;

-- ============================================================================
-- Migration complete
-- ============================================================================

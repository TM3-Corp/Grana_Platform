-- Migration: Create dim_date dimension table for OLAP
-- Purpose: Date hierarchy for efficient time-based analytics
-- Author: Claude Code
-- Date: 2025-11-12

-- ============================================
-- 1. CREATE DIM_DATE TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS dim_date (
    date_id INTEGER PRIMARY KEY,        -- YYYYMMDD format (e.g., 20250315)
    date DATE NOT NULL UNIQUE,

    -- Hierarchies for drill-down
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,           -- 1-4
    month INTEGER NOT NULL,             -- 1-12
    week INTEGER NOT NULL,              -- 1-53 (ISO week)
    day_of_week INTEGER NOT NULL,      -- 1-7 (Monday=1)
    day_of_month INTEGER NOT NULL,     -- 1-31
    day_of_year INTEGER NOT NULL,      -- 1-366

    -- Human-readable labels
    month_name VARCHAR(20),             -- January, February, etc.
    quarter_name VARCHAR(10),           -- Q1 2025, Q2 2025, etc.
    year_month VARCHAR(7),              -- 2025-03
    year_quarter VARCHAR(7),            -- 2025-Q1
    week_year VARCHAR(8),               -- 2025-W12

    -- Business attributes
    is_weekend BOOLEAN,
    is_holiday BOOLEAN DEFAULT FALSE,
    fiscal_year INTEGER,
    fiscal_quarter INTEGER,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- 2. CREATE INDEXES
-- ============================================

-- Most common query patterns
CREATE INDEX IF NOT EXISTS idx_date_year_month ON dim_date(year, month);
CREATE INDEX IF NOT EXISTS idx_date_year_quarter ON dim_date(year, quarter);
CREATE INDEX IF NOT EXISTS idx_date_fiscal ON dim_date(fiscal_year, fiscal_quarter);
CREATE INDEX IF NOT EXISTS idx_date_week ON dim_date(year, week);
CREATE INDEX IF NOT EXISTS idx_date_dow ON dim_date(day_of_week);

-- For range queries
CREATE INDEX IF NOT EXISTS idx_date_date ON dim_date(date);

-- ============================================
-- 3. ADD COMMENT
-- ============================================

COMMENT ON TABLE dim_date IS 'Date dimension table for OLAP analytics. Provides date hierarchies for efficient time-based queries. Covers 2020-2030.';

COMMENT ON COLUMN dim_date.date_id IS 'Primary key in YYYYMMDD format (e.g., 20250315)';
COMMENT ON COLUMN dim_date.fiscal_year IS 'Fiscal year (same as calendar year for Grana)';
COMMENT ON COLUMN dim_date.fiscal_quarter IS 'Fiscal quarter (Q1=Jan-Mar, Q2=Apr-Jun, Q3=Jul-Sep, Q4=Oct-Dec)';
COMMENT ON COLUMN dim_date.is_holiday IS 'Chilean holidays (to be populated)';

-- ============================================
-- 4. GRANT PERMISSIONS
-- ============================================

-- Grant SELECT to application role (if exists)
-- GRANT SELECT ON dim_date TO application_role;

-- Note: Population script is separate (populate_dim_date.py)
-- Run: python3 backend/scripts/migrations/populate_dim_date.py

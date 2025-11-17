-- Migration 015: Add sku_primario column to order_items table
-- This allows OLAP queries to group by SKU Primario directly in SQL
-- instead of requiring post-query Python mapping

-- Add sku_primario column (nullable initially, we'll populate it next)
ALTER TABLE order_items
ADD COLUMN sku_primario VARCHAR(100);

-- Create index for fast grouping in OLAP queries
CREATE INDEX idx_order_items_sku_primario ON order_items(sku_primario);

-- Add comment explaining the column
COMMENT ON COLUMN order_items.sku_primario IS
'Mapped primary SKU code from CSV (Codigos_Grana_Ingles.csv).
Handles legacy codes like ANU-BAKC_U04010 → BAKC_U04010.
This field is populated by the audit.py mapping logic and enables
efficient OLAP grouping by SKU Primario.';

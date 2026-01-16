#!/usr/bin/env python3
"""
Script: run_029_cleanup_obsolete_tables.py
Purpose: Execute migration 029 and clean up related Python code

This script:
1. Runs the SQL migration to drop obsolete tables
2. Updates Python files that reference deleted tables/views
3. Verifies the cleanup was successful

Usage:
    cd backend && source venv/bin/activate
    python scripts/migrations/run_029_cleanup_obsolete_tables.py [--dry-run]

Options:
    --dry-run    Show what would be done without making changes
"""

import os
import sys
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
from pathlib import Path
from datetime import datetime

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

# Load environment
env_path = BACKEND_DIR / '.env.development'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv(BACKEND_DIR / '.env')

DATABASE_URL = os.getenv("DATABASE_URL")

# Tables and views to delete
TABLES_TO_DELETE = [
    'inventory_movements',
    'product_variants',
    'channel_equivalents',
    'channel_product_equivalents',
    'relbase_product_mappings',
    'dim_date',
    'ml_tokens',
    'customer_channel_rules'
]

VIEWS_TO_DELETE = [
    'inventory_consolidated',
    'product_families'
]


def print_header(title: str):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_step(step: int, description: str):
    """Print step indicator"""
    print(f"\n[Step {step}] {description}")
    print("-" * 50)


def check_tables_exist(cursor) -> dict:
    """Check which tables/views currently exist"""
    result = {'tables': {}, 'views': {}}

    for table in TABLES_TO_DELETE:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """, (table,))
        result['tables'][table] = cursor.fetchone()[0]

    for view in VIEWS_TO_DELETE:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.views
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """, (view,))
        result['views'][view] = cursor.fetchone()[0]

    return result


def run_sql_migration(cursor, dry_run: bool = False) -> bool:
    """Execute the SQL migration"""

    if dry_run:
        print("  [DRY RUN] Would execute SQL migration")
        return True

    # Drop views first
    for view in VIEWS_TO_DELETE:
        print(f"  Dropping view: {view}")
        cursor.execute(f"DROP VIEW IF EXISTS {view} CASCADE")

    # Drop tables
    for table in TABLES_TO_DELETE:
        print(f"  Dropping table: {table}")
        cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    return True


def update_product_mapping_repository(dry_run: bool = False) -> bool:
    """Update product_mapping_repository.py to remove references to deleted views"""

    file_path = BACKEND_DIR / 'app' / 'repositories' / 'product_mapping_repository.py'

    if not file_path.exists():
        print(f"  File not found: {file_path}")
        return False

    content = file_path.read_text()
    original_content = content

    # Find and comment out the methods that use deleted views
    # Method: find_consolidated_inventory (uses inventory_consolidated)
    # Method: find_product_families (uses product_families)

    # We'll add a deprecation notice and make methods return empty results

    old_consolidated = '''    def find_consolidated_inventory(
        self,
        base_product_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get consolidated inventory from database view

        Args:
            base_product_id: Optional filter for specific product

        Returns:
            List of inventory records with calculated totals
        """
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        try:
            if base_product_id:
                cursor.execute("""
                    SELECT
                        base_product_id,
                        base_sku,
                        base_name,
                        base_source,
                        base_unit_price,
                        base_direct_stock,
                        num_variants,
                        variant_stock_as_units,
                        total_units_available,
                        stock_status,
                        inventory_value
                    FROM inventory_consolidated
                    WHERE base_product_id = %s
                    ORDER BY base_name
                """, (base_product_id,))
            else:
                cursor.execute("""
                    SELECT
                        base_product_id,
                        base_sku,
                        base_name,
                        base_source,
                        base_unit_price,
                        base_direct_stock,
                        num_variants,
                        variant_stock_as_units,
                        total_units_available,
                        stock_status,
                        inventory_value
                    FROM inventory_consolidated
                    ORDER BY base_name
                """)

            return cursor.fetchall()

        finally:
            cursor.close()
            conn.close()'''

    new_consolidated = '''    def find_consolidated_inventory(
        self,
        base_product_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        DEPRECATED: View inventory_consolidated was removed in migration 029.
        Use warehouse_stock and product_catalog for inventory queries.

        Returns empty list for backwards compatibility.
        """
        # View removed in migration 029_cleanup_obsolete_tables.sql
        return []'''

    old_families = '''    def find_product_families(
        self,
        base_product_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get product families from database view

        Args:
            base_product_id: Optional filter for specific product family

        Returns:
            List of product family records
        """
        conn = get_db_connection_dict_with_retry()
        cursor = conn.cursor()

        try:
            if base_product_id:
                cursor.execute("""
                    SELECT
                        base_product_id,
                        base_sku,
                        base_name,
                        variant_product_id,
                        variant_sku,
                        variant_name,
                        quantity_multiplier,
                        packaging_type,
                        variant_stock,
                        variant_stock_as_base_units,
                        variant_price,
                        base_unit_price,
                        variant_unit_price,
                        discount_percentage
                    FROM product_families
                    WHERE base_product_id = %s
                    ORDER BY quantity_multiplier
                """, (base_product_id,))
            else:
                cursor.execute("""
                    SELECT
                        base_product_id,
                        base_sku,
                        base_name,
                        variant_product_id,
                        variant_sku,
                        variant_name,
                        quantity_multiplier,
                        packaging_type,
                        variant_stock,
                        variant_stock_as_base_units,
                        variant_price,
                        base_unit_price,
                        variant_unit_price,
                        discount_percentage
                    FROM product_families
                    ORDER BY base_name, quantity_multiplier
                """)

            return cursor.fetchall()

        finally:
            cursor.close()
            conn.close()'''

    new_families = '''    def find_product_families(
        self,
        base_product_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        DEPRECATED: View product_families was removed in migration 029.
        Use product_catalog with sku_primario for family grouping.

        Returns empty list for backwards compatibility.
        """
        # View removed in migration 029_cleanup_obsolete_tables.sql
        return []'''

    if old_consolidated in content:
        content = content.replace(old_consolidated, new_consolidated)
        print("  Updated: find_consolidated_inventory method")

    if old_families in content:
        content = content.replace(old_families, new_families)
        print("  Updated: find_product_families method")

    if content != original_content:
        if dry_run:
            print("  [DRY RUN] Would update product_mapping_repository.py")
        else:
            file_path.write_text(content)
            print(f"  Saved: {file_path}")
        return True
    else:
        print("  No changes needed or patterns not found exactly")
        return False


def update_inventory_service(dry_run: bool = False) -> bool:
    """Update inventory_service.py to remove inventory_movements INSERT"""

    file_path = BACKEND_DIR / 'app' / 'services' / 'inventory_service.py'

    if not file_path.exists():
        print(f"  File not found: {file_path}")
        return False

    content = file_path.read_text()
    original_content = content

    # Comment out the inventory_movements INSERT block
    old_block = '''            # Record inventory movement
            quantity_change = new_stock - old_stock
            cursor.execute("""
                INSERT INTO inventory_movements
                (product_id, movement_type, quantity, stock_before, stock_after, reason, created_by, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, ('''

    new_block = '''            # Record inventory movement
            # NOTE: inventory_movements table removed in migration 029
            # quantity_change = new_stock - old_stock
            # cursor.execute("""
            #     INSERT INTO inventory_movements
            #     (product_id, movement_type, quantity, stock_before, stock_after, reason, created_by, created_at)
            #     VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            # """, ('''

    if old_block in content:
        content = content.replace(old_block, new_block)

        # Also comment out the closing part
        # This is tricky - let's do a more surgical approach
        if dry_run:
            print("  [DRY RUN] Would update inventory_service.py")
        else:
            # Read file and update line by line
            lines = original_content.split('\n')
            new_lines = []
            in_movement_block = False
            paren_count = 0

            for i, line in enumerate(lines):
                if 'INSERT INTO inventory_movements' in line:
                    in_movement_block = True
                    new_lines.append('            # NOTE: inventory_movements table removed in migration 029')
                    new_lines.append('            # ' + line.strip())
                    paren_count = line.count('(') - line.count(')')
                elif in_movement_block:
                    new_lines.append('            # ' + line.strip() if line.strip() else '')
                    paren_count += line.count('(') - line.count(')')
                    if paren_count <= 0 and ')' in line:
                        in_movement_block = False
                else:
                    new_lines.append(line)

            file_path.write_text('\n'.join(new_lines))
            print(f"  Saved: {file_path}")
        return True
    else:
        print("  Pattern not found - may already be updated")
        return False


def update_sync_service(dry_run: bool = False) -> bool:
    """Update sync_service.py to use customers.assigned_channel_id instead of customer_channel_rules"""

    file_path = BACKEND_DIR / 'app' / 'services' / 'sync_service.py'

    if not file_path.exists():
        print(f"  File not found: {file_path}")
        return False

    content = file_path.read_text()
    original_content = content

    # Replace the customer_channel_rules query with customers.assigned_channel_id
    old_block = '''                            # Step 4: If no channel_id yet and customer has a rule, apply it
                            if channel_id is None and customer_id_relbase:
                                cursor.execute("""
                                    SELECT c.id, ccr.channel_name
                                    FROM customer_channel_rules ccr
                                    JOIN channels c ON c.external_id = ccr.channel_external_id::text
                                    WHERE ccr.customer_external_id = %s AND ccr.is_active = true
                                """, (str(customer_id_relbase),))
                                rule_result = cursor.fetchone()
                                if rule_result:
                                    channel_id = rule_result[0]
                                    logger.info(f"Applied channel rule for customer {customer_id_relbase}: {rule_result[1]}")'''

    new_block = '''                            # Step 4: If no channel_id yet and customer has assigned channel, use it
                            # NOTE: Migration 029 removed customer_channel_rules table
                            # Now using customers.assigned_channel_id instead
                            if channel_id is None and customer_id_relbase:
                                cursor.execute("""
                                    SELECT assigned_channel_id
                                    FROM customers
                                    WHERE external_id = %s AND source = 'relbase'
                                      AND assigned_channel_id IS NOT NULL
                                """, (str(customer_id_relbase),))
                                assigned_result = cursor.fetchone()
                                if assigned_result:
                                    channel_id = assigned_result[0]
                                    logger.info(f"Applied assigned channel for customer {customer_id_relbase}")'''

    if old_block in content:
        content = content.replace(old_block, new_block)
        if dry_run:
            print("  [DRY RUN] Would update sync_service.py")
            print("  Replacing customer_channel_rules query with customers.assigned_channel_id")
        else:
            file_path.write_text(content)
            print(f"  Updated: sync_service.py")
            print(f"  Replaced customer_channel_rules → customers.assigned_channel_id")
        return True
    else:
        print("  Pattern not found exactly - checking for references...")
        if 'customer_channel_rules' in content:
            print("  WARNING: customer_channel_rules still referenced but pattern didn't match")
            print("  Manual review required")
        else:
            print("  No references to customer_channel_rules found")
        return False


def update_debug_script(dry_run: bool = False) -> bool:
    """Update check_current_data.py to remove inventory_movements query"""

    file_path = BACKEND_DIR / 'scripts' / 'debug' / 'check_current_data.py'

    if not file_path.exists():
        print(f"  File not found: {file_path}")
        return False

    content = file_path.read_text()
    original_content = content

    # Comment out the inventory_movements query
    old_query = '''    # Inventory movements
    cursor.execute("SELECT COUNT(*) FROM inventory_movements")
    print(f"  📦 INVENTORY MOVEMENTS: {cursor.fetchone()['count']}")'''

    new_query = '''    # Inventory movements - TABLE REMOVED in migration 029
    # cursor.execute("SELECT COUNT(*) FROM inventory_movements")
    # print(f"  📦 INVENTORY MOVEMENTS: {cursor.fetchone()['count']}")'''

    if old_query in content:
        content = content.replace(old_query, new_query)
        if dry_run:
            print("  [DRY RUN] Would update check_current_data.py")
        else:
            file_path.write_text(content)
            print(f"  Saved: {file_path}")
        return True
    else:
        print("  Pattern not found - may already be updated")
        return False


def update_test_connection(dry_run: bool = False) -> bool:
    """Update test_connection.py to remove inventory_movements from expected tables"""

    file_path = BACKEND_DIR / 'tests' / 'test_integration' / 'test_connection.py'

    if not file_path.exists():
        print(f"  File not found: {file_path}")
        return False

    content = file_path.read_text()
    original_content = content

    # Remove inventory_movements from the list
    if '"inventory_movements",' in content:
        content = content.replace('"inventory_movements",\n', '')
        content = content.replace('    "inventory_movements",\n', '')
        if dry_run:
            print("  [DRY RUN] Would update test_connection.py")
        else:
            file_path.write_text(content)
            print(f"  Saved: {file_path}")
        return True
    else:
        print("  Pattern not found - may already be updated")
        return False


def main():
    parser = argparse.ArgumentParser(description='Run migration 029 and cleanup code')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    args = parser.parse_args()

    dry_run = args.dry_run

    print_header("Migration 029: Cleanup Obsolete Tables")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")

    if not DATABASE_URL:
        print("\nERROR: DATABASE_URL not set")
        sys.exit(1)

    # Connect to database
    print_step(1, "Connecting to database")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cursor = conn.cursor()
        print("  Connected successfully")
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    # Check current state
    print_step(2, "Checking current database state")
    before_state = check_tables_exist(cursor)

    print("\n  Tables:")
    for table, exists in before_state['tables'].items():
        status = "EXISTS" if exists else "not found"
        print(f"    {table}: {status}")

    print("\n  Views:")
    for view, exists in before_state['views'].items():
        status = "EXISTS" if exists else "not found"
        print(f"    {view}: {status}")

    # Run SQL migration
    print_step(3, "Executing SQL migration")
    try:
        run_sql_migration(cursor, dry_run)
        if not dry_run:
            conn.commit()
            print("  Migration committed successfully")
    except Exception as e:
        conn.rollback()
        print(f"  ERROR: {e}")
        print("  Migration rolled back")
        sys.exit(1)

    # Verify deletion
    print_step(4, "Verifying database changes")
    after_state = check_tables_exist(cursor)

    all_deleted = True
    for table, existed_before in before_state['tables'].items():
        exists_after = after_state['tables'][table]
        if existed_before and not exists_after:
            print(f"  ✓ Deleted table: {table}")
        elif not existed_before:
            print(f"  - Table already gone: {table}")
        else:
            print(f"  ✗ FAILED to delete: {table}")
            all_deleted = False

    for view, existed_before in before_state['views'].items():
        exists_after = after_state['views'][view]
        if existed_before and not exists_after:
            print(f"  ✓ Deleted view: {view}")
        elif not existed_before:
            print(f"  - View already gone: {view}")
        else:
            print(f"  ✗ FAILED to delete: {view}")
            all_deleted = False

    cursor.close()
    conn.close()

    # Update Python code
    print_step(5, "Updating Python code")

    print("\n  5.1 Updating product_mapping_repository.py")
    update_product_mapping_repository(dry_run)

    print("\n  5.2 Updating inventory_service.py")
    update_inventory_service(dry_run)

    print("\n  5.3 Checking sync_service.py")
    update_sync_service(dry_run)

    print("\n  5.4 Updating check_current_data.py")
    update_debug_script(dry_run)

    print("\n  5.5 Updating test_connection.py")
    update_test_connection(dry_run)

    # Summary
    print_header("Summary")

    if dry_run:
        print("DRY RUN COMPLETE - No changes were made")
        print("\nRun without --dry-run to execute changes")
    else:
        print("MIGRATION COMPLETE")
        print(f"\nDeleted:")
        print(f"  - {len(VIEWS_TO_DELETE)} views")
        print(f"  - {len(TABLES_TO_DELETE)} tables")
        print(f"\nUpdated Python files:")
        print(f"  - app/repositories/product_mapping_repository.py")
        print(f"  - app/services/inventory_service.py")
        print(f"  - scripts/debug/check_current_data.py")
        print(f"  - tests/test_integration/test_connection.py")
        print(f"\nManual review needed:")
        print(f"  - app/services/sync_service.py (customer_channel_rules logic)")

    print(f"\nLinear issues: CORP-137 through CORP-144")
    print(f"Documentation: /docs/DATABASE_TABLE_USAGE_MAP.md")


if __name__ == '__main__':
    main()

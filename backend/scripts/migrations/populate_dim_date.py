#!/usr/bin/env python3
"""
Populate dim_date dimension table with dates from 2020 to 2030

Purpose: Generate complete date dimension with hierarchies for OLAP analytics
Author: Claude Code
Date: 2025-11-12

Usage:
    export DATABASE_URL="postgresql://..."
    python3 backend/scripts/migrations/populate_dim_date.py
"""

import os
import sys
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor

# Date range to populate
START_DATE = datetime(2020, 1, 1)
END_DATE = datetime(2030, 12, 31)

# Chilean holidays (can be expanded)
CHILEAN_HOLIDAYS = {
    # Format: (month, day) - recurring holidays
    (1, 1): "Año Nuevo",
    (5, 1): "Día del Trabajo",
    (5, 21): "Día de las Glorias Navales",
    (9, 18): "Fiestas Patrias",
    (9, 19): "Día del Ejército",
    (12, 25): "Navidad",
    # Add more as needed
}


def generate_date_dimension():
    """Generate date dimension records from START_DATE to END_DATE"""

    print(f"📅 Generating date dimension from {START_DATE.date()} to {END_DATE.date()}")
    print(f"📊 Total days to generate: {(END_DATE - START_DATE).days + 1}")
    print()

    date_records = []
    current_date = START_DATE

    while current_date <= END_DATE:
        # Calculate date_id (YYYYMMDD format)
        date_id = int(current_date.strftime('%Y%m%d'))

        # Extract date components
        year = current_date.year
        month = current_date.month
        day = current_date.day

        # ISO week number (1-53)
        iso_calendar = current_date.isocalendar()
        iso_year = iso_calendar[0]
        iso_week = iso_calendar[1]
        iso_weekday = iso_calendar[2]  # 1 (Monday) to 7 (Sunday)

        # Quarter (1-4)
        quarter = (month - 1) // 3 + 1

        # Day of year (1-366)
        day_of_year = current_date.timetuple().tm_yday

        # Human-readable labels
        month_names = [
            None, "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        month_name = month_names[month]

        quarter_name = f"Q{quarter} {year}"
        year_month = current_date.strftime('%Y-%m')
        year_quarter = f"{year}-Q{quarter}"
        week_year = f"{iso_year}-W{iso_week:02d}"

        # Weekend flag (Saturday=6, Sunday=7)
        is_weekend = iso_weekday >= 6

        # Holiday flag (simple check)
        is_holiday = (month, day) in CHILEAN_HOLIDAYS

        # Fiscal year/quarter (Grana uses calendar year)
        fiscal_year = year
        fiscal_quarter = quarter

        # Build record
        record = {
            'date_id': date_id,
            'date': current_date.date(),
            'year': year,
            'quarter': quarter,
            'month': month,
            'week': iso_week,
            'day_of_week': iso_weekday,
            'day_of_month': day,
            'day_of_year': day_of_year,
            'month_name': month_name,
            'quarter_name': quarter_name,
            'year_month': year_month,
            'year_quarter': year_quarter,
            'week_year': week_year,
            'is_weekend': is_weekend,
            'is_holiday': is_holiday,
            'fiscal_year': fiscal_year,
            'fiscal_quarter': fiscal_quarter
        }

        date_records.append(record)

        # Move to next day
        current_date += timedelta(days=1)

    print(f"✅ Generated {len(date_records)} date records")
    return date_records


def insert_date_dimension(records):
    """Insert date dimension records into database"""

    print(f"\n📥 Inserting {len(records)} records into dim_date table...")

    DATABASE_URL = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    try:
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'dim_date'
            );
        """)

        if not cursor.fetchone()[0]:
            print("❌ Error: dim_date table does not exist!")
            print("   Run migration 012_create_dim_date.sql first")
            return False

        # Check current count
        cursor.execute("SELECT COUNT(*) FROM dim_date")
        current_count = cursor.fetchone()[0]

        if current_count > 0:
            print(f"⚠️  Warning: dim_date already contains {current_count} records")
            print("   This will INSERT or UPDATE existing records (UPSERT)")
            print("   Skipping confirmation for automated run...")
            # For automated runs, always proceed
            # response = input("   Continue? (y/N): ")
            # if response.lower() != 'y':
            #     print("❌ Aborted by user")
            #     return False

        # Prepare UPSERT statement (INSERT ON CONFLICT UPDATE)
        upsert_sql = """
            INSERT INTO dim_date (
                date_id, date, year, quarter, month, week, day_of_week,
                day_of_month, day_of_year, month_name, quarter_name,
                year_month, year_quarter, week_year, is_weekend, is_holiday,
                fiscal_year, fiscal_quarter
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (date_id) DO UPDATE SET
                date = EXCLUDED.date,
                year = EXCLUDED.year,
                quarter = EXCLUDED.quarter,
                month = EXCLUDED.month,
                week = EXCLUDED.week,
                day_of_week = EXCLUDED.day_of_week,
                day_of_month = EXCLUDED.day_of_month,
                day_of_year = EXCLUDED.day_of_year,
                month_name = EXCLUDED.month_name,
                quarter_name = EXCLUDED.quarter_name,
                year_month = EXCLUDED.year_month,
                year_quarter = EXCLUDED.year_quarter,
                week_year = EXCLUDED.week_year,
                is_weekend = EXCLUDED.is_weekend,
                is_holiday = EXCLUDED.is_holiday,
                fiscal_year = EXCLUDED.fiscal_year,
                fiscal_quarter = EXCLUDED.fiscal_quarter
        """

        # Batch insert (1000 at a time)
        batch_size = 1000
        inserted = 0

        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]

            # Convert dict records to tuples in the correct order
            batch_tuples = [
                (
                    r['date_id'], r['date'], r['year'], r['quarter'], r['month'], r['week'],
                    r['day_of_week'], r['day_of_month'], r['day_of_year'], r['month_name'],
                    r['quarter_name'], r['year_month'], r['year_quarter'], r['week_year'],
                    r['is_weekend'], r['is_holiday'], r['fiscal_year'], r['fiscal_quarter']
                )
                for r in batch
            ]

            cursor.executemany(upsert_sql, batch_tuples)
            inserted += len(batch)

            if inserted % 1000 == 0:
                print(f"   Progress: {inserted}/{len(records)} records ({inserted/len(records)*100:.1f}%)")

        conn.commit()

        # Verify final count
        cursor.execute("SELECT COUNT(*) FROM dim_date")
        final_count = cursor.fetchone()[0]

        print(f"\n✅ Successfully inserted/updated {len(records)} records")
        print(f"📊 Total records in dim_date: {final_count}")

        # Show sample records
        cursor.execute("""
            SELECT date_id, date, year_month, quarter_name, is_weekend, is_holiday
            FROM dim_date
            ORDER BY date
            LIMIT 5
        """)

        print("\n📋 Sample records (first 5):")
        for row in cursor.fetchall():
            date_id, date, year_month, quarter_name, is_weekend, is_holiday = row
            print(f"   {date_id}: {date} ({year_month}) - "
                  f"{quarter_name} - Weekend: {is_weekend} - Holiday: {is_holiday}")

        return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Error inserting records: {e}")
        return False

    finally:
        cursor.close()
        conn.close()


def main():
    """Main execution"""
    print("="*60)
    print("🗓️  DIM_DATE POPULATION SCRIPT")
    print("="*60)
    print()

    # Check DATABASE_URL
    if not os.getenv("DATABASE_URL"):
        print("❌ Error: DATABASE_URL environment variable not set")
        print("   Set it before running this script")
        return 1

    # Generate records
    records = generate_date_dimension()

    # Insert into database
    success = insert_date_dimension(records)

    if success:
        print("\n" + "="*60)
        print("✅ DIM_DATE POPULATION COMPLETE")
        print("="*60)
        return 0
    else:
        print("\n" + "="*60)
        print("❌ DIM_DATE POPULATION FAILED")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

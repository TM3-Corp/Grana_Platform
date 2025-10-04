#!/usr/bin/env python3
"""
Test Conversion Service - Comprehensive testing of unit conversions

Author: TM3
Date: 2025-10-03
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from app.services.conversion_service import ConversionService

def print_test_header(test_name):
    print(f"\n{'='*60}")
    print(f"🧪 TEST: {test_name}")
    print(f"{'='*60}")

def test_basic_conversions():
    """Test basic unit conversions for Barrita de Chía"""
    print_test_header("Basic Conversions - Barrita de Chía")

    database_url = os.getenv('DATABASE_URL')
    service = ConversionService(database_url)

    sku = 'BAR-CHIA-001'

    # Test 1: Units to Boxes
    units = 720
    boxes = service.units_to_boxes(sku, units)
    expected = 5.0  # 720 / 144 = 5
    assert float(boxes) == expected, f"Expected {expected}, got {boxes}"
    print(f"✅ {units} units = {boxes} boxes (expected {expected})")

    # Test 2: Boxes to Units
    boxes = 3
    units = service.boxes_to_units(sku, boxes)
    expected = 432  # 3 * 144
    assert units == expected, f"Expected {expected}, got {units}"
    print(f"✅ {boxes} boxes = {units} units (expected {expected})")

    # Test 3: Units to Displays
    units = 36
    displays = service.units_to_displays(sku, units)
    expected = 3.0  # 36 / 12
    assert float(displays) == expected, f"Expected {expected}, got {displays}"
    print(f"✅ {units} units = {displays} displays (expected {expected})")

    # Test 4: Units to Pallets
    units = 2880
    pallets = service.units_to_pallets(sku, units)
    expected = 1.0  # 2880 / 2880
    assert float(pallets) == expected, f"Expected {expected}, got {pallets}"
    print(f"✅ {units} units = {pallets} pallets (expected {expected})")

def test_universal_converter():
    """Test universal convert() method"""
    print_test_header("Universal Converter")

    database_url = os.getenv('DATABASE_URL')
    service = ConversionService(database_url)

    sku = 'GRA-250-001'  # Granola: 6 units/display, 8 displays/box = 48 units/box

    # Test: Box to Units
    result = service.convert(sku, 2, 'box', 'unit')
    expected = 96  # 2 boxes * 48 units/box
    assert float(result) == expected, f"Expected {expected}, got {result}"
    print(f"✅ 2 boxes = {result} units (expected {expected})")

    # Test: Units to Box
    result = service.convert(sku, 144, 'unit', 'box')
    expected = 3.0  # 144 / 48
    assert float(result) == expected, f"Expected {expected}, got {result}"
    print(f"✅ 144 units = {result} boxes (expected {expected})")

    # Test: Display to Units
    result = service.convert(sku, 5, 'display', 'unit')
    expected = 30  # 5 displays * 6 units/display
    assert float(result) == expected, f"Expected {expected}, got {result}"
    print(f"✅ 5 displays = {result} units (expected {expected})")

def test_mixed_order_calculation():
    """Test calculating total units from a mixed order"""
    print_test_header("Mixed Order Calculation")

    database_url = os.getenv('DATABASE_URL')
    service = ConversionService(database_url)

    # Simulate a complex B2B order
    order_items = [
        {'sku': 'BAR-CHIA-001', 'quantity': 5, 'unit': 'box'},      # 5 * 144 = 720 units
        {'sku': 'GRA-250-001', 'quantity': 2, 'unit': 'display'},   # 2 * 6 = 12 units
        {'sku': 'MIX-FRUTOS-001', 'quantity': 50, 'unit': 'unit'}   # 50 units
    ]

    totals = service.calculate_order_total_units(order_items)

    print(f"Order items:")
    for item in order_items:
        print(f"  • {item['sku']}: {item['quantity']} {item['unit']}(s)")

    print(f"\nCalculated totals:")
    expected_totals = {
        'BAR-CHIA-001': 720,
        'GRA-250-001': 12,
        'MIX-FRUTOS-001': 50
    }

    for sku, units in totals.items():
        expected = expected_totals[sku]
        assert units == expected, f"Expected {expected} for {sku}, got {units}"
        print(f"  ✅ {sku}: {units} units (expected {expected})")

def test_stock_availability():
    """Test stock availability checking"""
    print_test_header("Stock Availability Check")

    database_url = os.getenv('DATABASE_URL')
    service = ConversionService(database_url)

    # Order that fits within stock
    order_items = [
        {'sku': 'BAR-CHIA-001', 'quantity': 5, 'unit': 'box'},  # 720 units (stock: 2000)
    ]

    stock_status = service.check_stock_availability(order_items)
    sku = 'BAR-CHIA-001'

    print(f"Order: 5 boxes of {stock_status[sku]['product_name']}")
    print(f"  Requested: {stock_status[sku]['requested']} units")
    print(f"  Available: {stock_status[sku]['available']} units")
    print(f"  Sufficient: {'✅ YES' if stock_status[sku]['sufficient'] else '❌ NO'}")
    print(f"  Shortage: {stock_status[sku]['shortage']} units")

    assert stock_status[sku]['sufficient'] == True, "Should have sufficient stock"
    print("\n✅ Stock check passed")

def test_channel_formatting():
    """Test quantity formatting for different channels"""
    print_test_header("Channel-Specific Formatting")

    database_url = os.getenv('DATABASE_URL')
    service = ConversionService(database_url)

    sku = 'BAR-CHIA-001'
    units = 720  # 5 boxes

    # B2C format (should show units)
    b2c = service.format_quantity_for_channel(sku, units, 'b2c')
    print(f"B2C format: {b2c['display_text']}")
    assert b2c['unit'] == 'unit', "B2C should use units"

    # Retail format (should show boxes)
    retail = service.format_quantity_for_channel(sku, units, 'retail')
    print(f"Retail format: {retail['display_text']}")
    assert retail['unit'] == 'box', "Retail should use boxes"

    print("\n✅ Channel formatting passed")

def test_conversion_summary():
    """Test comprehensive conversion summary"""
    print_test_header("Conversion Summary")

    database_url = os.getenv('DATABASE_URL')
    service = ConversionService(database_url)

    sku = 'MIX-FRUTOS-001'
    units = 1200

    summary = service.get_conversion_summary(sku, units)

    print(f"Product: {summary['product_name']} ({sku})")
    print(f"Quantity: {units} units")
    print(f"\nConversions:")
    print(f"  • {summary['quantity_displays']} {summary['unit_names']['display']}")
    print(f"  • {summary['quantity_boxes']} {summary['unit_names']['box']}")
    print(f"  • {summary['quantity_pallets']} {summary['unit_names']['pallet']}")
    print(f"\nFactors:")
    print(f"  • {summary['conversion_factors']['units_per_display']} units per display")
    print(f"  • {summary['conversion_factors']['units_per_box']} units per box")
    print(f"  • {summary['conversion_factors']['units_per_pallet']} units per pallet")

    # Verify calculations
    expected_boxes = 1200 / 120  # 10 boxes
    assert summary['quantity_boxes'] == expected_boxes, f"Expected {expected_boxes} boxes"

    print("\n✅ Conversion summary passed")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("🚀 STARTING CONVERSION SERVICE TESTS")
    print("="*60)

    try:
        test_basic_conversions()
        test_universal_converter()
        test_mixed_order_calculation()
        test_stock_availability()
        test_channel_formatting()
        test_conversion_summary()

        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\n📊 Summary:")
        print("  • Basic conversions: ✅")
        print("  • Universal converter: ✅")
        print("  • Mixed order calculation: ✅")
        print("  • Stock availability: ✅")
        print("  • Channel formatting: ✅")
        print("  • Conversion summary: ✅")
        print("\n🎉 Conversion Engine is working perfectly!")

        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

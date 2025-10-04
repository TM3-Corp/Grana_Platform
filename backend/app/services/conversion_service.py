"""
Conversion Service - Core business logic for unit conversions
Handles conversions between units, displays, boxes, and pallets

Author: TM3
Date: 2025-10-03
"""
from typing import Dict, Tuple, Optional, List
from decimal import Decimal, ROUND_HALF_UP
import psycopg2
from psycopg2.extras import RealDictCursor


class ConversionService:
    """
    Service for converting between different product units

    Hierarchy:
    1 unit → X units = 1 display → Y displays = 1 box → Z boxes = 1 pallet

    Example (Barrita de Chía):
    1 unit → 12 units = 1 display → 12 displays = 1 box (144 units) → 20 boxes = 1 pallet (2,880 units)
    """

    def __init__(self, db_connection_string: str):
        self.db_connection_string = db_connection_string

    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_connection_string)

    def get_product_conversion_info(self, sku: str) -> Optional[Dict]:
        """
        Get conversion info for a product by SKU

        Args:
            sku: Product SKU

        Returns:
            Dict with conversion info or None if product not found
        """
        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM v_product_conversion
                    WHERE sku = %s
                """, (sku,))
                return cursor.fetchone()
        finally:
            conn.close()

    def units_to_displays(self, sku: str, units: int) -> Decimal:
        """Convert units to displays"""
        info = self.get_product_conversion_info(sku)
        if not info:
            raise ValueError(f"Product not found: {sku}")

        units_per_display = info['units_per_display']
        if units_per_display == 0:
            raise ValueError(f"Invalid units_per_display for {sku}: {units_per_display}")

        return Decimal(units) / Decimal(units_per_display)

    def units_to_boxes(self, sku: str, units: int) -> Decimal:
        """Convert units to boxes"""
        info = self.get_product_conversion_info(sku)
        if not info:
            raise ValueError(f"Product not found: {sku}")

        units_per_box = info['units_per_box']
        if units_per_box == 0:
            raise ValueError(f"Invalid units_per_box for {sku}: {units_per_box}")

        result = Decimal(units) / Decimal(units_per_box)
        return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def units_to_pallets(self, sku: str, units: int) -> Decimal:
        """Convert units to pallets"""
        info = self.get_product_conversion_info(sku)
        if not info:
            raise ValueError(f"Product not found: {sku}")

        units_per_pallet = info['units_per_pallet']
        if units_per_pallet == 0:
            raise ValueError(f"Invalid units_per_pallet for {sku}: {units_per_pallet}")

        result = Decimal(units) / Decimal(units_per_pallet)
        return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    def displays_to_units(self, sku: str, displays: int) -> int:
        """Convert displays to units"""
        info = self.get_product_conversion_info(sku)
        if not info:
            raise ValueError(f"Product not found: {sku}")

        return displays * info['units_per_display']

    def boxes_to_units(self, sku: str, boxes: int) -> int:
        """Convert boxes to units"""
        info = self.get_product_conversion_info(sku)
        if not info:
            raise ValueError(f"Product not found: {sku}")

        return boxes * info['units_per_box']

    def pallets_to_units(self, sku: str, pallets: int) -> int:
        """Convert pallets to units"""
        info = self.get_product_conversion_info(sku)
        if not info:
            raise ValueError(f"Product not found: {sku}")

        return pallets * info['units_per_pallet']

    def convert(self, sku: str, quantity: float, from_unit: str, to_unit: str) -> Decimal:
        """
        Universal converter between any two units

        Args:
            sku: Product SKU
            quantity: Quantity to convert
            from_unit: Source unit ('unit', 'display', 'box', 'pallet')
            to_unit: Target unit ('unit', 'display', 'box', 'pallet')

        Returns:
            Converted quantity
        """
        # First, convert to units (base unit)
        if from_unit == 'unit':
            units = int(quantity)
        elif from_unit == 'display':
            units = self.displays_to_units(sku, int(quantity))
        elif from_unit == 'box':
            units = self.boxes_to_units(sku, int(quantity))
        elif from_unit == 'pallet':
            units = self.pallets_to_units(sku, int(quantity))
        else:
            raise ValueError(f"Invalid from_unit: {from_unit}")

        # Then convert from units to target unit
        if to_unit == 'unit':
            return Decimal(units)
        elif to_unit == 'display':
            return self.units_to_displays(sku, units)
        elif to_unit == 'box':
            return self.units_to_boxes(sku, units)
        elif to_unit == 'pallet':
            return self.units_to_pallets(sku, units)
        else:
            raise ValueError(f"Invalid to_unit: {to_unit}")

    def calculate_order_total_units(self, order_items: List[Dict]) -> Dict[str, int]:
        """
        Calculate total units from a mixed order

        Args:
            order_items: List of items like:
                [
                    {'sku': 'BAR-CHIA-001', 'quantity': 5, 'unit': 'box'},
                    {'sku': 'GRA-250-001', 'quantity': 2, 'unit': 'display'},
                    {'sku': 'MIX-FRUTOS-001', 'quantity': 50, 'unit': 'unit'}
                ]

        Returns:
            Dict with total units per SKU: {'BAR-CHIA-001': 720, 'GRA-250-001': 12, ...}
        """
        totals = {}

        for item in order_items:
            sku = item['sku']
            quantity = item['quantity']
            unit = item.get('unit', 'unit')

            # Convert to units
            units = int(self.convert(sku, quantity, unit, 'unit'))

            # Add to totals
            if sku in totals:
                totals[sku] += units
            else:
                totals[sku] = units

        return totals

    def check_stock_availability(self, order_items: List[Dict]) -> Dict[str, Dict]:
        """
        Check if there's enough stock for an order

        Args:
            order_items: List of items (same format as calculate_order_total_units)

        Returns:
            Dict with stock status per SKU:
            {
                'BAR-CHIA-001': {
                    'requested': 720,
                    'available': 1440,
                    'sufficient': True,
                    'shortage': 0
                },
                ...
            }
        """
        totals = self.calculate_order_total_units(order_items)
        stock_status = {}

        conn = self.get_db_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                for sku, requested_units in totals.items():
                    # Get current stock
                    cursor.execute("""
                        SELECT current_stock, name
                        FROM products
                        WHERE sku = %s
                    """, (sku,))
                    result = cursor.fetchone()

                    if not result:
                        stock_status[sku] = {
                            'requested': requested_units,
                            'available': 0,
                            'sufficient': False,
                            'shortage': requested_units,
                            'error': 'Product not found'
                        }
                        continue

                    available = result['current_stock']
                    sufficient = available >= requested_units
                    shortage = max(0, requested_units - available)

                    stock_status[sku] = {
                        'product_name': result['name'],
                        'requested': requested_units,
                        'available': available,
                        'sufficient': sufficient,
                        'shortage': shortage
                    }
        finally:
            conn.close()

        return stock_status

    def format_quantity_for_channel(self, sku: str, units: int, channel_type: str) -> Dict[str, any]:
        """
        Format quantity according to channel preferences

        Args:
            sku: Product SKU
            units: Quantity in units
            channel_type: 'b2c', 'retail', 'marketplace', 'direct'

        Returns:
            Formatted quantity with preferred unit for channel
        """
        info = self.get_product_conversion_info(sku)
        if not info:
            raise ValueError(f"Product not found: {sku}")

        # Channel preferences
        if channel_type == 'b2c' or channel_type == 'marketplace':
            # B2C prefers units
            return {
                'quantity': units,
                'unit': 'unit',
                'display_text': f"{units} {info['unit_name']}"
            }
        elif channel_type == 'retail':
            # Retail prefers boxes
            boxes = self.units_to_boxes(sku, units)
            return {
                'quantity': float(boxes),
                'unit': 'box',
                'display_text': f"{boxes} {info['box_name']}",
                'detail': f"({units} {info['unit_name']})"
            }
        else:
            # Direct sales can be mixed
            boxes = self.units_to_boxes(sku, units)
            remaining_units = units % info['units_per_box']

            if remaining_units == 0:
                return {
                    'quantity': float(boxes),
                    'unit': 'box',
                    'display_text': f"{boxes} {info['box_name']}"
                }
            else:
                full_boxes = int(boxes)
                return {
                    'quantity': units,
                    'unit': 'mixed',
                    'display_text': f"{full_boxes} {info['box_name']} + {remaining_units} {info['unit_name']}"
                }

    def get_conversion_summary(self, sku: str, units: int) -> Dict:
        """
        Get a complete conversion summary for a quantity

        Args:
            sku: Product SKU
            units: Quantity in units

        Returns:
            Complete conversion info in all units
        """
        info = self.get_product_conversion_info(sku)
        if not info:
            raise ValueError(f"Product not found: {sku}")

        return {
            'sku': sku,
            'product_name': info['name'],
            'quantity_units': units,
            'quantity_displays': float(self.units_to_displays(sku, units)),
            'quantity_boxes': float(self.units_to_boxes(sku, units)),
            'quantity_pallets': float(self.units_to_pallets(sku, units)),
            'unit_names': {
                'unit': info['unit_name'],
                'display': info['display_name'],
                'box': info['box_name'],
                'pallet': info['pallet_name']
            },
            'conversion_factors': {
                'units_per_display': info['units_per_display'],
                'displays_per_box': info['displays_per_box'],
                'boxes_per_pallet': info['boxes_per_pallet'],
                'units_per_box': info['units_per_box'],
                'units_per_pallet': info['units_per_pallet']
            }
        }

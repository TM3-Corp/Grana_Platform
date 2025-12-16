"""
SKU Mapping Service
Database-driven SKU mapping that replaces hardcoded rules in audit.py

Purpose:
- Map raw SKUs to official catalog SKUs using database rules
- Support multiple pattern types (exact, prefix, suffix, regex, contains)
- Provide caching for performance
- Enable UI-driven rule management

Author: TM3
Date: 2025-12-10
"""
import os
import re
import time
from typing import Optional, Dict, List
from dataclasses import dataclass
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor


@dataclass
class MappingResult:
    """Result of a SKU mapping operation"""
    target_sku: str
    quantity_multiplier: int
    match_type: str
    confidence: int
    rule_id: int
    rule_name: Optional[str]


class SKUMappingService:
    """
    Database-driven SKU mapping service.

    Replaces the 13+ hardcoded transformation rules in audit.py
    with configurable database rules that can be managed via UI.

    Features:
    - Caching with TTL for performance
    - Multiple pattern types (exact, prefix, suffix, regex, contains)
    - Source filtering (e.g., only apply to mercadolibre orders)
    - Priority-based rule evaluation
    - Quantity multipliers for PACK rules
    """

    # Cache TTL in seconds (5 minutes)
    CACHE_TTL = 300

    def __init__(self):
        """Initialize service with database connection"""
        self._mappings_cache: Optional[List[Dict]] = None
        self._cache_timestamp: Optional[float] = None
        self._connection_string = self._get_database_url()

    def _get_database_url(self) -> str:
        """
        Get database connection string

        Priority:
        1. Environment variable DATABASE_URL
        2. backend/.env file
        3. Hardcoded Session Pooler URL (WSL2 compatible)
        """
        # Check environment variable first
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return db_url

        # Try loading from .env file
        env_path = Path(__file__).parent.parent.parent / '.env'
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('DATABASE_URL='):
                        return line.split('=', 1)[1].strip().strip('"').strip("'")

        # Fallback: Hardcoded Session Pooler URL (IPv4 - works in WSL2)
        return "postgresql://postgres.lypuvibmtxjaxmcmahxr:%24Ilofono1@aws-1-sa-east-1.pooler.supabase.com:6543/postgres"

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid based on TTL"""
        if self._mappings_cache is None or self._cache_timestamp is None:
            return False
        return (time.time() - self._cache_timestamp) < self.CACHE_TTL

    def _load_mappings_from_database(self) -> List[Dict]:
        """
        Load all active mapping rules from database.

        Returns:
            List of mapping dictionaries ordered by priority DESC
        """
        mappings = []

        try:
            conn = psycopg2.connect(self._connection_string, connect_timeout=10)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT
                    id,
                    source_pattern,
                    pattern_type,
                    source_filter,
                    target_sku,
                    quantity_multiplier,
                    rule_name,
                    confidence,
                    priority
                FROM sku_mappings
                WHERE is_active = TRUE
                ORDER BY priority DESC, id ASC
            """)

            mappings = [dict(row) for row in cursor.fetchall()]

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"Warning: Failed to load SKU mappings from database: {e}")

        return mappings

    def get_all_active_mappings(self) -> List[Dict]:
        """
        Get all active mappings, using cache if valid.

        Returns:
            List of mapping dictionaries
        """
        if not self._is_cache_valid():
            self._mappings_cache = self._load_mappings_from_database()
            self._cache_timestamp = time.time()

        return self._mappings_cache or []

    def invalidate_cache(self):
        """
        Invalidate the cache to force reload from database.

        Call this after any CRUD operation on sku_mappings table.
        """
        self._mappings_cache = None
        self._cache_timestamp = None

    def reload_mappings(self):
        """Force reload mappings from database"""
        self.invalidate_cache()
        self._mappings_cache = self._load_mappings_from_database()
        self._cache_timestamp = time.time()

    def _matches_pattern(self, sku: str, mapping: Dict, source: Optional[str]) -> bool:
        """
        Check if a SKU matches the mapping pattern.

        Args:
            sku: Raw SKU to test
            mapping: Mapping rule dictionary
            source: Data source (e.g., 'relbase', 'mercadolibre')

        Returns:
            True if SKU matches the pattern
        """
        # Check source filter first
        source_filter = mapping.get('source_filter')
        if source_filter and source and source.lower() != source_filter.lower():
            return False

        pattern = mapping['source_pattern']
        pattern_type = mapping['pattern_type']

        if pattern_type == 'exact':
            return sku == pattern

        elif pattern_type == 'prefix':
            return sku.startswith(pattern)

        elif pattern_type == 'suffix':
            return sku.endswith(pattern)

        elif pattern_type == 'contains':
            return pattern in sku

        elif pattern_type == 'regex':
            try:
                return re.match(pattern, sku) is not None
            except re.error:
                # Invalid regex pattern
                return False

        return False

    def map_sku(self, raw_sku: str, source: Optional[str] = None) -> Optional[MappingResult]:
        """
        Map a raw SKU to a catalog SKU using database rules.

        Rules are evaluated in priority order (highest first).
        First matching rule wins.

        Args:
            raw_sku: Raw SKU as it appears in orders
            source: Data source (e.g., 'relbase', 'mercadolibre', 'shopify')

        Returns:
            MappingResult if a rule matches, None otherwise

        Examples:
            map_sku('PACKBAMC_U04010') → MappingResult(target_sku='BAMC_U04010', quantity_multiplier=5, ...)
            map_sku('MLC1630337051', 'mercadolibre') → MappingResult(target_sku='BABE_U20010', ...)
            map_sku('BAMC_U04010') → None (direct catalog match, no mapping needed)
        """
        if not raw_sku:
            return None

        raw_sku = raw_sku.strip()
        mappings = self.get_all_active_mappings()

        for mapping in mappings:
            if self._matches_pattern(raw_sku, mapping, source):
                return MappingResult(
                    target_sku=mapping['target_sku'],
                    quantity_multiplier=mapping.get('quantity_multiplier', 1),
                    match_type=mapping['pattern_type'],
                    confidence=mapping.get('confidence', 100),
                    rule_id=mapping['id'],
                    rule_name=mapping.get('rule_name')
                )

        # No mapping found
        return None

    def test_sku(self, raw_sku: str, source: Optional[str] = None) -> Dict:
        """
        Test a SKU against all active rules (for preview in UI).

        Args:
            raw_sku: SKU to test
            source: Optional source filter

        Returns:
            Dictionary with test results:
            {
                'input_sku': 'PACKBAMC_U04010',
                'source': 'relbase',
                'matched': True,
                'result': {
                    'target_sku': 'BAMC_U04010',
                    'quantity_multiplier': 5,
                    'match_type': 'prefix',
                    'confidence': 90,
                    'rule_id': 123,
                    'rule_name': 'Pack prefix removal'
                }
            }
        """
        result = self.map_sku(raw_sku, source)

        response = {
            'input_sku': raw_sku,
            'source': source,
            'matched': result is not None
        }

        if result:
            response['result'] = {
                'target_sku': result.target_sku,
                'quantity_multiplier': result.quantity_multiplier,
                'match_type': result.match_type,
                'confidence': result.confidence,
                'rule_id': result.rule_id,
                'rule_name': result.rule_name
            }

        return response

    def get_mapping_stats(self) -> Dict:
        """
        Get statistics about current mappings.

        Returns:
            Dictionary with stats:
            {
                'total': 193,
                'active': 190,
                'by_type': {'exact': 185, 'prefix': 3, ...},
                'by_source': {'mercadolibre': 17, None: 173},
                'cache_valid': True
            }
        """
        mappings = self.get_all_active_mappings()

        by_type = {}
        by_source = {}

        for m in mappings:
            # Count by type
            ptype = m.get('pattern_type', 'unknown')
            by_type[ptype] = by_type.get(ptype, 0) + 1

            # Count by source
            source = m.get('source_filter') or 'all'
            by_source[source] = by_source.get(source, 0) + 1

        return {
            'total': len(mappings),
            'by_type': by_type,
            'by_source': by_source,
            'cache_valid': self._is_cache_valid()
        }


# Singleton instance for use across the application
_sku_mapping_service: Optional[SKUMappingService] = None


def get_sku_mapping_service() -> SKUMappingService:
    """Get or create the SKUMappingService singleton"""
    global _sku_mapping_service
    if _sku_mapping_service is None:
        _sku_mapping_service = SKUMappingService()
    return _sku_mapping_service

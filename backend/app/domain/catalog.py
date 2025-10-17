"""
Official Grana Product Catalog
Single Source of Truth for all products

Based on: public/Archivos_Compartidos/CÓDIGOS GRANA.csv
Last updated: October 2025

Author: TM3
Date: 2025-10-17
"""
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from enum import Enum


class ProductCategory(str, Enum):
    """Product categories"""
    GRANOLAS = "GRANOLAS"
    BARRAS = "BARRAS"
    CRACKERS = "CRACKERS"
    KEEPERS = "KEEPERS"
    KRUMS = "KRUMS"


class PackageType(str, Enum):
    """Package types"""
    DISPLAY = "DISPLAY"
    DOYPACK = "DOYPACK"
    GRANEL = "GRANEL"
    SACHET = "SACHET"
    UNIDAD = "UNIDAD"
    BANDEJA = "BANDEJA"
    BOLSA = "BOLSA"


@dataclass
class OfficialProduct:
    """Official product definition from Grana catalog"""
    sku: str
    category: ProductCategory
    product_name: str
    base_code: str  # BAKC, GRAL, CRSM, etc.
    package_type: PackageType
    units_per_display: int

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['category'] = self.category.value
        data['package_type'] = self.package_type.value
        return data


# ================================================================================
# OFFICIAL PRODUCT CATALOG
# ================================================================================
# This is the authoritative source for all Grana products
# All product mapping, variants, and equivalents reference this catalog
# ================================================================================

OFFICIAL_CATALOG: Dict[str, OfficialProduct] = {
    # ===== GRANOLAS =====

    # Low Carb Almendras
    "GRAL_U26010": OfficialProduct(
        sku="GRAL_U26010",
        category=ProductCategory.GRANOLAS,
        product_name="GRANOLA LOW CARB ALMENDRAS 260",
        base_code="GRAL",
        package_type=PackageType.DISPLAY,
        units_per_display=1
    ),
    "GRAL_U1000H": OfficialProduct(
        sku="GRAL_U1000H",
        category=ProductCategory.GRANOLAS,
        product_name="GRANOLA LOW CARB ALMENDRAS 1 KILO",
        base_code="GRAL",
        package_type=PackageType.BOLSA,
        units_per_display=1
    ),

    # Low Carb Cacao
    "GRCA_U26010": OfficialProduct(
        sku="GRCA_U26010",
        category=ProductCategory.GRANOLAS,
        product_name="GRANOLA LOW CARB CACAO 260",
        base_code="GRCA",
        package_type=PackageType.DOYPACK,
        units_per_display=1
    ),
    "GRCA_U1000H": OfficialProduct(
        sku="GRCA_U1000H",
        category=ProductCategory.GRANOLAS,
        product_name="GRANOLA LOW CARB CACAO 1 KILO",
        base_code="GRCA",
        package_type=PackageType.BOLSA,
        units_per_display=1
    ),

    # Low Carb Berries
    "GRBE_U26010": OfficialProduct(
        sku="GRBE_U26010",
        category=ProductCategory.GRANOLAS,
        product_name="GRANOLA LOW CARB BERRIES 260",
        base_code="GRBE",
        package_type=PackageType.DISPLAY,
        units_per_display=1
    ),
    "GRBE_U1000H": OfficialProduct(
        sku="GRBE_U1000H",
        category=ProductCategory.GRANOLAS,
        product_name="GRANOLA LOW CARB BERRIES 1 KILO",
        base_code="GRBE",
        package_type=PackageType.BOLSA,
        units_per_display=1
    ),

    # Keto Nuez
    "GRKC_U21010": OfficialProduct(
        sku="GRKC_U21010",
        category=ProductCategory.GRANOLAS,
        product_name="GRANOLA KETO NUEZ 210",
        base_code="GRKC",
        package_type=PackageType.DOYPACK,
        units_per_display=1
    ),
    "GRKC_U1000H": OfficialProduct(
        sku="GRKC_U1000H",
        category=ProductCategory.GRANOLAS,
        product_name="GRANOLA KETO NUEZ 1 KILO",
        base_code="GRKC",
        package_type=PackageType.BOLSA,
        units_per_display=1
    ),

    # Protein Almendras
    "GPAA_U24010": OfficialProduct(
        sku="GPAA_U24010",
        category=ProductCategory.GRANOLAS,
        product_name="GRANOLA PROTEIN ALMENDRAS 240",
        base_code="GPAA",
        package_type=PackageType.DISPLAY,
        units_per_display=1
    ),
    "GPAA_U04010": OfficialProduct(
        sku="GPAA_U04010",
        category=ProductCategory.GRANOLAS,
        product_name="GRANOLA PROTEIN ALMENDRAS SACHET 40 X1",
        base_code="GPAA",
        package_type=PackageType.SACHET,
        units_per_display=1
    ),

    # Protein Cacao
    "GPCC_U24010": OfficialProduct(
        sku="GPCC_U24010",
        category=ProductCategory.GRANOLAS,
        product_name="GRANOLA PROTEIN CACAO 240",
        base_code="GPCC",
        package_type=PackageType.DISPLAY,
        units_per_display=1
    ),
    "GPCC_U04010": OfficialProduct(
        sku="GPCC_U04010",
        category=ProductCategory.GRANOLAS,
        product_name="GRANOLA PROTEIN CACAO SACHET 40 X1",
        base_code="GPCC",
        package_type=PackageType.SACHET,
        units_per_display=1
    ),

    # Protein Berries
    "GPBB_U24010": OfficialProduct(
        sku="GPBB_U24010",
        category=ProductCategory.GRANOLAS,
        product_name="GRANOLA PROTEIN BERRIES 240",
        base_code="GPBB",
        package_type=PackageType.DISPLAY,
        units_per_display=1
    ),
    "GPBB_U04010": OfficialProduct(
        sku="GPBB_U04010",
        category=ProductCategory.GRANOLAS,
        product_name="GRANOLA PROTEIN BERRIES SACHET 40 X1",
        base_code="GPBB",
        package_type=PackageType.SACHET,
        units_per_display=1
    ),

    # ===== BARRAS =====

    # Low Carb Cacao Maní
    "BACM_U04010": OfficialProduct(
        sku="BACM_U04010",
        category=ProductCategory.BARRAS,
        product_name="BARRA LOW CARB CACAO MANÍ X1",
        base_code="BACM",
        package_type=PackageType.GRANEL,
        units_per_display=1
    ),
    "BACM_U20010": OfficialProduct(
        sku="BACM_U20010",
        category=ProductCategory.BARRAS,
        product_name="BARRA LOW CARB CACAO MANÍ X5",
        base_code="BACM",
        package_type=PackageType.DISPLAY,
        units_per_display=5
    ),
    "BACM_U64010": OfficialProduct(
        sku="BACM_U64010",
        category=ProductCategory.BARRAS,
        product_name="BARRA LOW CARB CACAO MANÍ X16",
        base_code="BACM",
        package_type=PackageType.DISPLAY,
        units_per_display=16
    ),

    # Low Carb Manzana Canela
    "BAMC_U04010": OfficialProduct(
        sku="BAMC_U04010",
        category=ProductCategory.BARRAS,
        product_name="BARRA LOW CARB MANZANA CANELA X1",
        base_code="BAMC",
        package_type=PackageType.GRANEL,
        units_per_display=1
    ),
    "BAMC_U20010": OfficialProduct(
        sku="BAMC_U20010",
        category=ProductCategory.BARRAS,
        product_name="BARRA LOW CARB MANZANA CANELA X5",
        base_code="BAMC",
        package_type=PackageType.DISPLAY,
        units_per_display=5
    ),
    "BAMC_U64010": OfficialProduct(
        sku="BAMC_U64010",
        category=ProductCategory.BARRAS,
        product_name="BARRA LOW CARB MANZANA CANELA X16",
        base_code="BAMC",
        package_type=PackageType.DISPLAY,
        units_per_display=16
    ),

    # Low Carb Berries
    "BABE_U04010": OfficialProduct(
        sku="BABE_U04010",
        category=ProductCategory.BARRAS,
        product_name="BARRA LOW CARB BERRIES X1",
        base_code="BABE",
        package_type=PackageType.GRANEL,
        units_per_display=1
    ),
    "BABE_U20010": OfficialProduct(
        sku="BABE_U20010",
        category=ProductCategory.BARRAS,
        product_name="BARRA LOW CARB BERRIES X5",
        base_code="BABE",
        package_type=PackageType.DISPLAY,
        units_per_display=5
    ),
    "BABE_U64010": OfficialProduct(
        sku="BABE_U64010",
        category=ProductCategory.BARRAS,
        product_name="BARRA LOW CARB BERRIES X16",
        base_code="BABE",
        package_type=PackageType.DISPLAY,
        units_per_display=16
    ),

    # Keto Nuez
    "BAKC_U04010": OfficialProduct(
        sku="BAKC_U04010",
        category=ProductCategory.BARRAS,
        product_name="BARRA KETO NUEZ X1",
        base_code="BAKC",
        package_type=PackageType.GRANEL,
        units_per_display=1
    ),
    "BAKC_U20010": OfficialProduct(
        sku="BAKC_U20010",
        category=ProductCategory.BARRAS,
        product_name="BARRA KETO NUEZ X5",
        base_code="BAKC",
        package_type=PackageType.DISPLAY,
        units_per_display=5
    ),
    "BAKC_U64010": OfficialProduct(
        sku="BAKC_U64010",
        category=ProductCategory.BARRAS,
        product_name="BARRA KETO NUEZ X16",
        base_code="BAKC",
        package_type=PackageType.DISPLAY,
        units_per_display=16
    ),

    # Keto Almendra
    "BAKA_U04010": OfficialProduct(
        sku="BAKA_U04010",
        category=ProductCategory.BARRAS,
        product_name="BARRA KETO ALMENDRA X1",
        base_code="BAKA",
        package_type=PackageType.GRANEL,
        units_per_display=1
    ),
    "BAKA_U20010": OfficialProduct(
        sku="BAKA_U20010",
        category=ProductCategory.BARRAS,
        product_name="BARRA KETO ALMENDRA X5",
        base_code="BAKA",
        package_type=PackageType.DISPLAY,
        units_per_display=5
    ),
    "BAKA_U64010": OfficialProduct(
        sku="BAKA_U64010",
        category=ProductCategory.BARRAS,
        product_name="BARRA KETO ALMENDRA X16",
        base_code="BAKA",
        package_type=PackageType.DISPLAY,
        units_per_display=16
    ),

    # ===== CRACKERS =====

    # Sal de Mar
    "CRSM_U13510": OfficialProduct(
        sku="CRSM_U13510",
        category=ProductCategory.CRACKERS,
        product_name="CRACKERS KETO SAL DE MAR 135 GRS",
        base_code="CRSM",
        package_type=PackageType.DISPLAY,
        units_per_display=1
    ),
    "CRSM_U02510": OfficialProduct(
        sku="CRSM_U02510",
        category=ProductCategory.CRACKERS,
        product_name="SACHET CRACKERS KETO SAL DE MAR 25 GRS X1",
        base_code="CRSM",
        package_type=PackageType.SACHET,
        units_per_display=1
    ),
    "CRSM_U25010": OfficialProduct(
        sku="CRSM_U25010",
        category=ProductCategory.CRACKERS,
        product_name="CRACKERS KETO SAL DE MAR 25 GRS X7",
        base_code="CRSM",
        package_type=PackageType.DISPLAY,
        units_per_display=7
    ),
    "CRSM_U1000H": OfficialProduct(
        sku="CRSM_U1000H",
        category=ProductCategory.CRACKERS,
        product_name="CRACKERS KETO SAL DE MAR BANDEJA 1 KILO",
        base_code="CRSM",
        package_type=PackageType.BANDEJA,
        units_per_display=1
    ),

    # Pimienta
    "CRPM_U13510": OfficialProduct(
        sku="CRPM_U13510",
        category=ProductCategory.CRACKERS,
        product_name="CRACKERS KETO PIMIENTA 135 GRS",
        base_code="CRPM",
        package_type=PackageType.DISPLAY,
        units_per_display=1
    ),
    "CRPM_U02510": OfficialProduct(
        sku="CRPM_U02510",
        category=ProductCategory.CRACKERS,
        product_name="SACHET CRACKERS KETO PIMIENTA 25 GRS X1",
        base_code="CRPM",
        package_type=PackageType.SACHET,
        units_per_display=1
    ),
    "CRPM_U25010": OfficialProduct(
        sku="CRPM_U25010",
        category=ProductCategory.CRACKERS,
        product_name="CRACKERS KETO PIMIENTA 25 GRS X7",
        base_code="CRPM",
        package_type=PackageType.DISPLAY,
        units_per_display=7
    ),

    # Cúrcuma
    "CRCU_U13510": OfficialProduct(
        sku="CRCU_U13510",
        category=ProductCategory.CRACKERS,
        product_name="CRACKERS KETO CÚRCUMA 135 GRS",
        base_code="CRCU",
        package_type=PackageType.DISPLAY,
        units_per_display=1
    ),

    # Romero
    "CRRO_U13510": OfficialProduct(
        sku="CRRO_U13510",
        category=ProductCategory.CRACKERS,
        product_name="CRACKERS KETO ROMERO 135 GRS",
        base_code="CRRO",
        package_type=PackageType.DISPLAY,
        units_per_display=1
    ),
    "CRRO_U02510": OfficialProduct(
        sku="CRRO_U02510",
        category=ProductCategory.CRACKERS,
        product_name="SACHET CRACKERS KETO ROMERO 25 GRS X1",
        base_code="CRRO",
        package_type=PackageType.SACHET,
        units_per_display=1
    ),
    "CRRO_U25010": OfficialProduct(
        sku="CRRO_U25010",
        category=ProductCategory.CRACKERS,
        product_name="CRACKERS KETO ROMERO 25 GRS X7",
        base_code="CRRO",
        package_type=PackageType.DISPLAY,
        units_per_display=7
    ),

    # Ajo Albahaca
    "CRAA_U13510": OfficialProduct(
        sku="CRAA_U13510",
        category=ProductCategory.CRACKERS,
        product_name="CRACKERS KETO AJO ALBAHACA 135 GRS",
        base_code="CRAA",
        package_type=PackageType.DISPLAY,
        units_per_display=1
    ),

    # ===== KEEPERS =====

    # Keeper Maní
    "KSMC_U03010": OfficialProduct(
        sku="KSMC_U03010",
        category=ProductCategory.KEEPERS,
        product_name="KEEPER MANÍ 30 GRS X1",
        base_code="KSMC",
        package_type=PackageType.UNIDAD,
        units_per_display=1
    ),
    "KSMC_U15010": OfficialProduct(
        sku="KSMC_U15010",
        category=ProductCategory.KEEPERS,
        product_name="KEEPER MANÍ 30 GRS X5",
        base_code="KSMC",
        package_type=PackageType.DISPLAY,
        units_per_display=5
    ),
    "KSMC_U54010": OfficialProduct(
        sku="KSMC_U54010",
        category=ProductCategory.KEEPERS,
        product_name="KEEPER MANÍ 30 GRS X18",
        base_code="KSMC",
        package_type=PackageType.DISPLAY,
        units_per_display=18
    ),

    # Keeper Protein Maní
    "KPMC_U04010": OfficialProduct(
        sku="KPMC_U04010",
        category=ProductCategory.KEEPERS,
        product_name="KEEPER PROTEIN MANÍ 40 GRS X1",
        base_code="KPMC",
        package_type=PackageType.UNIDAD,
        units_per_display=1
    ),
    "KPMC_U16010": OfficialProduct(
        sku="KPMC_U16010",
        category=ProductCategory.KEEPERS,
        product_name="KEEPER PROTEIN MANÍ 40 GRS X4",
        base_code="KPMC",
        package_type=PackageType.DISPLAY,
        units_per_display=4
    ),
    "KPMC_U48010": OfficialProduct(
        sku="KPMC_U48010",
        category=ProductCategory.KEEPERS,
        product_name="KEEPER PROTEIN MANÍ 40 GRS X12",
        base_code="KPMC",
        package_type=PackageType.DISPLAY,
        units_per_display=12
    ),

    # ===== KRUMS =====

    # Granola Salada Mostaza
    "PKMM_U24010": OfficialProduct(
        sku="PKMM_U24010",
        category=ProductCategory.KRUMS,
        product_name="GRANOLA SALADA MOSTAZA 240",
        base_code="PKMM",
        package_type=PackageType.DISPLAY,
        units_per_display=1
    ),
    "PKMM_U04010": OfficialProduct(
        sku="PKMM_U04010",
        category=ProductCategory.KRUMS,
        product_name="GRANOLA SALADA MOSTAZA SACHET 40 X1",
        base_code="PKMM",
        package_type=PackageType.SACHET,
        units_per_display=1
    ),

    # Granola Salada Tahine
    "PKST_U24010": OfficialProduct(
        sku="PKST_U24010",
        category=ProductCategory.KRUMS,
        product_name="GRANOLA SALADA TAHINE 240",
        base_code="PKST",
        package_type=PackageType.DISPLAY,
        units_per_display=1
    ),
    "PKST_U04010": OfficialProduct(
        sku="PKST_U04010",
        category=ProductCategory.KRUMS,
        product_name="GRANOLA SALADA TAHINE SACHET 40 X1",
        base_code="PKST",
        package_type=PackageType.SACHET,
        units_per_display=1
    ),

    # Granola Salada Spicy
    "PKSP_U24010": OfficialProduct(
        sku="PKSP_U24010",
        category=ProductCategory.KRUMS,
        product_name="GRANOLA SALADA SPICY 240",
        base_code="PKSP",
        package_type=PackageType.DISPLAY,
        units_per_display=1
    ),
    "PKSP_U04010": OfficialProduct(
        sku="PKSP_U04010",
        category=ProductCategory.KRUMS,
        product_name="GRANOLA SALADA SPICY SACHET 40 X1",
        base_code="PKSP",
        package_type=PackageType.SACHET,
        units_per_display=1
    ),
}


# ================================================================================
# HELPER FUNCTIONS
# ================================================================================

def get_product_by_sku(sku: str) -> Optional[OfficialProduct]:
    """Get product from catalog by SKU"""
    return OFFICIAL_CATALOG.get(sku)


def get_products_by_category(category: ProductCategory) -> List[OfficialProduct]:
    """Get all products in a category"""
    return [p for p in OFFICIAL_CATALOG.values() if p.category == category]


def get_products_by_base_code(base_code: str) -> List[OfficialProduct]:
    """Get all variants of a product (same base code)"""
    return [p for p in OFFICIAL_CATALOG.values() if p.base_code == base_code]


def is_official_product(sku: str) -> bool:
    """Check if SKU is in official catalog"""
    return sku in OFFICIAL_CATALOG


def get_all_products() -> List[OfficialProduct]:
    """Get all products from catalog"""
    return list(OFFICIAL_CATALOG.values())


def get_catalog_stats() -> dict:
    """Get catalog statistics"""
    products = list(OFFICIAL_CATALOG.values())
    return {
        "total_products": len(products),
        "by_category": {
            cat.value: len([p for p in products if p.category == cat])
            for cat in ProductCategory
        },
        "unique_base_codes": len(set(p.base_code for p in products)),
    }

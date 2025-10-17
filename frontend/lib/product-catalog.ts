/**
 * CATÁLOGO OFICIAL DE PRODUCTOS GRANA
 *
 * Basado en: public/Archivos_Compartidos/CÓDIGOS GRANA.csv
 * Última actualización: Octubre 2025
 */

export interface CatalogProduct {
  sku: string;
  category: 'GRANOLAS' | 'BARRAS' | 'CRACKERS' | 'KEEPERS' | 'KRUMS';
  productName: string;
  baseCode: string; // BAKC, GRAL, etc.
  packageType: 'DISPLAY' | 'DOYPACK' | 'GRANEL' | 'SACHET' | 'UNIDAD' | 'BANDEJA' | 'BOLSA';
  unitsPerDisplay: number;
}

/**
 * Catálogo completo de productos oficiales
 * Estructura: SKU → Información del producto
 */
export const OFFICIAL_CATALOG: Record<string, CatalogProduct> = {
  // ===== GRANOLAS =====
  // Low Carb Almendras
  'GRAL_U26010': { sku: 'GRAL_U26010', category: 'GRANOLAS', productName: 'GRANOLA LOW CARB ALMENDRAS 260', baseCode: 'GRAL', packageType: 'DISPLAY', unitsPerDisplay: 1 },
  'GRAL_U1000H': { sku: 'GRAL_U1000H', category: 'GRANOLAS', productName: 'GRANOLA LOW CARB ALMENDRAS 1 KILO', baseCode: 'GRAL', packageType: 'BOLSA', unitsPerDisplay: 1 },

  // Low Carb Cacao
  'GRCA_U26010': { sku: 'GRCA_U26010', category: 'GRANOLAS', productName: 'GRANOLA LOW CARB CACAO 260', baseCode: 'GRCA', packageType: 'DOYPACK', unitsPerDisplay: 1 },
  'GRCA_U1000H': { sku: 'GRCA_U1000H', category: 'GRANOLAS', productName: 'GRANOLA LOW CARB CACAO 1 KILO', baseCode: 'GRCA', packageType: 'BOLSA', unitsPerDisplay: 1 },

  // Low Carb Berries
  'GRBE_U26010': { sku: 'GRBE_U26010', category: 'GRANOLAS', productName: 'GRANOLA LOW CARB BERRIES 260', baseCode: 'GRBE', packageType: 'DISPLAY', unitsPerDisplay: 1 },
  'GRBE_U1000H': { sku: 'GRBE_U1000H', category: 'GRANOLAS', productName: 'GRANOLA LOW CARB BERRIES 1 KILO', baseCode: 'GRBE', packageType: 'BOLSA', unitsPerDisplay: 1 },

  // Keto Nuez
  'GRKC_U21010': { sku: 'GRKC_U21010', category: 'GRANOLAS', productName: 'GRANOLA KETO NUEZ 210', baseCode: 'GRKC', packageType: 'DOYPACK', unitsPerDisplay: 1 },
  'GRKC_U1000H': { sku: 'GRKC_U1000H', category: 'GRANOLAS', productName: 'GRANOLA KETO NUEZ 1 KILO', baseCode: 'GRKC', packageType: 'BOLSA', unitsPerDisplay: 1 },

  // Protein Almendras
  'GPAA_U24010': { sku: 'GPAA_U24010', category: 'GRANOLAS', productName: 'GRANOLA PROTEIN ALMENDRAS 240', baseCode: 'GPAA', packageType: 'DISPLAY', unitsPerDisplay: 1 },
  'GPAA_U04010': { sku: 'GPAA_U04010', category: 'GRANOLAS', productName: 'GRANOLA PROTEIN ALMENDRAS SACHET 40 X1', baseCode: 'GPAA', packageType: 'SACHET', unitsPerDisplay: 1 },

  // Protein Cacao
  'GPCC_U24010': { sku: 'GPCC_U24010', category: 'GRANOLAS', productName: 'GRANOLA PROTEIN CACAO 240', baseCode: 'GPCC', packageType: 'DISPLAY', unitsPerDisplay: 1 },
  'GPCC_U04010': { sku: 'GPCC_U04010', category: 'GRANOLAS', productName: 'GRANOLA PROTEIN CACAO SACHET 40 X1', baseCode: 'GPCC', packageType: 'SACHET', unitsPerDisplay: 1 },

  // Protein Berries
  'GPBB_U24010': { sku: 'GPBB_U24010', category: 'GRANOLAS', productName: 'GRANOLA PROTEIN BERRIES 240', baseCode: 'GPBB', packageType: 'DISPLAY', unitsPerDisplay: 1 },
  'GPBB_U04010': { sku: 'GPBB_U04010', category: 'GRANOLAS', productName: 'GRANOLA PROTEIN BERRIES SACHET 40 X1', baseCode: 'GPBB', packageType: 'SACHET', unitsPerDisplay: 1 },

  // ===== BARRAS =====
  // Low Carb Cacao Maní
  'BACM_U04010': { sku: 'BACM_U04010', category: 'BARRAS', productName: 'BARRA LOW CARB CACAO MANÍ X1', baseCode: 'BACM', packageType: 'GRANEL', unitsPerDisplay: 1 },
  'BACM_U20010': { sku: 'BACM_U20010', category: 'BARRAS', productName: 'BARRA LOW CARB CACAO MANÍ X5', baseCode: 'BACM', packageType: 'DISPLAY', unitsPerDisplay: 5 },
  'BACM_U64010': { sku: 'BACM_U64010', category: 'BARRAS', productName: 'BARRA LOW CARB CACAO MANÍ X16', baseCode: 'BACM', packageType: 'DISPLAY', unitsPerDisplay: 16 },

  // Low Carb Manzana Canela
  'BAMC_U04010': { sku: 'BAMC_U04010', category: 'BARRAS', productName: 'BARRA LOW CARB MANZANA CANELA X1', baseCode: 'BAMC', packageType: 'GRANEL', unitsPerDisplay: 1 },
  'BAMC_U20010': { sku: 'BAMC_U20010', category: 'BARRAS', productName: 'BARRA LOW CARB MANZANA CANELA X5', baseCode: 'BAMC', packageType: 'DISPLAY', unitsPerDisplay: 5 },
  'BAMC_U64010': { sku: 'BAMC_U64010', category: 'BARRAS', productName: 'BARRA LOW CARB MANZANA CANELA X16', baseCode: 'BAMC', packageType: 'DISPLAY', unitsPerDisplay: 16 },

  // Low Carb Berries
  'BABE_U04010': { sku: 'BABE_U04010', category: 'BARRAS', productName: 'BARRA LOW CARB BERRIES X1', baseCode: 'BABE', packageType: 'GRANEL', unitsPerDisplay: 1 },
  'BABE_U20010': { sku: 'BABE_U20010', category: 'BARRAS', productName: 'BARRA LOW CARB BERRIES X5', baseCode: 'BABE', packageType: 'DISPLAY', unitsPerDisplay: 5 },
  'BABE_U64010': { sku: 'BABE_U64010', category: 'BARRAS', productName: 'BARRA LOW CARB BERRIES X16', baseCode: 'BABE', packageType: 'DISPLAY', unitsPerDisplay: 16 },

  // Keto Nuez
  'BAKC_U04010': { sku: 'BAKC_U04010', category: 'BARRAS', productName: 'BARRA KETO NUEZ X1', baseCode: 'BAKC', packageType: 'GRANEL', unitsPerDisplay: 1 },
  'BAKC_U20010': { sku: 'BAKC_U20010', category: 'BARRAS', productName: 'BARRA KETO NUEZ X5', baseCode: 'BAKC', packageType: 'DISPLAY', unitsPerDisplay: 5 },
  'BAKC_U64010': { sku: 'BAKC_U64010', category: 'BARRAS', productName: 'BARRA KETO NUEZ X16', baseCode: 'BAKC', packageType: 'DISPLAY', unitsPerDisplay: 16 },

  // Keto Almendra
  'BAKA_U04010': { sku: 'BAKA_U04010', category: 'BARRAS', productName: 'BARRA KETO ALMENDRA X1', baseCode: 'BAKA', packageType: 'GRANEL', unitsPerDisplay: 1 },
  'BAKA_U20010': { sku: 'BAKA_U20010', category: 'BARRAS', productName: 'BARRA KETO ALMENDRA X5', baseCode: 'BAKA', packageType: 'DISPLAY', unitsPerDisplay: 5 },
  'BAKA_U64010': { sku: 'BAKA_U64010', category: 'BARRAS', productName: 'BARRA KETO ALMENDRA X16', baseCode: 'BAKA', packageType: 'DISPLAY', unitsPerDisplay: 16 },

  // ===== CRACKERS =====
  // Sal de Mar
  'CRSM_U13510': { sku: 'CRSM_U13510', category: 'CRACKERS', productName: 'CRACKERS KETO SAL DE MAR 135 GRS', baseCode: 'CRSM', packageType: 'DISPLAY', unitsPerDisplay: 1 },
  'CRSM_U02510': { sku: 'CRSM_U02510', category: 'CRACKERS', productName: 'SACHET CRACKERS KETO SAL DE MAR 25 GRS X1', baseCode: 'CRSM', packageType: 'SACHET', unitsPerDisplay: 1 },
  'CRSM_U25010': { sku: 'CRSM_U25010', category: 'CRACKERS', productName: 'CRACKERS KETO SAL DE MAR 25 GRS X7', baseCode: 'CRSM', packageType: 'DISPLAY', unitsPerDisplay: 7 },
  'CRSM_U1000H': { sku: 'CRSM_U1000H', category: 'CRACKERS', productName: 'CRACKERS KETO SAL DE MAR BANDEJA 1 KILO', baseCode: 'CRSM', packageType: 'BANDEJA', unitsPerDisplay: 1 },

  // Pimienta
  'CRPM_U13510': { sku: 'CRPM_U13510', category: 'CRACKERS', productName: 'CRACKERS KETO PIMIENTA 135 GRS', baseCode: 'CRPM', packageType: 'DISPLAY', unitsPerDisplay: 1 },
  'CRPM_U02510': { sku: 'CRPM_U02510', category: 'CRACKERS', productName: 'SACHET CRACKERS KETO PIMIENTA 25 GRS X1', baseCode: 'CRPM', packageType: 'SACHET', unitsPerDisplay: 1 },
  'CRPM_U25010': { sku: 'CRPM_U25010', category: 'CRACKERS', productName: 'CRACKERS KETO PIMIENTA 25 GRS X7', baseCode: 'CRPM', packageType: 'DISPLAY', unitsPerDisplay: 7 },

  // Cúrcuma
  'CRCU_U13510': { sku: 'CRCU_U13510', category: 'CRACKERS', productName: 'CRACKERS KETO CÚRCUMA 135 GRS', baseCode: 'CRCU', packageType: 'DISPLAY', unitsPerDisplay: 1 },

  // Romero
  'CRRO_U13510': { sku: 'CRRO_U13510', category: 'CRACKERS', productName: 'CRACKERS KETO ROMERO 135 GRS', baseCode: 'CRRO', packageType: 'DISPLAY', unitsPerDisplay: 1 },
  'CRRO_U02510': { sku: 'CRRO_U02510', category: 'CRACKERS', productName: 'SACHET CRACKERS KETO ROMERO 25 GRS X1', baseCode: 'CRRO', packageType: 'SACHET', unitsPerDisplay: 1 },
  'CRRO_U25010': { sku: 'CRRO_U25010', category: 'CRACKERS', productName: 'CRACKERS KETO ROMERO 25 GRS X7', baseCode: 'CRRO', packageType: 'DISPLAY', unitsPerDisplay: 7 },

  // Ajo Albahaca
  'CRAA_U13510': { sku: 'CRAA_U13510', category: 'CRACKERS', productName: 'CRACKERS KETO AJO ALBAHACA 135 GRS', baseCode: 'CRAA', packageType: 'DISPLAY', unitsPerDisplay: 1 },

  // ===== KEEPERS =====
  // Keeper Maní
  'KSMC_U03010': { sku: 'KSMC_U03010', category: 'KEEPERS', productName: 'KEEPER MANÍ 30 GRS X1', baseCode: 'KSMC', packageType: 'UNIDAD', unitsPerDisplay: 1 },
  'KSMC_U15010': { sku: 'KSMC_U15010', category: 'KEEPERS', productName: 'KEEPER MANÍ 30 GRS X5', baseCode: 'KSMC', packageType: 'DISPLAY', unitsPerDisplay: 5 },
  'KSMC_U54010': { sku: 'KSMC_U54010', category: 'KEEPERS', productName: 'KEEPER MANÍ 30 GRS X18', baseCode: 'KSMC', packageType: 'DISPLAY', unitsPerDisplay: 18 },

  // Keeper Protein Maní
  'KPMC_U04010': { sku: 'KPMC_U04010', category: 'KEEPERS', productName: 'KEEPER PROTEIN MANÍ 40 GRS X1', baseCode: 'KPMC', packageType: 'UNIDAD', unitsPerDisplay: 1 },
  'KPMC_U16010': { sku: 'KPMC_U16010', category: 'KEEPERS', productName: 'KEEPER PROTEIN MANÍ 40 GRS X4', baseCode: 'KPMC', packageType: 'DISPLAY', unitsPerDisplay: 4 },
  'KPMC_U48010': { sku: 'KPMC_U48010', category: 'KEEPERS', productName: 'KEEPER PROTEIN MANÍ 40 GRS X12', baseCode: 'KPMC', packageType: 'DISPLAY', unitsPerDisplay: 12 },

  // ===== KRUMS =====
  // Granola Salada Mostaza
  'PKMM_U24010': { sku: 'PKMM_U24010', category: 'KRUMS', productName: 'GRANOLA SALADA MOSTAZA 240', baseCode: 'PKMM', packageType: 'DISPLAY', unitsPerDisplay: 1 },
  'PKMM_U04010': { sku: 'PKMM_U04010', category: 'KRUMS', productName: 'GRANOLA SALADA MOSTAZA SACHET 40 X1', baseCode: 'PKMM', packageType: 'SACHET', unitsPerDisplay: 1 },

  // Granola Salada Tahine
  'PKST_U24010': { sku: 'PKST_U24010', category: 'KRUMS', productName: 'GRANOLA SALADA TAHINE 240', baseCode: 'PKST', packageType: 'DISPLAY', unitsPerDisplay: 1 },
  'PKST_U04010': { sku: 'PKST_U04010', category: 'KRUMS', productName: 'GRANOLA SALADA TAHINE SACHET 40 X1', baseCode: 'PKST', packageType: 'SACHET', unitsPerDisplay: 1 },

  // Granola Salada Spicy
  'PKSP_U24010': { sku: 'PKSP_U24010', category: 'KRUMS', productName: 'GRANOLA SALADA SPICY 240', baseCode: 'PKSP', packageType: 'DISPLAY', unitsPerDisplay: 1 },
  'PKSP_U04010': { sku: 'PKSP_U04010', category: 'KRUMS', productName: 'GRANOLA SALADA SPICY SACHET 40 X1', baseCode: 'PKSP', packageType: 'SACHET', unitsPerDisplay: 1 },
};

/**
 * Obtiene la categoría oficial del catálogo para un SKU
 */
export function getOfficialCategory(sku: string): string | null {
  const catalogProduct = OFFICIAL_CATALOG[sku];
  return catalogProduct ? catalogProduct.category : null;
}

/**
 * Obtiene el código base (BAKC, GRAL, etc.) para un SKU
 */
export function getBaseCode(sku: string): string | null {
  const catalogProduct = OFFICIAL_CATALOG[sku];
  return catalogProduct ? catalogProduct.baseCode : null;
}

/**
 * Obtiene las unidades por display para un SKU
 */
export function getUnitsPerDisplay(sku: string): number {
  const catalogProduct = OFFICIAL_CATALOG[sku];
  return catalogProduct ? catalogProduct.unitsPerDisplay : 1;
}

/**
 * Verifica si un SKU está en el catálogo oficial
 */
export function isOfficialProduct(sku: string): boolean {
  return sku in OFFICIAL_CATALOG;
}

/**
 * Obtiene todos los productos de una categoría
 */
export function getProductsByCategory(category: string): CatalogProduct[] {
  return Object.values(OFFICIAL_CATALOG).filter(p => p.category === category);
}

/**
 * Obtiene todas las variantes de un producto base
 */
export function getProductVariants(baseCode: string): CatalogProduct[] {
  return Object.values(OFFICIAL_CATALOG).filter(p => p.baseCode === baseCode);
}

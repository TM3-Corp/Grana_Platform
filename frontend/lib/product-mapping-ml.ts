/**
 * MAPEO DE PRODUCTOS MERCADOLIBRE → CATÁLOGO OFICIAL
 *
 * Este archivo mapea productos de MercadoLibre y otros canales
 * a sus equivalentes en el catálogo oficial de Grana
 */

import { OFFICIAL_CATALOG } from './product-catalog';

/**
 * Mapeo manual de productos MercadoLibre a SKUs del catálogo oficial
 *
 * Estructura: SKU_ML → SKU_Catálogo_Oficial
 */
export const ML_TO_CATALOG_MAPPING: Record<string, string> = {
  // Barras Low Carb Cacao Maní
  'ML-MLC1630349929': 'BACM_U64010', // Barra Low Carb Cacao Maní - probablemente 16un
  'ML-MLC2978631042': 'BACM_U20010', // Display 5 Uds
  'ML-MLC1630414337': 'BACM_U20010', // Display 5 Uds (duplicado)

  // Barras Keto Nuez
  'ML-MLC2929973548': 'BAKC_U64010', // 16 Un
  'ML-MLC2930199094': 'BAKC_U20010', // Display 5 Uds

  // Barras Manzana Canela
  'ML-MLC1630337053': 'BAMC_U64010', // 16 Un
  'ML-MLC2938290826': 'BAMC_U20010', // Display 5 Uds
  'ML-MLC1630416135': 'BAMC_U20010', // Display 5 Uds (duplicado)

  // Crackers Sal de Mar
  'ML-MLC2930215860': 'CRSM_U13510', // 135 GRS (mencionan 120g pero es el de 135g)

  // Crackers Romero
  'ML-MLC2930238714': 'CRRO_U13510', // 135 GRS
  'ML-MLC2933751572': 'CRRO_U13510', // 135 GRS (duplicado)

  // Crackers Ajo Albahaca
  'ML-MLC2930200766': 'CRAA_U13510', // 135 GRS

  // Crackers Pimienta
  'ML-MLC1630369169': 'CRPM_U13510', // 135 GRS

  // Granola Low Carb Almendras
  'ML-MLC2967399930': 'GRAL_U26010', // 260g
  'ML-MLC3029455396': 'GRAL_U26010', // 260g (duplicado)

  // Granola Low Carb Berries
  'ML-MLC2978641268': 'GRBE_U26010', // 260g
  'ML-MLC2966323128': 'GRBE_U26010', // 260g (duplicado)
};

/**
 * Obtiene el SKU del catálogo oficial para un producto de cualquier canal
 *
 * @param sku - SKU del producto (puede ser de Shopify, ML, etc.)
 * @returns SKU del catálogo oficial, o el mismo SKU si ya es oficial
 */
export function getOfficialSKU(sku: string): string {
  // Si el SKU está en el catálogo oficial, retornarlo
  if (sku in OFFICIAL_CATALOG) {
    return sku;
  }

  // Si es de MercadoLibre, buscar mapeo
  if (sku in ML_TO_CATALOG_MAPPING) {
    return ML_TO_CATALOG_MAPPING[sku];
  }

  // Si no se encuentra mapeo, retornar el SKU original
  return sku;
}

/**
 * Mapeo inteligente basado en nombres de productos
 * Para productos sin mapeo manual
 */
export function inferOfficialSKUFromName(productName: string): string | null {
  const name = productName.toLowerCase();

  // Barras Keto Nuez
  if (name.includes('barra') && name.includes('keto') && (name.includes('nuez') || name.includes('chocolate'))) {
    if (name.includes('16') || name.includes('display')) return 'BAKC_U64010';
    if (name.includes('5')) return 'BAKC_U20010';
    if (name.includes('1') || name.includes('granel')) return 'BAKC_U04010';
  }

  // Barras Low Carb Cacao Maní
  if (name.includes('barra') && name.includes('low carb') && (name.includes('cacao') || name.includes('maní'))) {
    if (name.includes('16')) return 'BACM_U64010';
    if (name.includes('5')) return 'BACM_U20010';
    if (name.includes('1') || name.includes('granel')) return 'BACM_U04010';
  }

  // Barras Low Carb Manzana Canela
  if (name.includes('barra') && name.includes('low carb') && name.includes('manzana')) {
    if (name.includes('16')) return 'BAMC_U64010';
    if (name.includes('5')) return 'BAMC_U20010';
    if (name.includes('1') || name.includes('granel')) return 'BAMC_U04010';
  }

  // Barras Low Carb Berries
  if (name.includes('barra') && name.includes('low carb') && name.includes('berries')) {
    if (name.includes('16')) return 'BABE_U64010';
    if (name.includes('5')) return 'BABE_U20010';
    if (name.includes('1') || name.includes('granel')) return 'BABE_U04010';
  }

  // Crackers Sal de Mar
  if (name.includes('cracker') && name.includes('sal de mar')) {
    if (name.includes('kilo')) return 'CRSM_U1000H';
    if (name.includes('135') || name.includes('120')) return 'CRSM_U13510';
    if (name.includes('25') && (name.includes('7') || name.includes('display'))) return 'CRSM_U25010';
    if (name.includes('25') && name.includes('sachet')) return 'CRSM_U02510';
  }

  // Crackers Romero
  if (name.includes('cracker') && name.includes('romero')) {
    if (name.includes('135')) return 'CRRO_U13510';
    if (name.includes('25') && (name.includes('7') || name.includes('display'))) return 'CRRO_U25010';
    if (name.includes('25') && name.includes('sachet')) return 'CRRO_U02510';
  }

  // Crackers Pimienta
  if (name.includes('cracker') && name.includes('pimienta')) {
    if (name.includes('135')) return 'CRPM_U13510';
    if (name.includes('25') && (name.includes('7') || name.includes('display'))) return 'CRPM_U25010';
    if (name.includes('25') && name.includes('sachet')) return 'CRPM_U02510';
  }

  // Crackers Ajo Albahaca
  if (name.includes('cracker') && name.includes('ajo')) {
    return 'CRAA_U13510';
  }

  // Crackers Cúrcuma
  if (name.includes('cracker') && name.includes('cúrcuma')) {
    return 'CRCU_U13510';
  }

  // Granola Low Carb Almendras
  if (name.includes('granola') && name.includes('low carb') && name.includes('almendra')) {
    if (name.includes('kilo')) return 'GRAL_U1000H';
    if (name.includes('260')) return 'GRAL_U26010';
  }

  // Granola Low Carb Cacao
  if (name.includes('granola') && name.includes('low carb') && name.includes('cacao')) {
    if (name.includes('kilo')) return 'GRCA_U1000H';
    if (name.includes('260')) return 'GRCA_U26010';
  }

  // Granola Low Carb Berries
  if (name.includes('granola') && name.includes('low carb') && name.includes('berries')) {
    if (name.includes('kilo')) return 'GRBE_U1000H';
    if (name.includes('260')) return 'GRBE_U26010';
  }

  // Granola Keto Nuez
  if (name.includes('granola') && name.includes('keto') && name.includes('nuez')) {
    if (name.includes('kilo')) return 'GRKC_U1000H';
    if (name.includes('210')) return 'GRKC_U21010';
  }

  // Keeper Maní
  if (name.includes('keeper') && !name.includes('protein') && name.includes('maní')) {
    if (name.includes('18')) return 'KSMC_U54010';
    if (name.includes('5')) return 'KSMC_U15010';
    if (name.includes('30')) return 'KSMC_U03010';
  }

  // Keeper Protein Maní
  if (name.includes('keeper') && name.includes('protein') && name.includes('maní')) {
    if (name.includes('12')) return 'KPMC_U48010';
    if (name.includes('4')) return 'KPMC_U16010';
    if (name.includes('40')) return 'KPMC_U04010';
  }

  return null;
}

/**
 * Obtiene el SKU oficial usando múltiples estrategias
 */
export function resolveOfficialSKU(sku: string, productName: string): string {
  // 1. Verificar si ya está en el catálogo oficial
  if (sku in OFFICIAL_CATALOG) {
    return sku;
  }

  // 2. Verificar mapeo manual de ML
  if (sku in ML_TO_CATALOG_MAPPING) {
    return ML_TO_CATALOG_MAPPING[sku];
  }

  // 3. Inferir desde el nombre del producto
  const inferredSKU = inferOfficialSKUFromName(productName);
  if (inferredSKU) {
    return inferredSKU;
  }

  // 4. Si no se pudo resolver, retornar el SKU original
  return sku;
}

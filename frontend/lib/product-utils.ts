/**
 * Product utility functions for filtering, validating, and mapping products
 * Uses official catalog from CÓDIGOS GRANA.csv
 */

import { OFFICIAL_CATALOG, getOfficialCategory, getBaseCode, getUnitsPerDisplay, isOfficialProduct } from './product-catalog';
import { resolveOfficialSKU } from './product-mapping-ml';

export interface Product {
  id: number;
  sku: string;
  name: string;
  category: string | null;
  brand: string | null;
  source: string;
  sale_price: number | null;
  current_stock: number | null;
  min_stock: number | null;
  is_active: boolean;
}

/**
 * Filter out obsolete MercadoLibre products
 *
 * Problem: Some ML products exist in two versions:
 * - "MLCxxxxxx" (obsolete): No price, negative stock, should be excluded
 * - "ML-MLCxxxxxx" (current): Has price, positive stock, should be used
 *
 * This function filters out the obsolete versions.
 */
export function filterValidProducts(products: Product[]): Product[] {
  return products.filter(product => {
    // Exclude obsolete ML products (those starting with "MLC" but NOT "ML-MLC")
    if (product.sku.startsWith('MLC') && !product.sku.startsWith('ML-MLC')) {
      return false;
    }
    return true;
  });
}

/**
 * Get the base name of a product by removing packaging suffixes
 */
export function getBaseName(name: string): string {
  let baseName = name;
  const suffixes = [
    ' - 1 unidad',
    ' - 1 barrita',
    ' - Display con 5 unidades',
    ' - Display con 16 unidades',
    ' - Display con 5 barras',
    ' - Display 18 unidades',
    ' - Display 10 sachets',
    ' - Sachet individual 25 grs',
    ' - Display 135 grs',
    ' 5 Un',
    ' 16 Un',
    ' Display 5 Un',
    ' Display 16 Un',
    ' Individual 25 gr',
  ];

  for (const suffix of suffixes) {
    baseName = baseName.replace(suffix, '');
  }

  return baseName.trim();
}

/**
 * Normalize product names across channels for better matching
 *
 * Examples:
 * - "Barras Keto Chocolate Nuez Grana Vegana 35 Gr - 16 Un" (ML)
 * - "Barra Keto Nuez - Display con 16 unidades" (Shopify)
 *
 * Both should map to "Barra Keto Nuez"
 */
export function normalizeProductName(name: string): string {
  let normalized = name.toLowerCase();

  // Remove common words
  normalized = normalized
    .replace(/grana/gi, '')
    .replace(/vegana/gi, '')
    .replace(/\d+\s*gr(s)?/gi, '')
    .replace(/\d+\s*g\b/gi, '')
    .replace(/chocolate/gi, '')
    .replace(/sabor/gi, '')
    .replace(/galletas/gi, '')
    .replace(/barritas/gi, 'barra')
    .replace(/barras/gi, 'barra');

  // Remove packaging info
  normalized = getBaseName(normalized);

  // Clean up extra spaces
  normalized = normalized.replace(/\s+/g, ' ').trim();

  return normalized;
}

/**
 * Get the format from a product name
 */
export function getFormat(name: string): string {
  if (name.includes('16 Un') || name.includes('Display con 16') || name.includes('Display 16')) {
    return '16un';
  }
  if (name.includes('5 Un') || name.includes('Display con 5') || name.includes('Display 5')) {
    return '5un';
  }
  if (name.includes('1 unidad') || name.includes('1 barrita')) {
    return '1un';
  }
  if (name.includes('210') || name.includes('210g')) {
    return '210g';
  }
  if (name.includes('260') || name.includes('260g')) {
    return '260g';
  }
  if (name.includes('135') || name.includes('135g')) {
    return '135g';
  }
  return '1un'; // default
}

/**
 * Group products by their normalized base name (consolidating cross-channel)
 */
export function groupProductsByBase(products: Product[]): Map<string, Product[]> {
  const groups = new Map<string, Product[]>();

  products.forEach(product => {
    const baseName = normalizeProductName(product.name);

    if (!groups.has(baseName)) {
      groups.set(baseName, []);
    }

    groups.get(baseName)!.push(product);
  });

  return groups;
}

/**
 * Obtiene el SKU oficial del catálogo para un producto
 * Mapea automáticamente productos de ML y otros canales
 */
export function getProductOfficialSKU(product: Product): string {
  return resolveOfficialSKU(product.sku, product.name);
}

/**
 * Obtiene la categoría oficial del catálogo para un producto
 */
export function getProductOfficialCategory(product: Product): string {
  const officialSKU = getProductOfficialSKU(product);
  const officialCategory = getOfficialCategory(officialSKU);

  // Si se encuentra en el catálogo, usar esa categoría
  if (officialCategory) {
    return officialCategory;
  }

  // Fallback: categoría del producto o inferir del nombre
  if (product.category) {
    // Normalizar categoría
    const cat = product.category.toLowerCase();
    if (cat.includes('barra')) return 'BARRAS';
    if (cat.includes('cracker') || cat.includes('galleta')) return 'CRACKERS';
    if (cat.includes('granola')) return 'GRANOLAS';
    if (cat.includes('keeper')) return 'KEEPERS';
  }

  // Fallback final: inferir del nombre
  const name = product.name.toLowerCase();
  if (name.includes('barra')) return 'BARRAS';
  if (name.includes('cracker') || name.includes('galleta')) return 'CRACKERS';
  if (name.includes('granola')) return 'GRANOLAS';
  if (name.includes('keeper')) return 'KEEPERS';

  return 'OTROS';
}

/**
 * Obtiene el código base del producto (BAKC, GRAL, etc.)
 */
export function getProductBaseCode(product: Product): string {
  const officialSKU = getProductOfficialSKU(product);
  const baseCode = getBaseCode(officialSKU);

  if (baseCode) {
    return baseCode;
  }

  // Fallback: extraer primeras 4 letras del SKU si es formato oficial
  if (officialSKU.includes('_')) {
    return officialSKU.split('_')[0];
  }

  return officialSKU;
}

/**
 * Obtiene las unidades por display del producto
 */
export function getProductUnitsPerDisplay(product: Product): number {
  const officialSKU = getProductOfficialSKU(product);
  return getUnitsPerDisplay(officialSKU);
}

/**
 * Verifica si un producto pertenece al catálogo oficial
 */
export function isProductOfficial(product: Product): boolean {
  const officialSKU = getProductOfficialSKU(product);
  return isOfficialProduct(officialSKU);
}

/**
 * Agrupa productos por su código base (usando catálogo oficial)
 * Esto consolida productos de diferentes canales que son el mismo producto base
 */
export function groupProductsByBaseCode(products: Product[]): Map<string, Product[]> {
  const groups = new Map<string, Product[]>();

  products.forEach(product => {
    const baseCode = getProductBaseCode(product);

    if (!groups.has(baseCode)) {
      groups.set(baseCode, []);
    }

    groups.get(baseCode)!.push(product);
  });

  return groups;
}

/**
 * Obtiene el nombre del producto base desde el catálogo oficial
 */
export function getProductBaseName(product: Product): string {
  const officialSKU = getProductOfficialSKU(product);

  if (officialSKU in OFFICIAL_CATALOG) {
    return OFFICIAL_CATALOG[officialSKU].productName;
  }

  // Fallback: normalizar nombre del producto
  return normalizeProductName(product.name);
}

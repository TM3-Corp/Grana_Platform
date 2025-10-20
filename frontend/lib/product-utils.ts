/**
 * Product utility functions for filtering, validating, and mapping products
 * Refactored to work with API-fetched catalog data instead of hardcoded data
 *
 * Author: TM3
 * Date: 2025-10-17
 */

import { OfficialProduct } from './catalog-api';

export interface Product {
  id: number;
  sku: string;
  name: string;
  category: string | null;
  brand: string | null;
  source: string | null;  // Made optional to match backend
  sale_price: number | null;
  current_stock: number | null;
  min_stock: number | null;
  is_active: boolean;
}

// ============================================
// Product Filtering
// ============================================

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

// ============================================
// Name Normalization
// ============================================

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

// ============================================
// Product Grouping
// ============================================

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

// ============================================
// Catalog Integration (with API-fetched data)
// ============================================

/**
 * Resolve ML SKU to official Shopify SKU using channel equivalents data
 *
 * @param sku - ML SKU (e.g., 'ML-MLC1630349929')
 * @param channelEquivalents - Fetched from /api/v1/product-mapping/channel-equivalents
 * @returns Official Shopify SKU or original SKU if no mapping found
 */
export function resolveOfficialSKU(
  sku: string,
  channelEquivalents: Array<{
    mercadolibre_sku: string;
    shopify_sku: string;
  }>
): string {
  if (!sku.startsWith('ML-')) {
    return sku; // Already a Shopify SKU
  }

  const mapping = channelEquivalents.find(eq => eq.mercadolibre_sku === sku);
  return mapping ? mapping.shopify_sku : sku;
}

/**
 * Get official SKU for a product (resolves ML SKUs)
 *
 * @param product - Product object
 * @param channelEquivalents - Fetched from API
 * @returns Official SKU
 */
export function getProductOfficialSKU(
  product: Product,
  channelEquivalents: Array<{
    mercadolibre_sku: string;
    shopify_sku: string;
  }>
): string {
  return resolveOfficialSKU(product.sku, channelEquivalents);
}

/**
 * Get official category for a product from catalog
 *
 * @param product - Product object
 * @param catalog - Optional official catalog fetched from API
 * @param channelEquivalents - Optional channel equivalents fetched from API
 * @returns Official category or inferred category
 */
export function getProductOfficialCategory(
  product: Product,
  catalog?: OfficialProduct[],
  channelEquivalents?: Array<{
    mercadolibre_sku: string;
    shopify_sku: string;
  }>
): string {
  // Only use catalog if both catalog and channelEquivalents are provided
  if (catalog && channelEquivalents) {
    const officialSKU = getProductOfficialSKU(product, channelEquivalents);
    const catalogProduct = catalog.find(p => p.sku === officialSKU);

    // If found in catalog, use that category
    if (catalogProduct) {
      return catalogProduct.category;
    }
  }

  // Fallback: use product's category
  if (product.category) {
    const cat = product.category.toLowerCase();
    if (cat.includes('barra')) return 'BARRAS';
    if (cat.includes('cracker') || cat.includes('galleta')) return 'CRACKERS';
    if (cat.includes('granola')) return 'GRANOLAS';
    if (cat.includes('keeper')) return 'KEEPERS';
  }

  // Final fallback: infer from name
  const name = product.name.toLowerCase();
  if (name.includes('barra')) return 'BARRAS';
  if (name.includes('cracker') || name.includes('galleta')) return 'CRACKERS';
  if (name.includes('granola')) return 'GRANOLAS';
  if (name.includes('keeper')) return 'KEEPERS';

  return 'OTROS';
}

/**
 * Get base code from catalog (BAKC, GRAL, etc.)
 *
 * @param product - Product object
 * @param catalog - Optional official catalog
 * @param channelEquivalents - Optional channel equivalents
 * @returns Base code or extracted from SKU
 */
export function getProductBaseCode(
  product: Product,
  catalog?: OfficialProduct[],
  channelEquivalents?: Array<{
    mercadolibre_sku: string;
    shopify_sku: string;
  }>
): string {
  // Only use catalog if both parameters are provided
  if (catalog && channelEquivalents) {
    const officialSKU = getProductOfficialSKU(product, channelEquivalents);
    const catalogProduct = catalog.find(p => p.sku === officialSKU);

    if (catalogProduct) {
      return catalogProduct.base_code;
    }
  }

  // Fallback: extract from SKU
  const sku = product.sku;

  // Extract first 4 letters from SKU if it's in official format
  if (sku.includes('_')) {
    return sku.split('_')[0];
  }

  return sku;
}

/**
 * Get units per display from catalog
 *
 * @param product - Product object
 * @param catalog - Optional official catalog
 * @param channelEquivalents - Optional channel equivalents
 * @returns Units per display
 */
export function getProductUnitsPerDisplay(
  product: Product,
  catalog?: OfficialProduct[],
  channelEquivalents?: Array<{
    mercadolibre_sku: string;
    shopify_sku: string;
  }>
): number {
  // Only use catalog if both parameters are provided
  if (catalog && channelEquivalents) {
    const officialSKU = getProductOfficialSKU(product, channelEquivalents);
    const catalogProduct = catalog.find(p => p.sku === officialSKU);

    if (catalogProduct) {
      return catalogProduct.units_per_display;
    }
  }

  // Fallback: infer from product name
  const name = product.name;
  if (name.includes('16 Un') || name.includes('Display con 16') || name.includes('Display 16')) {
    return 16;
  }
  if (name.includes('18 unidades') || name.includes('Display 18')) {
    return 18;
  }
  if (name.includes('10 sachets') || name.includes('Display 10')) {
    return 10;
  }
  if (name.includes('5 Un') || name.includes('Display con 5') || name.includes('Display 5')) {
    return 5;
  }

  return 1; // Default: single unit
}

/**
 * Check if product is in official catalog
 *
 * @param product - Product object
 * @param catalog - Optional official catalog
 * @param channelEquivalents - Optional channel equivalents
 * @returns true if product is official
 */
export function isProductOfficial(
  product: Product,
  catalog?: OfficialProduct[],
  channelEquivalents?: Array<{
    mercadolibre_sku: string;
    shopify_sku: string;
  }>
): boolean {
  if (!catalog || !channelEquivalents) {
    return false; // Cannot determine without catalog
  }

  const officialSKU = getProductOfficialSKU(product, channelEquivalents);
  return catalog.some(p => p.sku === officialSKU);
}

/**
 * Get product base name from catalog
 *
 * @param product - Product object
 * @param catalog - Optional official catalog
 * @param channelEquivalents - Optional channel equivalents
 * @returns Base product name or normalized name
 */
export function getProductBaseName(
  product: Product,
  catalog?: OfficialProduct[],
  channelEquivalents?: Array<{
    mercadolibre_sku: string;
    shopify_sku: string;
  }>
): string {
  // Only use catalog if both parameters are provided
  if (catalog && channelEquivalents) {
    const officialSKU = getProductOfficialSKU(product, channelEquivalents);
    const catalogProduct = catalog.find(p => p.sku === officialSKU);

    if (catalogProduct) {
      return catalogProduct.product_name;
    }
  }

  // Fallback: normalize product name
  return normalizeProductName(product.name);
}

/**
 * Group products by base code (using catalog)
 *
 * @param products - Array of products
 * @param catalog - Optional official catalog
 * @param channelEquivalents - Optional channel equivalents
 * @returns Map of base code to products
 */
export function groupProductsByBaseCode(
  products: Product[],
  catalog?: OfficialProduct[],
  channelEquivalents?: Array<{
    mercadolibre_sku: string;
    shopify_sku: string;
  }>
): Map<string, Product[]> {
  const groups = new Map<string, Product[]>();

  products.forEach(product => {
    const baseCode = getProductBaseCode(product, catalog, channelEquivalents);

    if (!groups.has(baseCode)) {
      groups.set(baseCode, []);
    }

    groups.get(baseCode)!.push(product);
  });

  return groups;
}

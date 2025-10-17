/**
 * Catalog API Client
 *
 * Fetches official product catalog from backend API.
 * Replaces hardcoded frontend catalog data.
 *
 * Author: TM3
 * Date: 2025-10-17
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';

export interface OfficialProduct {
  sku: string;
  category: string;
  product_name: string;
  base_code: string;
  package_type: string;
  units_per_display: number;
  is_active: boolean;
}

export interface CatalogResponse {
  status: string;
  total: number;
  data: OfficialProduct[];
}

export interface CatalogStatsResponse {
  status: string;
  data: {
    total_products: number;
    by_category: Record<string, number>;
    unique_base_codes: number;
  };
}

/**
 * Get all products from the official catalog
 *
 * @param category Optional category filter (BARRAS, GRANOLAS, etc.)
 * @param baseCode Optional base code filter (BAKC, GRAL, etc.)
 * @returns Promise with catalog products
 */
export async function getCatalog(
  category?: string,
  baseCode?: string
): Promise<OfficialProduct[]> {
  try {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (baseCode) params.append('base_code', baseCode);

    const queryString = params.toString();
    const url = `${API_BASE_URL}/api/v1/product-mapping/catalog${queryString ? `?${queryString}` : ''}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      // Cache for 5 minutes (catalog doesn't change often)
      next: { revalidate: 300 }
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch catalog: ${response.statusText}`);
    }

    const result: CatalogResponse = await response.json();
    return result.data;
  } catch (error) {
    console.error('Error fetching catalog:', error);
    throw error;
  }
}

/**
 * Get a single product by SKU from the official catalog
 *
 * @param sku Product SKU
 * @returns Promise with product or null if not found
 */
export async function getCatalogProduct(sku: string): Promise<OfficialProduct | null> {
  try {
    const url = `${API_BASE_URL}/api/v1/product-mapping/catalog/${sku}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      next: { revalidate: 300 }
    });

    if (response.status === 404) {
      return null;
    }

    if (!response.ok) {
      throw new Error(`Failed to fetch product: ${response.statusText}`);
    }

    const result = await response.json();
    return result.data;
  } catch (error) {
    console.error(`Error fetching product ${sku}:`, error);
    throw error;
  }
}

/**
 * Get catalog statistics
 *
 * @returns Promise with catalog stats
 */
export async function getCatalogStats(): Promise<CatalogStatsResponse['data']> {
  try {
    const url = `${API_BASE_URL}/api/v1/product-mapping/catalog/stats`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      next: { revalidate: 300 }
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch catalog stats: ${response.statusText}`);
    }

    const result: CatalogStatsResponse = await response.json();
    return result.data;
  } catch (error) {
    console.error('Error fetching catalog stats:', error);
    throw error;
  }
}

/**
 * Get products by category
 *
 * @param category Category name (BARRAS, GRANOLAS, etc.)
 * @returns Promise with filtered products
 */
export async function getProductsByCategory(category: string): Promise<OfficialProduct[]> {
  return getCatalog(category);
}

/**
 * Get products by base code
 *
 * @param baseCode Base code (BAKC, GRAL, etc.)
 * @returns Promise with filtered products
 */
export async function getProductsByBaseCode(baseCode: string): Promise<OfficialProduct[]> {
  return getCatalog(undefined, baseCode);
}

// Re-export for backward compatibility with existing code
export type { OfficialProduct as Product };

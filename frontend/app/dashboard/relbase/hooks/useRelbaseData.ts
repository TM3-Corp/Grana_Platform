'use client';

import { useState, useEffect } from 'react';

// Use localhost for development, fallback to env variable
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Types
export interface MappingStats {
  total_products: number;
  total_sales: number;
  mapped_products: number;
  mapped_sales: number;
  unmapped_products: number;
  unmapped_sales: number;
  service_items: number;
  service_sales: number;
  legacy_codes: number;
  legacy_sales: number;
  needs_review: number;
  by_match_type: {
    [key: string]: { count: number; sales: number };
  };
  by_confidence: {
    [key: string]: { count: number; sales: number };
  };
}

export interface TopProduct {
  relbase_code: string;
  relbase_name: string | null;
  official_sku: string | null;
  match_type: string;
  confidence_level: string;
  confidence_percentage: number;
  total_sales: number;
  is_mapped: boolean;
}

export interface MappingRecord {
  relbase_code: string;
  relbase_name: string | null;
  official_sku: string | null;
  match_type: string;
  confidence_level: string;
  confidence_percentage: number;
  total_sales: number;
  is_service_item: boolean;
  is_legacy_code: boolean;
  needs_manual_review: boolean;
}

export interface PaginatedMappings {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  data: MappingRecord[];
}

/**
 * Hook to fetch summary statistics for Relbase mappings
 */
export function useRelbaseStats() {
  const [stats, setStats] = useState<MappingStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/v1/relbase/stats`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        setStats(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return { stats, loading, error };
}

/**
 * Hook to fetch top N products by sales volume
 */
export function useTopProducts(limit: number = 20, excludeService: boolean = true) {
  const [products, setProducts] = useState<TopProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    fetch(`${API_URL}/api/v1/relbase/top-products?limit=${limit}&exclude_service=${excludeService}`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(data => {
        setProducts(data);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [limit, excludeService]);

  return { products, loading, error };
}

/**
 * Hook to fetch paginated mappings with filters
 */
export function useMappings(filters: {
  page?: number;
  page_size?: number;
  search?: string;
  match_type?: string;
  confidence?: string;
  needs_review?: boolean;
  exclude_service?: boolean;
  sort_by?: string;
  sort_order?: string;
} = {}) {
  const [data, setData] = useState<PaginatedMappings>({
    total: 0,
    page: 1,
    page_size: 50,
    total_pages: 0,
    data: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);

    // Build query params
    const params = new URLSearchParams();
    if (filters.page) params.append('page', String(filters.page));
    if (filters.page_size) params.append('page_size', String(filters.page_size));
    if (filters.search) params.append('search', filters.search);
    if (filters.match_type) params.append('match_type', filters.match_type);
    if (filters.confidence) params.append('confidence', filters.confidence);
    if (filters.needs_review !== undefined) params.append('needs_review', String(filters.needs_review));
    if (filters.exclude_service !== undefined) params.append('exclude_service', String(filters.exclude_service));
    if (filters.sort_by) params.append('sort_by', filters.sort_by);
    if (filters.sort_order) params.append('sort_order', filters.sort_order);

    fetch(`${API_URL}/api/v1/relbase/mappings?${params.toString()}`)
      .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then(result => {
        setData(result);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, [JSON.stringify(filters)]);

  return { ...data, loading, error };
}

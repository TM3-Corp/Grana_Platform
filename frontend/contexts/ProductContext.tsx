'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { filterValidProducts, type Product } from '@/lib/product-utils';

interface ProductContextType {
  products: Product[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

const ProductContext = createContext<ProductContextType | undefined>(undefined);

export function ProductProvider({ children }: { children: ReactNode }) {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      setError(null);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';
      const response = await fetch(`${apiUrl}/api/v1/products/?limit=1000`);

      if (!response.ok) {
        throw new Error('Error al cargar productos');
      }

      const data = await response.json();
      const allProducts: Product[] = data.data;
      const validProducts = filterValidProducts(allProducts);

      setProducts(validProducts);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  return (
    <ProductContext.Provider value={{ products, loading, error, refetch: fetchProducts }}>
      {children}
    </ProductContext.Provider>
  );
}

export function useProducts() {
  const context = useContext(ProductContext);
  if (context === undefined) {
    throw new Error('useProducts must be used within a ProductProvider');
  }
  return context;
}

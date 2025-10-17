'use client';

import React, { useState, useEffect } from 'react';
import {
  filterValidProducts,
  groupProductsByBaseCode,
  getProductOfficialCategory,
  getProductBaseCode,
  getProductUnitsPerDisplay,
  getFormat,
  type Product
} from '@/lib/product-utils';

interface ProductFamily {
  base_code: string; // BAKC, GRAL, etc.
  base_name: string;
  category: string; // GRANOLAS, BARRAS, CRACKERS, KEEPERS, KRUMS
  products: Product[];
}

interface SuperCategory {
  name: string; // GRANOLAS, BARRAS, CRACKERS, KEEPERS, KRUMS
  icon: string;
  families: ProductFamily[];
}

export default function ProductFamilyView() {
  const [superCategories, setSuperCategories] = useState<SuperCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedSuperCategory, setExpandedSuperCategory] = useState<string | null>(null);
  const [expandedFamily, setExpandedFamily] = useState<string | null>(null);

  useEffect(() => {
    fetchAndGroupProducts();
  }, []);

  const getBaseName = (name: string): string => {
    // Remove common suffixes to identify base product
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
  };

  const getSuperCategoryIcon = (category: string): string => {
    const icons: Record<string, string> = {
      'GRANOLAS': '🥣',
      'BARRAS': '🍫',
      'CRACKERS': '🍘',
      'KEEPERS': '🍬',
      'KRUMS': '🥨',
      'OTROS': '📦',
    };
    return icons[category] || '📦';
  };

  const fetchAndGroupProducts = async () => {
    try {
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';
      const response = await fetch(`${apiUrl}/api/v1/products/?limit=1000`);

      if (!response.ok) {
        throw new Error('Error al cargar productos');
      }

      const data = await response.json();
      let allProducts: Product[] = data.data;

      // Filter out obsolete ML products
      const validProducts = filterValidProducts(allProducts);

      // Group products by base code using official catalog
      // This automatically consolidates cross-channel products
      const baseCodeGroups = groupProductsByBaseCode(validProducts);

      // Create product families from base code groups
      const families: ProductFamily[] = [];

      baseCodeGroups.forEach((products, baseCode) => {
        // Only include families with multiple products OR products with multiple channels
        const uniqueChannels = new Set(products.map(p => p.source));

        if (products.length > 1 || uniqueChannels.size > 1) {
          // Get category from first product (they should all be the same family)
          const category = getProductOfficialCategory(products[0]);

          // Get base name from catalog
          const baseName = baseCode;

          families.push({
            base_code: baseCode,
            base_name: baseName,
            category: category,
            products: products,
          });
        }
      });

      // Group families by official category (GRANOLAS, BARRAS, CRACKERS, KEEPERS, KRUMS)
      const categoryMap = new Map<string, SuperCategory>();

      families.forEach((family) => {
        const categoryName = family.category;

        if (!categoryMap.has(categoryName)) {
          categoryMap.set(categoryName, {
            name: categoryName,
            icon: getSuperCategoryIcon(categoryName),
            families: [],
          });
        }

        categoryMap.get(categoryName)!.families.push(family);
      });

      // Sort categories and their families
      const categoriesArray = Array.from(categoryMap.values())
        .map((category) => ({
          ...category,
          families: category.families.sort((a, b) => b.products.length - a.products.length),
        }))
        .sort((a, b) => {
          // Official order from catalog
          const order = ['GRANOLAS', 'BARRAS', 'CRACKERS', 'KEEPERS', 'KRUMS', 'OTROS'];
          return order.indexOf(a.name) - order.indexOf(b.name);
        });

      setSuperCategories(categoriesArray);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value: number | null) => {
    if (value === null) return 'N/A';
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
    }).format(value);
  };

  const getPackagingIcon = (name: string) => {
    if (name.includes('Display con 16') || name.includes('16 Un')) return '📦📦📦';
    if (name.includes('Display con 18')) return '📦📦📦';
    if (name.includes('Display con 10')) return '📦📦';
    if (name.includes('Display con 5') || name.includes('5 Un')) return '📦📦';
    if (name.includes('Sachet') || name.includes('Individual')) return '📄';
    if (name.includes('250g') || name.includes('260g')) return '🥤';
    if (name.includes('500g')) return '🥤🥤';
    return '📦';
  };

  const getCategoryIcon = (category: string) => {
    const icons: Record<string, string> = {
      'GRANOLAS': '🥣',
      'BARRAS': '🍫',
      'CRACKERS': '🍘',
      'KEEPERS': '🍬',
      'KRUMS': '🥨',
      // Legacy support
      'Barra': '🍫',
      'Barritas': '🍫',
      'Crackers': '🍘',
      'Granola': '🥣',
      'Granolas': '🥣',
      'Keeper': '🍬',
    };
    return icons[category] || '📦';
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center p-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-700">❌ {error}</p>
      </div>
    );
  }

  if (superCategories.length === 0) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-8 text-center">
        <p className="text-blue-700">ℹ️ No hay familias de productos identificadas</p>
        <p className="text-sm text-blue-600 mt-2">
          Las familias se identifican automáticamente por productos con variantes
        </p>
      </div>
    );
  }

  const totalFamilies = superCategories.reduce((sum, sc) => sum + sc.families.length, 0);
  const totalVariants = superCategories.reduce(
    (sum, sc) => sum + sc.families.reduce((fsum, f) => fsum + f.products.length, 0),
    0
  );

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-700">
          💡 <strong>{superCategories.length}</strong> categorías principales • <strong>{totalFamilies}</strong> familias • <strong>{totalVariants}</strong> variantes
        </p>
      </div>

      {/* Super Categories */}
      {superCategories.map((superCat, idx) => (
        <div key={idx} className="bg-white border-2 border-gray-300 rounded-xl overflow-hidden shadow-md">
          {/* Super Category Header */}
          <div
            className="bg-gradient-to-r from-blue-500 to-purple-500 text-white p-6 cursor-pointer hover:from-blue-600 hover:to-purple-600 transition-all"
            onClick={() =>
              setExpandedSuperCategory(expandedSuperCategory === superCat.name ? null : superCat.name)
            }
          >
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-4">
                <span className="text-5xl">{superCat.icon}</span>
                <div>
                  <h2 className="text-2xl font-bold">{superCat.name}</h2>
                  <p className="text-sm opacity-90 mt-1">
                    {superCat.families.length} familia{superCat.families.length !== 1 ? 's' : ''} de productos
                  </p>
                </div>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold">
                  {superCat.families.reduce((sum, f) => sum + f.products.reduce((psum, p) => psum + (p.current_stock || 0), 0), 0).toLocaleString()}
                </div>
                <div className="text-sm opacity-90">Stock Total</div>
                <div className="text-xs opacity-75 mt-2">
                  {expandedSuperCategory === superCat.name ? '▲ Ocultar' : '▼ Ver familias'}
                </div>
              </div>
            </div>
          </div>

          {/* Families within Super Category */}
          {expandedSuperCategory === superCat.name && (
            <div className="p-4 space-y-3 bg-gray-50">
              {superCat.families.map((family, fidx) => {
        const baseProduct = family.products.find((p) =>
          p.name.includes('1 unidad') || p.name.includes('1 barrita') || !p.name.includes('Display')
        ) || family.products[0];

                return (
                  <div key={fidx} className="bg-white border border-gray-300 rounded-lg overflow-hidden shadow-sm">
                    <div
                      className="bg-gradient-to-r from-gray-50 to-gray-100 border-b p-4 cursor-pointer hover:from-gray-100 hover:to-gray-200 transition-all"
                      onClick={() =>
                        setExpandedFamily(expandedFamily === family.base_name ? null : family.base_name)
                      }
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{getCategoryIcon(family.category)}</span>
                          <div>
                            <div className="flex items-center gap-2">
                              <h3 className="font-semibold text-gray-900">{family.base_code}</h3>
                              <span className="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-800">
                                {family.category}
                              </span>
                            </div>
                            <p className="text-xs text-gray-600 mt-1">
                              {family.products.length} variante(s) • {new Set(family.products.map(p => p.source)).size} canal(es)
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-xs text-gray-600">Stock Total</div>
                          <div className="font-bold text-blue-600">
                            {family.products.reduce((sum, p) => sum + (p.current_stock || 0), 0).toLocaleString()}
                          </div>
                          <div className="text-xs text-gray-500 mt-1">
                            {expandedFamily === family.base_name ? '▲ Ocultar' : '▼ Ver variantes'}
                          </div>
                        </div>
                      </div>
                    </div>

                    {expandedFamily === family.base_name && (
              <div className="p-4 space-y-3 bg-gray-50">
                {family.products
                  .sort((a, b) => {
                    // Sort by units per display (1un, 5un, 16un, etc.)
                    const unitsA = getProductUnitsPerDisplay(a);
                    const unitsB = getProductUnitsPerDisplay(b);
                    return unitsA - unitsB;
                  })
                  .map((product) => {
                    const isLowStock = (product.current_stock || 0) < (product.min_stock || 0);
                    const isOversold = (product.current_stock || 0) < 0;
                    const unitsPerDisplay = getProductUnitsPerDisplay(product);

                    return (
                      <div
                        key={product.id}
                        className={`border rounded-lg p-4 bg-white ${
                          isOversold ? 'border-red-300 bg-red-50' :
                          isLowStock ? 'border-yellow-300 bg-yellow-50' :
                          'border-gray-200'
                        }`}
                      >
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                          {/* Product Info */}
                          <div className="col-span-2">
                            <div className="flex items-start gap-2">
                              <span className="text-2xl">{getPackagingIcon(product.name)}</span>
                              <div>
                                <h4 className="font-medium text-gray-900">{product.name}</h4>
                                <p className="text-xs text-gray-600 font-mono mt-1">{product.sku}</p>
                                <div className="flex gap-2 mt-1">
                                  <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-800">
                                    {product.source}
                                  </span>
                                  <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-800">
                                    {unitsPerDisplay} {unitsPerDisplay === 1 ? 'un' : 'un/display'}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* Stock */}
                          <div className="text-center">
                            <div className="text-xs text-gray-600 mb-1">Stock Actual</div>
                            <div className={`text-2xl font-bold ${
                              isOversold ? 'text-red-600' :
                              isLowStock ? 'text-yellow-600' :
                              'text-green-600'
                            }`}>
                              {(product.current_stock || 0).toLocaleString()}
                            </div>
                            {product.min_stock !== null && (
                              <div className="text-xs text-gray-500 mt-1">
                                Min: {product.min_stock}
                              </div>
                            )}
                            {isOversold && (
                              <span className="text-xs font-medium text-red-600">⚠️ Sobrevendido</span>
                            )}
                            {isLowStock && !isOversold && (
                              <span className="text-xs font-medium text-yellow-600">⚠️ Stock bajo</span>
                            )}
                          </div>

                          {/* Pricing */}
                          <div className="text-right">
                            <div className="text-xs text-gray-600 mb-1">Precio</div>
                            <div className="text-xl font-bold text-green-600">
                              {formatCurrency(product.sale_price)}
                            </div>
                            {product.sale_price && baseProduct.sale_price &&
                             product.id !== baseProduct.id && baseProduct.sale_price > 0 && (
                              <div className="text-xs text-gray-500 mt-1">
                                {formatCurrency(product.sale_price / (baseProduct.sale_price || 1))} / unidad
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

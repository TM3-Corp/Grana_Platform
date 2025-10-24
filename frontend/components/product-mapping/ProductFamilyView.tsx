'use client';

import React, { useState, useEffect } from 'react';

// New hierarchical structure from API
interface Product {
  sku: string;
  name: string;
  stock: number;
  price: number | null;
  package_type: string | null;
  units_per_package: number | null;
  master_box_sku: string | null;
  master_box_name: string | null;
}

interface Format {
  name: string;
  product_count: number;
  total_stock: number;
  products: Product[];
}

interface Subfamily {
  name: string;
  formats: Format[];
  total_stock: number;
}

interface Category {
  name: string;
  subfamilies: Subfamily[];
  total_stock: number;
}

export default function ProductFamilyView() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [originalCategories, setOriginalCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);
  const [expandedSubfamily, setExpandedSubfamily] = useState<string | null>(null);
  const [expandedFormat, setExpandedFormat] = useState<string | null>(null);

  // Filter states
  const [selectedFormats, setSelectedFormats] = useState<string[]>([]);
  const [selectedChannels, setSelectedChannels] = useState<string[]>([]);
  const [availableFormats, setAvailableFormats] = useState<string[]>([]);
  const [availableChannels, setAvailableChannels] = useState<string[]>([]);

  useEffect(() => {
    fetchHierarchicalFamilies();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [selectedFormats, selectedChannels, originalCategories]);

  const getCategoryIcon = (category: string): string => {
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

  const fetchHierarchicalFamilies = async () => {
    try {
      setLoading(true);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';
      const response = await fetch(`${apiUrl}/api/v1/product-mapping/families/hierarchical`);

      if (!response.ok) {
        throw new Error('Error al cargar familias de productos');
      }

      const result = await response.json();

      if (result.status === 'success' && result.data) {
        // Sort categories by standard order
        const sortedCategories = result.data.sort((a: Category, b: Category) => {
          const order = ['GRANOLAS', 'BARRAS', 'CRACKERS', 'KEEPERS', 'KRUMS', 'OTROS'];
          return order.indexOf(a.name) - order.indexOf(b.name);
        });

        setOriginalCategories(sortedCategories);
        setCategories(sortedCategories);

        // Extract available formats and channels
        extractFiltersFromData(sortedCategories);
      } else {
        throw new Error('Formato de respuesta inválido');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  const extractFiltersFromData = (data: Category[]) => {
    const formats = new Set<string>();
    const channels = new Set<string>();

    data.forEach(category => {
      category.subfamilies.forEach(subfamily => {
        subfamily.formats.forEach(format => {
          formats.add(format.name);

          // Extract channel from SKU
          format.products.forEach(product => {
            if (product.sku.startsWith('ML-')) {
              channels.add('MercadoLibre');
            } else if (product.sku.match(/^[A-Z]{4}_/)) {
              channels.add('Catálogo Oficial');
            } else if (product.sku.startsWith('PACK')) {
              channels.add('Packs');
            } else {
              channels.add('Shopify');
            }
          });
        });
      });
    });

    setAvailableFormats(Array.from(formats).sort());
    setAvailableChannels(Array.from(channels).sort());
  };

  const applyFilters = () => {
    if (selectedFormats.length === 0 && selectedChannels.length === 0) {
      setCategories(originalCategories);
      return;
    }

    const filtered = originalCategories.map(category => {
      const filteredSubfamilies = category.subfamilies.map(subfamily => {
        const filteredFormats = subfamily.formats
          .filter(format => {
            // Filter by format
            if (selectedFormats.length > 0 && !selectedFormats.includes(format.name)) {
              return false;
            }

            // Filter by channel
            if (selectedChannels.length > 0) {
              const hasMatchingChannel = format.products.some(product => {
                if (selectedChannels.includes('MercadoLibre') && product.sku.startsWith('ML-')) return true;
                if (selectedChannels.includes('Catálogo Oficial') && product.sku.match(/^[A-Z]{4}_/)) return true;
                if (selectedChannels.includes('Packs') && product.sku.startsWith('PACK')) return true;
                if (selectedChannels.includes('Shopify') &&
                    !product.sku.startsWith('ML-') &&
                    !product.sku.match(/^[A-Z]{4}_/) &&
                    !product.sku.startsWith('PACK')) return true;
                return false;
              });
              if (!hasMatchingChannel) return false;
            }

            return true;
          })
          .map(format => {
            // If channel filter is active, filter products within format
            if (selectedChannels.length > 0) {
              const filteredProducts = format.products.filter(product => {
                if (selectedChannels.includes('MercadoLibre') && product.sku.startsWith('ML-')) return true;
                if (selectedChannels.includes('Catálogo Oficial') && product.sku.match(/^[A-Z]{4}_/)) return true;
                if (selectedChannels.includes('Packs') && product.sku.startsWith('PACK')) return true;
                if (selectedChannels.includes('Shopify') &&
                    !product.sku.startsWith('ML-') &&
                    !product.sku.match(/^[A-Z]{4}_/) &&
                    !product.sku.startsWith('PACK')) return true;
                return false;
              });

              return {
                ...format,
                products: filteredProducts,
                product_count: filteredProducts.length,
                total_stock: filteredProducts.reduce((sum, p) => sum + (p.stock || 0), 0)
              };
            }

            return format;
          });

        return {
          ...subfamily,
          formats: filteredFormats,
          total_stock: filteredFormats.reduce((sum, f) => sum + f.total_stock, 0)
        };
      }).filter(subfamily => subfamily.formats.length > 0);

      return {
        ...category,
        subfamilies: filteredSubfamilies,
        total_stock: filteredSubfamilies.reduce((sum, sf) => sum + sf.total_stock, 0)
      };
    }).filter(category => category.subfamilies.length > 0);

    setCategories(filtered);
  };

  const toggleFormat = (format: string) => {
    setSelectedFormats(prev =>
      prev.includes(format)
        ? prev.filter(f => f !== format)
        : [...prev, format]
    );
  };

  const toggleChannel = (channel: string) => {
    setSelectedChannels(prev =>
      prev.includes(channel)
        ? prev.filter(c => c !== channel)
        : [...prev, channel]
    );
  };

  const clearFilters = () => {
    setSelectedFormats([]);
    setSelectedChannels([]);
  };

  const formatCurrency = (value: number | null) => {
    if (value === null) return 'N/A';
    return new Intl.NumberFormat('es-CL', {
      style: 'currency',
      currency: 'CLP',
      minimumFractionDigits: 0,
    }).format(value);
  };

  const getFormatIcon = (formatName: string) => {
    if (formatName.includes('X16') || formatName.includes('16')) return '📦📦📦';
    if (formatName.includes('X18') || formatName.includes('18')) return '📦📦📦';
    if (formatName.includes('X12') || formatName.includes('12')) return '📦📦';
    if (formatName.includes('X5') || formatName.includes('5')) return '📦📦';
    if (formatName.includes('X7') || formatName.includes('7')) return '📦📦';
    if (formatName.includes('X4') || formatName.includes('4')) return '📦';
    if (formatName.includes('Sachet') || formatName.includes('X1') || formatName.includes('1')) return '📄';
    if (formatName.includes('260') || formatName.includes('240') || formatName.includes('210')) return '🥤';
    if (formatName.includes('500')) return '🥤🥤';
    if (formatName.includes('135')) return '📦';
    return '📦';
  };

  const classifySubfamiliesByStock = (subfamilies: Subfamily[]) => {
    const positive: Subfamily[] = [];
    const zero: Subfamily[] = [];
    const negative: Subfamily[] = [];

    subfamilies.forEach(subfamily => {
      if (subfamily.total_stock > 0) {
        positive.push(subfamily);
      } else if (subfamily.total_stock === 0) {
        zero.push(subfamily);
      } else {
        negative.push(subfamily);
      }
    });

    return { positive, zero, negative };
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

  if (categories.length === 0) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-8 text-center">
        <p className="text-blue-700">ℹ️ No hay familias de productos identificadas</p>
        <p className="text-sm text-blue-600 mt-2">
          Revisa que los productos tengan información de jerarquía (category, subfamily, format)
        </p>
      </div>
    );
  }

  const totalSubfamilies = categories.reduce((sum, cat) => sum + cat.subfamilies.length, 0);
  const totalFormats = categories.reduce(
    (sum, cat) => sum + cat.subfamilies.reduce((fsum, sf) => fsum + sf.formats.length, 0),
    0
  );

  const activeFiltersCount = selectedFormats.length + selectedChannels.length;

  return (
    <div className="space-y-6">
      {/* Filters Section */}
      <div className="bg-white border-2 border-gray-300 rounded-xl p-6 shadow-md">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-gray-900">
            🔍 Filtros {activeFiltersCount > 0 && <span className="text-blue-600">({activeFiltersCount} activos)</span>}
          </h3>
          {activeFiltersCount > 0 && (
            <button
              onClick={clearFilters}
              className="px-3 py-1 text-sm bg-red-100 text-red-700 rounded-lg hover:bg-red-200 transition-colors"
            >
              Limpiar filtros
            </button>
          )}
        </div>

        {/* Format Filters */}
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">📦 Formato:</h4>
          <div className="flex flex-wrap gap-2">
            {availableFormats.map(format => (
              <button
                key={format}
                onClick={() => toggleFormat(format)}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-all ${
                  selectedFormats.includes(format)
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {format}
                {selectedFormats.includes(format) && ' ✓'}
              </button>
            ))}
          </div>
        </div>

        {/* Channel Filters */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">🛒 Canal de Venta:</h4>
          <div className="flex flex-wrap gap-2">
            {availableChannels.map(channel => {
              const channelIcons: Record<string, string> = {
                'Catálogo Oficial': '📋',
                'MercadoLibre': '🔷',
                'Shopify': '🛍️',
                'Packs': '📦'
              };
              return (
                <button
                  key={channel}
                  onClick={() => toggleChannel(channel)}
                  className={`px-3 py-1 rounded-full text-sm font-medium transition-all ${
                    selectedChannels.includes(channel)
                      ? 'bg-green-600 text-white shadow-md'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  {channelIcons[channel]} {channel}
                  {selectedChannels.includes(channel) && ' ✓'}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-700">
          💡 <strong>{categories.length}</strong> categorías • <strong>{totalSubfamilies}</strong> subfamilias • <strong>{totalFormats}</strong> formatos
          {activeFiltersCount > 0 && <span className="ml-2 text-purple-700">(Filtrado)</span>}
        </p>
      </div>

      {/* Categories (GRANOLAS, BARRAS, CRACKERS, KEEPERS) */}
      {categories.map((category, idx) => {
        const { positive, zero, negative } = classifySubfamiliesByStock(category.subfamilies);

        return (
          <div key={idx} className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow">
            {/* Category Header */}
            <div
              className="bg-gradient-to-r from-blue-500 to-purple-500 text-white p-5 cursor-pointer hover:opacity-95 transition-opacity"
              onClick={() => setExpandedCategory(expandedCategory === category.name ? null : category.name)}
            >
              <div className="flex items-center justify-between gap-4">
                {/* Left: Icon + Title */}
                <div className="flex items-center gap-3 flex-1">
                  <span className="text-3xl">{getCategoryIcon(category.name)}</span>
                  <div>
                    <h2 className="text-lg font-bold">{category.name}</h2>
                    <p className="text-xs opacity-80">
                      {category.subfamilies.length} subfamilia{category.subfamilies.length !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>

                {/* Center: Traffic Light Indicators */}
                <div className="flex items-center gap-4 px-6">
                  <div className="flex flex-col items-center">
                    <div className="w-8 h-8 rounded-full bg-green-400 bg-opacity-30 flex items-center justify-center">
                      <span className="text-xs font-bold">{positive.length}</span>
                    </div>
                    <span className="text-[10px] opacity-70 mt-0.5">Con stock</span>
                  </div>
                  <div className="flex flex-col items-center">
                    <div className="w-8 h-8 rounded-full bg-yellow-400 bg-opacity-30 flex items-center justify-center">
                      <span className="text-xs font-bold">{zero.length}</span>
                    </div>
                    <span className="text-[10px] opacity-70 mt-0.5">Sin stock</span>
                  </div>
                  <div className="flex flex-col items-center">
                    <div className="w-8 h-8 rounded-full bg-red-400 bg-opacity-30 flex items-center justify-center">
                      <span className="text-xs font-bold">{negative.length}</span>
                    </div>
                    <span className="text-[10px] opacity-70 mt-0.5">Negativo</span>
                  </div>
                </div>

                {/* Right: Stock Total */}
                <div className="text-right">
                  <div className="text-2xl font-bold">
                    {category.total_stock.toLocaleString()}
                  </div>
                  <div className="text-xs opacity-80">Stock Total</div>
                  <div className="text-xs opacity-60 mt-1">
                    {expandedCategory === category.name ? '▲ Ocultar' : '▼ Ver más'}
                  </div>
                </div>
              </div>

              {/* Stock Preview - Compact List */}
              <div className="grid grid-cols-3 gap-3 mt-4 pt-4 border-t border-white border-opacity-20">
                {/* Green Column */}
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <div className="w-2 h-2 rounded-full bg-green-400"></div>
                    <span className="text-[10px] font-semibold opacity-90">Stock Positivo</span>
                  </div>
                  <div className="space-y-1">
                    {positive.slice(0, 4).map((subfamily, idx) => (
                      <button
                        key={idx}
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedCategory(category.name);
                          setExpandedSubfamily(subfamily.name);
                        }}
                        className="block w-full text-left text-[10px] leading-snug opacity-75 hover:opacity-100 truncate transition-opacity"
                        title={subfamily.name}
                      >
                        • {subfamily.name}
                      </button>
                    ))}
                    {positive.length > 4 && (
                      <div className="text-[9px] opacity-50 italic">+{positive.length - 4} más</div>
                    )}
                    {positive.length === 0 && (
                      <div className="text-[10px] opacity-40 italic">Sin productos</div>
                    )}
                  </div>
                </div>

                {/* Yellow Column */}
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <div className="w-2 h-2 rounded-full bg-yellow-400"></div>
                    <span className="text-[10px] font-semibold opacity-90">Sin Stock</span>
                  </div>
                  <div className="space-y-1">
                    {zero.slice(0, 4).map((subfamily, idx) => (
                      <button
                        key={idx}
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedCategory(category.name);
                          setExpandedSubfamily(subfamily.name);
                        }}
                        className="block w-full text-left text-[10px] leading-snug opacity-75 hover:opacity-100 truncate transition-opacity"
                        title={subfamily.name}
                      >
                        • {subfamily.name}
                      </button>
                    ))}
                    {zero.length > 4 && (
                      <div className="text-[9px] opacity-50 italic">+{zero.length - 4} más</div>
                    )}
                    {zero.length === 0 && (
                      <div className="text-[10px] opacity-40 italic">Sin productos</div>
                    )}
                  </div>
                </div>

                {/* Red Column */}
                <div>
                  <div className="flex items-center gap-1.5 mb-2">
                    <div className="w-2 h-2 rounded-full bg-red-400"></div>
                    <span className="text-[10px] font-semibold opacity-90">Stock Negativo</span>
                  </div>
                  <div className="space-y-1">
                    {negative.slice(0, 4).map((subfamily, idx) => (
                      <button
                        key={idx}
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedCategory(category.name);
                          setExpandedSubfamily(subfamily.name);
                        }}
                        className="block w-full text-left text-[10px] leading-snug opacity-75 hover:opacity-100 truncate transition-opacity"
                        title={subfamily.name}
                      >
                        • {subfamily.name}
                      </button>
                    ))}
                    {negative.length > 4 && (
                      <div className="text-[9px] opacity-50 italic">+{negative.length - 4} más</div>
                    )}
                    {negative.length === 0 && (
                      <div className="text-[10px] opacity-40 italic">Sin productos</div>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Subfamilies (e.g., "Barra Keto Nuez", "Granola Low Carb Almendras") */}
            {expandedCategory === category.name && (
              <div className="p-4 bg-gray-50">
                {/* Subfamily List - Sorted by Criticality */}
                <div className="space-y-3">
                  <h3 className="text-md font-semibold text-gray-700 px-2">📋 Lista Completa de Subfamilias (Ordenadas por Criticidad)</h3>
                  {[...category.subfamilies]
                    .sort((a, b) => a.total_stock - b.total_stock)
                    .map((subfamily, sfIdx) => {
                      // Determinar nivel de criticidad
                      const getStockStatus = (stock: number) => {
                        if (stock < 0) return { label: 'Stock Crítico', color: 'bg-red-100 text-red-800 border-red-300', textColor: 'text-red-700' };
                        if (stock === 0) return { label: 'Sin Stock', color: 'bg-yellow-100 text-yellow-800 border-yellow-300', textColor: 'text-yellow-700' };
                        if (stock <= 30) return { label: 'Stock Bajo', color: 'bg-orange-100 text-orange-800 border-orange-300', textColor: 'text-orange-700' };
                        return { label: 'Stock Positivo', color: 'bg-green-100 text-green-800 border-green-300', textColor: 'text-green-700' };
                      };

                      const status = getStockStatus(subfamily.total_stock);

                      return (
                    <div key={sfIdx} className={`bg-white border-2 rounded-lg overflow-hidden shadow-sm ${
                      subfamily.total_stock < 0 ? 'border-red-200' :
                      subfamily.total_stock === 0 ? 'border-yellow-200' :
                      subfamily.total_stock <= 30 ? 'border-orange-200' :
                      'border-green-200'
                    }`}>
                      <div
                        className={`border-b p-4 cursor-pointer transition-all ${
                          subfamily.total_stock < 0 ? 'bg-red-50 hover:bg-red-100' :
                          subfamily.total_stock === 0 ? 'bg-yellow-50 hover:bg-yellow-100' :
                          subfamily.total_stock <= 30 ? 'bg-orange-50 hover:bg-orange-100' :
                          'bg-green-50 hover:bg-green-100'
                        }`}
                        onClick={() =>
                          setExpandedSubfamily(expandedSubfamily === subfamily.name ? null : subfamily.name)
                        }
                      >
                        <div className="flex justify-between items-start">
                          <div className="flex items-center gap-3 flex-1">
                            <span className="text-2xl">{getCategoryIcon(category.name)}</span>
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <h3 className="font-semibold text-gray-900">{subfamily.name}</h3>
                                <span className={`px-2 py-0.5 text-[10px] font-semibold rounded-full border ${status.color}`}>
                                  {status.label}
                                </span>
                              </div>
                              <p className="text-xs text-gray-600">
                                {subfamily.formats.length} formato{subfamily.formats.length !== 1 ? 's' : ''}
                              </p>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-xs text-gray-600 mb-1">Stock Total</div>
                            <div className={`text-xl font-bold ${status.textColor}`}>
                              {subfamily.total_stock.toLocaleString()}
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {expandedSubfamily === subfamily.name ? '▲ Ocultar' : '▼ Ver formatos'}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Formats (X1, X5, X16, etc.) */}
                      {expandedSubfamily === subfamily.name && (
                        <div className="p-4 space-y-3 bg-gray-50">
                          {subfamily.formats.map((format, fIdx) => (
                            <div key={fIdx} className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                              <div
                                className="bg-gray-50 border-b p-3 cursor-pointer hover:bg-gray-100 transition-all"
                                onClick={() =>
                                  setExpandedFormat(expandedFormat === `${subfamily.name}-${format.name}` ? null : `${subfamily.name}-${format.name}`)
                                }
                              >
                                <div className="flex justify-between items-center">
                                  <div className="flex items-center gap-2">
                                    <span className="text-xl">{getFormatIcon(format.name)}</span>
                                    <div>
                                      <span className="font-medium text-gray-800">{format.name}</span>
                                      <span className="text-xs text-gray-500 ml-2">
                                        ({format.product_count} producto{format.product_count !== 1 ? 's' : ''})
                                      </span>
                                    </div>
                                  </div>
                                  <div className="text-right">
                                    <div className="text-sm font-semibold text-blue-600">
                                      Stock: {format.total_stock.toLocaleString()}
                                    </div>
                                    <div className="text-xs text-gray-500">
                                      {expandedFormat === `${subfamily.name}-${format.name}` ? '▲' : '▼'}
                                    </div>
                                  </div>
                                </div>
                              </div>

                              {/* Products within Format */}
                              {expandedFormat === `${subfamily.name}-${format.name}` && (
                                <div className="p-3 space-y-2 bg-gray-50">
                                  {format.products.map((product, pIdx) => {
                                    const isOversold = (product.stock || 0) < 0;
                                    const isLowStock = (product.stock || 0) < 10 && (product.stock || 0) >= 0;

                                    return (
                                      <div
                                        key={pIdx}
                                        className={`border rounded-lg p-3 ${
                                          isOversold ? 'border-red-300 bg-red-50' :
                                          isLowStock ? 'border-yellow-300 bg-yellow-50' :
                                          'border-gray-200 bg-white'
                                        }`}
                                      >
                                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                                          {/* Product Info */}
                                          <div>
                                            <h4 className="font-medium text-sm text-gray-900">{product.name}</h4>
                                            <p className="text-xs text-gray-600 font-mono mt-1">{product.sku}</p>
                                            {product.package_type && (
                                              <span className="inline-block px-2 py-0.5 text-xs rounded-full bg-purple-100 text-purple-800 mt-1">
                                                {product.package_type}
                                                {product.units_per_package && ` (${product.units_per_package} un)`}
                                              </span>
                                            )}
                                          </div>

                                          {/* Stock */}
                                          <div className="text-center">
                                            <div className="text-xs text-gray-600">Stock</div>
                                            <div className={`text-xl font-bold ${
                                              isOversold ? 'text-red-600' :
                                              isLowStock ? 'text-yellow-600' :
                                              'text-green-600'
                                            }`}>
                                              {(product.stock || 0).toLocaleString()}
                                            </div>
                                            {isOversold && (
                                              <span className="text-xs font-medium text-red-600">⚠️ Sobrevendido</span>
                                            )}
                                            {isLowStock && (
                                              <span className="text-xs font-medium text-yellow-600">⚠️ Stock bajo</span>
                                            )}
                                          </div>

                                          {/* Price & Master Box */}
                                          <div className="text-right">
                                            <div className="text-xs text-gray-600">Precio</div>
                                            <div className="text-lg font-bold text-green-600">
                                              {formatCurrency(product.price)}
                                            </div>
                                            {product.master_box_sku && (
                                              <div className="text-xs text-gray-500 mt-1">
                                                📦 {product.master_box_sku}
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
                          ))}
                        </div>
                      )}
                    </div>
                      );
                    })}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

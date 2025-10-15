'use client';

import React, { useState, useEffect } from 'react';

interface ChannelEquivalent {
  id: number;
  shopify_product_id: number;
  mercadolibre_product_id: number;
  equivalence_confidence: number;
  verified: boolean;
  notes: string | null;
  // Joined product data
  shopify_sku: string;
  shopify_name: string;
  shopify_price: number | null;
  shopify_stock: number;
  ml_sku: string;
  ml_name: string;
  ml_price: number | null;
  ml_stock: number;
}

export default function ChannelEquivalentsView() {
  const [equivalents, setEquivalents] = useState<ChannelEquivalent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchEquivalents();
  }, []);

  const fetchEquivalents = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/product-mapping/channel-equivalents`);

      if (!response.ok) {
        throw new Error('Error al cargar equivalencias entre canales');
      }

      const data = await response.json();
      setEquivalents(data);
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

  const calculatePriceDiff = (shopifyPrice: number | null, mlPrice: number | null) => {
    if (!shopifyPrice || !mlPrice) return null;

    const diff = mlPrice - shopifyPrice;
    const percentage = (diff / shopifyPrice) * 100;

    return {
      amount: diff,
      percentage: percentage,
      isMLCheaper: diff < 0,
      isMLExpensive: diff > 0,
    };
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

  if (equivalents.length === 0) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-8 text-center">
        <p className="text-blue-700">ℹ️ No hay equivalencias entre canales configuradas aún</p>
        <p className="text-sm text-blue-600 mt-2">
          Las equivalencias mapean el mismo producto entre Shopify y MercadoLibre
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-700">
          💡 <strong>{equivalents.length}</strong> equivalencias entre canales encontradas
        </p>
      </div>

      {equivalents.map((equiv) => {
        const priceDiff = calculatePriceDiff(equiv.shopify_price, equiv.ml_price);
        const confidenceColor = equiv.equivalence_confidence >= 0.9 ? 'green' : equiv.equivalence_confidence >= 0.7 ? 'yellow' : 'orange';

        return (
          <div key={equiv.id} className="bg-white border rounded-lg overflow-hidden">
            <div className="bg-gray-50 border-b p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">🔄</span>
                  <div>
                    <h3 className="font-semibold text-gray-900">Equivalencia Cross-Canal</h3>
                    {equiv.notes && (
                      <p className="text-sm text-gray-600">{equiv.notes}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {equiv.verified ? (
                    <span className="px-3 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full border border-green-300">
                      ✓ Verificado
                    </span>
                  ) : (
                    <span className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded-full border border-gray-300">
                      Sugerencia automática
                    </span>
                  )}
                  <span className={`px-3 py-1 bg-${confidenceColor}-100 text-${confidenceColor}-700 text-xs font-medium rounded-full border border-${confidenceColor}-300`}>
                    {Math.round(equiv.equivalence_confidence * 100)}% confianza
                  </span>
                </div>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4 p-6">
              {/* Shopify Product */}
              <div className="border-r pr-6">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-2xl">🛍️</span>
                  <h4 className="font-semibold text-gray-900">Shopify</h4>
                </div>

                <div className="space-y-2">
                  <div>
                    <div className="text-xs text-gray-600">SKU</div>
                    <div className="font-mono text-sm">{equiv.shopify_sku}</div>
                  </div>

                  <div>
                    <div className="text-xs text-gray-600">Nombre</div>
                    <div className="text-sm">{equiv.shopify_name}</div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 pt-2">
                    <div>
                      <div className="text-xs text-gray-600">Precio</div>
                      <div className="text-lg font-semibold text-gray-900">
                        {formatCurrency(equiv.shopify_price)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600">Stock</div>
                      <div className={`text-lg font-semibold ${equiv.shopify_stock < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                        {equiv.shopify_stock.toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* MercadoLibre Product */}
              <div className="pl-6">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-2xl">📦</span>
                  <h4 className="font-semibold text-gray-900">MercadoLibre</h4>
                </div>

                <div className="space-y-2">
                  <div>
                    <div className="text-xs text-gray-600">SKU</div>
                    <div className="font-mono text-sm">{equiv.ml_sku}</div>
                  </div>

                  <div>
                    <div className="text-xs text-gray-600">Nombre</div>
                    <div className="text-sm">{equiv.ml_name}</div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 pt-2">
                    <div>
                      <div className="text-xs text-gray-600">Precio</div>
                      <div className="text-lg font-semibold text-gray-900">
                        {formatCurrency(equiv.ml_price)}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-gray-600">Stock</div>
                      <div className={`text-lg font-semibold ${equiv.ml_stock < 0 ? 'text-red-600' : 'text-gray-900'}`}>
                        {equiv.ml_stock.toLocaleString()}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Price Comparison */}
            {priceDiff && (
              <div className={`border-t p-4 ${priceDiff.isMLCheaper ? 'bg-blue-50' : priceDiff.isMLExpensive ? 'bg-orange-50' : 'bg-gray-50'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {priceDiff.isMLCheaper && (
                      <>
                        <span className="text-2xl">💰</span>
                        <div>
                          <div className="text-sm font-medium text-blue-900">
                            MercadoLibre es más barato
                          </div>
                          <div className="text-xs text-blue-700">
                            {formatCurrency(Math.abs(priceDiff.amount))} menos ({Math.abs(priceDiff.percentage).toFixed(1)}% descuento)
                          </div>
                        </div>
                      </>
                    )}
                    {priceDiff.isMLExpensive && (
                      <>
                        <span className="text-2xl">⚠️</span>
                        <div>
                          <div className="text-sm font-medium text-orange-900">
                            MercadoLibre es más caro
                          </div>
                          <div className="text-xs text-orange-700">
                            {formatCurrency(priceDiff.amount)} más (+{priceDiff.percentage.toFixed(1)}%)
                          </div>
                        </div>
                      </>
                    )}
                  </div>

                  <div className="text-right">
                    <div className="text-xs text-gray-600">Stock Total</div>
                    <div className="text-lg font-bold text-gray-900">
                      {(equiv.shopify_stock + equiv.ml_stock).toLocaleString()} unidades
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

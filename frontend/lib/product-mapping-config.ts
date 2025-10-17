/**
 * Product Mapping Configuration
 *
 * Este archivo mapea productos base con sus variantes en diferentes formatos y canales.
 * Permite visualizaciones agregadas de ventas por producto, desglosadas por formato y canal.
 */

export interface ProductVariant {
  sku: string;
  channel: 'shopify' | 'mercadolibre' | 'manual';
  format: string; // '1un', '5un', '16un', '18un', '210g', '260g', etc.
  formatDescription: string; // Descripción legible del formato
}

export interface BaseProduct {
  id: string; // ID único del producto base
  name: string; // Nombre del producto base
  family: 'Barritas' | 'Granolas' | 'Crackers' | 'Keeper';
  variants: ProductVariant[];
}

/**
 * MAPEO COMPLETO DE PRODUCTOS
 * =========================
 *
 * Cada producto base agrupa todas sus variantes en diferentes formatos y canales.
 * Esto permite analizar ventas totales por producto, desglosadas por:
 * - Formato (1 unidad, display 5, display 16, etc.)
 * - Canal (Shopify, MercadoLibre, Manual)
 */

export const PRODUCT_MAPPING: BaseProduct[] = [
  // ========================================================================
  // FAMILIA: BARRITAS
  // ========================================================================

  {
    id: 'BARRA_KETO_NUEZ',
    name: 'Barra Keto Nuez',
    family: 'Barritas',
    variants: [
      // Shopify
      { sku: 'BAKC_U04010', channel: 'shopify', format: '1un', formatDescription: '1 unidad' },
      { sku: 'BAKC_U20010', channel: 'shopify', format: '5un', formatDescription: 'Display 5 unidades' },
      { sku: 'BAKC_U64010', channel: 'shopify', format: '16un', formatDescription: 'Display 16 unidades' },
      { sku: 'PACKBAKC_U20010', channel: 'shopify', format: '5un-pack4', formatDescription: 'Pack 4 Display x5' },

      // MercadoLibre
      { sku: 'MLC2929973548', channel: 'mercadolibre', format: '16un', formatDescription: 'Display 16 unidades' },
      { sku: 'ML-MLC2929973548', channel: 'mercadolibre', format: '16un', formatDescription: 'Display 16 unidades (duplicado)' },
      { sku: 'MLC2930199094', channel: 'mercadolibre', format: '5un', formatDescription: 'Display 5 unidades' },
      { sku: 'ML-MLC2930199094', channel: 'mercadolibre', format: '5un', formatDescription: 'Display 5 unidades (duplicado)' },
    ]
  },

  {
    id: 'BARRA_LOW_CARB_BERRIES',
    name: 'Barra Low Carb Berries',
    family: 'Barritas',
    variants: [
      // Shopify
      { sku: 'BABE_U04010', channel: 'shopify', format: '1un', formatDescription: '1 barrita' },
      { sku: 'BABE_U20010', channel: 'shopify', format: '5un', formatDescription: 'Display 5 barras' },
      { sku: 'PACKBABE_U20010', channel: 'shopify', format: '5un-pack4', formatDescription: 'Pack 4 Display x5' },

      // MercadoLibre
      { sku: 'MLC1630337051', channel: 'mercadolibre', format: '5un', formatDescription: 'Display 5 unidades' },
    ]
  },

  {
    id: 'BARRA_LOW_CARB_CACAO_MANI',
    name: 'Barra Low Carb Cacao Maní',
    family: 'Barritas',
    variants: [
      // Shopify
      { sku: 'BACM_U04010', channel: 'shopify', format: '1un', formatDescription: '1 unidad' },
      { sku: 'BACM_U20010', channel: 'shopify', format: '5un', formatDescription: 'Display 5 unidades' },
      { sku: 'BACM_U64010', channel: 'shopify', format: '16un', formatDescription: 'Display 16 unidades' },
      { sku: 'PACKBACM_U20010', channel: 'shopify', format: '5un-pack4', formatDescription: 'Pack 4 Display x5' },

      // MercadoLibre
      { sku: 'MLC1630349929', channel: 'mercadolibre', format: '5un', formatDescription: 'Display 5 unidades' },
      { sku: 'ML-MLC1630349929', channel: 'mercadolibre', format: '5un', formatDescription: 'Display 5 unidades (duplicado)' },
      { sku: 'MLC2978631042', channel: 'mercadolibre', format: '5un', formatDescription: 'Display 5 unidades' },
      { sku: 'ML-MLC2978631042', channel: 'mercadolibre', format: '5un', formatDescription: 'Display 5 unidades (duplicado)' },
      { sku: 'ML-MLC1630414337', channel: 'mercadolibre', format: '5un', formatDescription: 'Display 5 unidades' },
    ]
  },

  {
    id: 'BARRA_LOW_CARB_MANZANA_CANELA',
    name: 'Barra Low Carb Manzana Canela',
    family: 'Barritas',
    variants: [
      // Shopify
      { sku: 'BAMC_U04010', channel: 'shopify', format: '1un', formatDescription: '1 unidad' },
      { sku: 'BAMC_U20010', channel: 'shopify', format: '5un', formatDescription: 'Display 5 unidades' },
      { sku: 'BAMC_U64010', channel: 'shopify', format: '16un', formatDescription: 'Display 16 unidades' },
      { sku: 'PACKBAMC_U20010', channel: 'shopify', format: '5un-pack4', formatDescription: 'Pack 4 Display x5' },

      // MercadoLibre
      { sku: 'ML-MLC1630337053', channel: 'mercadolibre', format: '16un', formatDescription: 'Display 16 unidades' },
      { sku: 'MLC1630416135', channel: 'mercadolibre', format: '5un', formatDescription: 'Display 5 unidades' },
      { sku: 'ML-MLC2938290826', channel: 'mercadolibre', format: '5un', formatDescription: 'Display 5 unidades (duplicado)' },
      { sku: 'ML-MLC1630416135', channel: 'mercadolibre', format: '5un', formatDescription: 'Display 5 unidades (duplicado)' },
    ]
  },

  {
    id: 'BARRITA_CHIA',
    name: 'Barrita de Chía',
    family: 'Barritas',
    variants: [
      { sku: 'BAR-CHIA-001', channel: 'manual', format: '1un', formatDescription: '1 unidad' },
    ]
  },

  {
    id: 'BARRITA_QUINOA',
    name: 'Barrita de Quinoa',
    family: 'Barritas',
    variants: [
      { sku: 'BAR-QUINOA-001', channel: 'manual', format: '1un', formatDescription: '1 unidad' },
    ]
  },

  {
    id: 'PACK_BARRAS_SURTIDAS',
    name: 'Pack Barras Surtidas',
    family: 'Barritas',
    variants: [
      { sku: 'PACKBASURTIDA', channel: 'shopify', format: 'surtido-4pack', formatDescription: 'Pack 4 Barras Surtidas x5' },
    ]
  },

  // ========================================================================
  // FAMILIA: GRANOLAS
  // ========================================================================

  {
    id: 'GRANOLA_KETO_NUEZ',
    name: 'Granola Keto Nuez',
    family: 'Granolas',
    variants: [
      // Shopify
      { sku: 'GRKC_U21010', channel: 'shopify', format: '210g', formatDescription: '210 gramos' },
      { sku: 'PACKGRKC_U21010', channel: 'shopify', format: '210g-pack4', formatDescription: 'Pack 4 x 210g' },
    ]
  },

  {
    id: 'GRANOLA_LOW_CARB_ALMENDRAS',
    name: 'Granola Low Carb Almendras',
    family: 'Granolas',
    variants: [
      // Shopify
      { sku: 'GRAL_U26010', channel: 'shopify', format: '260g', formatDescription: '260 gramos' },
      { sku: 'PACKGRAL_U26010', channel: 'shopify', format: '260g-pack4', formatDescription: 'Pack 4 x 260g' },

      // MercadoLibre
      { sku: 'ML-MLC2967399930', channel: 'mercadolibre', format: '260g', formatDescription: '260 gramos' },
      { sku: 'ML-MLC3029455396', channel: 'mercadolibre', format: '260g', formatDescription: '260 gramos (duplicado)' },
    ]
  },

  {
    id: 'GRANOLA_LOW_CARB_BERRIES',
    name: 'Granola Low Carb Berries',
    family: 'Granolas',
    variants: [
      // Shopify
      { sku: 'GRBE_U26010', channel: 'shopify', format: '260g', formatDescription: '260 gramos' },
      { sku: 'PACKGRBE_U26010', channel: 'shopify', format: '260g-pack4', formatDescription: 'Pack 4 x 260g' },

      // MercadoLibre
      { sku: 'ML-MLC2978641268', channel: 'mercadolibre', format: '260g', formatDescription: '260 gramos' },
      { sku: 'ML-MLC2966323128', channel: 'mercadolibre', format: '260g', formatDescription: '260 gramos (duplicado)' },
      { sku: 'MLC2978641268', channel: 'mercadolibre', format: '260g', formatDescription: '260 gramos (duplicado)' },
    ]
  },

  {
    id: 'GRANOLA_LOW_CARB_CACAO',
    name: 'Granola Low Carb Cacao',
    family: 'Granolas',
    variants: [
      // Shopify
      { sku: 'GRCA_U26010', channel: 'shopify', format: '260g', formatDescription: '260 gramos' },
      { sku: 'PACKGRCA_U26010', channel: 'shopify', format: '260g-pack4', formatDescription: 'Pack 4 x 260g' },

      // MercadoLibre
      { sku: 'MLC2930070644', channel: 'mercadolibre', format: '260g', formatDescription: '260 gramos' },
      { sku: 'MLC1630349931', channel: 'mercadolibre', format: '260g', formatDescription: '260 gramos' },
      { sku: 'MLC1644022833', channel: 'mercadolibre', format: '260g', formatDescription: '260 gramos' },
    ]
  },

  {
    id: 'GRANOLA_GENERICA',
    name: 'Granola Genérica',
    family: 'Granolas',
    variants: [
      { sku: 'GRA-250-001', channel: 'manual', format: '250g', formatDescription: '250 gramos' },
      { sku: 'GRA-500-001', channel: 'manual', format: '500g', formatDescription: '500 gramos' },
    ]
  },

  {
    id: 'PACK_GRANOLAS_SURTIDAS',
    name: 'Pack Granolas Surtidas',
    family: 'Granolas',
    variants: [
      { sku: 'PACKGRSURTIDA', channel: 'shopify', format: 'surtido-4pack', formatDescription: 'Pack 4 Granolas Surtidas' },
    ]
  },

  // ========================================================================
  // FAMILIA: CRACKERS
  // ========================================================================

  {
    id: 'CRACKERS_KETO_SAL_MAR',
    name: 'Crackers Keto Sal de Mar',
    family: 'Crackers',
    variants: [
      // Shopify
      { sku: 'CRSM_U13510', channel: 'shopify', format: '135g', formatDescription: 'Display 135 gramos' },
      { sku: 'CRSM_U02510', channel: 'shopify', format: '25g', formatDescription: 'Sachet individual 25g' },
      { sku: 'CRSM_U02520', channel: 'shopify', format: '25g', formatDescription: 'Individual 25g' },
      { sku: 'CRSM_U25010', channel: 'shopify', format: '25g', formatDescription: 'Individual 25g' },
      { sku: 'CRSM_U25020', channel: 'shopify', format: '25g-10pack', formatDescription: 'Display 10 sachets x25g' },
      { sku: 'PACKCRSM_U13510', channel: 'shopify', format: '135g-pack4', formatDescription: 'Pack 4 x 135g' },
      { sku: 'PACKCRSM_U25020', channel: 'shopify', format: '25g-10pack-pack4', formatDescription: 'Pack 4 Display 10 sachets' },

      // MercadoLibre
      { sku: 'MLC2930215860', channel: 'mercadolibre', format: '120g', formatDescription: '120 gramos' },
      { sku: 'ML-MLC2930215860', channel: 'mercadolibre', format: '120g', formatDescription: '120 gramos (duplicado)' },
    ]
  },

  {
    id: 'CRACKERS_KETO_ROMERO',
    name: 'Crackers Keto Romero',
    family: 'Crackers',
    variants: [
      // Shopify
      { sku: 'CRRO_U13510', channel: 'shopify', format: '135g', formatDescription: '135 gramos' },
      { sku: 'PACKCRRO_U13510', channel: 'shopify', format: '135g-pack4', formatDescription: 'Pack 4 x 135g' },

      // MercadoLibre
      { sku: 'ML-MLC2930238714', channel: 'mercadolibre', format: '135g', formatDescription: '135 gramos' },
      { sku: 'MLC2930238714', channel: 'mercadolibre', format: '135g', formatDescription: '135 gramos (duplicado)' },
      { sku: 'ML-MLC2933751572', channel: 'mercadolibre', format: '135g', formatDescription: '135 gramos' },
      { sku: 'MLC2933751572', channel: 'mercadolibre', format: '135g', formatDescription: '135 gramos (duplicado)' },
    ]
  },

  {
    id: 'CRACKERS_KETO_AJO_ALBAHACA',
    name: 'Crackers Keto Ajo Albahaca',
    family: 'Crackers',
    variants: [
      // Shopify
      { sku: 'CRAA_U13510', channel: 'shopify', format: '135g', formatDescription: '135 gramos' },
      { sku: 'PACKCRAA_U13510', channel: 'shopify', format: '135g-pack4', formatDescription: 'Pack 4 x 135g' },

      // MercadoLibre
      { sku: 'MLC2930200766', channel: 'mercadolibre', format: '135g', formatDescription: '135 gramos' },
      { sku: 'ML-MLC2930200766', channel: 'mercadolibre', format: '135g', formatDescription: '135 gramos (duplicado)' },
    ]
  },

  {
    id: 'CRACKERS_KETO_PIMIENTA',
    name: 'Crackers Keto Pimienta',
    family: 'Crackers',
    variants: [
      // Shopify
      { sku: 'CRPM_U13510', channel: 'shopify', format: '135g', formatDescription: '135 gramos' },
      { sku: 'PACKCRPM_U13510', channel: 'shopify', format: '135g-pack5', formatDescription: 'Pack 5 x 135g' },

      // MercadoLibre
      { sku: 'MLC1630369169', channel: 'mercadolibre', format: '135g', formatDescription: '135 gramos' },
      { sku: 'ML-MLC1630369169', channel: 'mercadolibre', format: '135g', formatDescription: '135 gramos (duplicado)' },
    ]
  },

  {
    id: 'CRACKERS_KETO_CURCUMA',
    name: 'Crackers Keto Cúrcuma',
    family: 'Crackers',
    variants: [
      { sku: 'CRCU_U13510', channel: 'shopify', format: '135g', formatDescription: '135 gramos' },
    ]
  },

  {
    id: 'PACK_CRACKERS_SURTIDOS',
    name: 'Pack Crackers Surtidos',
    family: 'Crackers',
    variants: [
      { sku: 'PACKCRSURTIDO', channel: 'shopify', format: 'surtido-4pack', formatDescription: 'Pack 4 Crackers Surtidos' },
    ]
  },

  // ========================================================================
  // FAMILIA: KEEPER
  // ========================================================================

  {
    id: 'KEEPER_CHOCOLATE_MANI',
    name: 'Keeper Chocolate Maní',
    family: 'Keeper',
    variants: [
      // Shopify
      { sku: 'KSMC_U03010', channel: 'shopify', format: '1un', formatDescription: '1 unidad 30g' },
      { sku: 'KSMC_U15010', channel: 'shopify', format: '5un', formatDescription: 'Display 5 unidades' },
      { sku: 'KSMC_U54010', channel: 'shopify', format: '18un', formatDescription: 'Display 18 unidades' },
      { sku: 'PACKKSMC_U15010', channel: 'shopify', format: '5un-pack4', formatDescription: 'Pack 4 Display x5' },
      { sku: 'PACKKSMC_U54010', channel: 'shopify', format: '18un-pack2', formatDescription: 'Pack 2 Display x18' },
      { sku: 'KEEPER_PIONEROS', channel: 'shopify', format: '10un-special', formatDescription: 'Pack x10 Edición Pioneros' },

      // MercadoLibre
      { sku: 'MLC2930251054', channel: 'mercadolibre', format: '30g', formatDescription: '30 gramos' },
      { sku: 'MLC3016921654', channel: 'mercadolibre', format: '30g', formatDescription: '30 gramos (duplicado)' },
    ]
  },
];

/**
 * Función helper para buscar producto base por SKU
 */
export function findBaseProductBySku(sku: string): BaseProduct | null {
  for (const baseProduct of PRODUCT_MAPPING) {
    const variant = baseProduct.variants.find(v => v.sku === sku);
    if (variant) {
      return baseProduct;
    }
  }
  return null;
}

/**
 * Función helper para obtener todos los SKUs de un producto base
 */
export function getAllSkusForBaseProduct(baseProductId: string): string[] {
  const baseProduct = PRODUCT_MAPPING.find(p => p.id === baseProductId);
  return baseProduct ? baseProduct.variants.map(v => v.sku) : [];
}

/**
 * Función helper para agrupar ventas por producto base
 */
export interface SalesData {
  sku: string;
  quantity: number;
  revenue: number;
}

export interface AggregatedSales {
  baseProduct: BaseProduct;
  totalQuantity: number;
  totalRevenue: number;
  byFormat: Record<string, { quantity: number; revenue: number }>;
  byChannel: Record<string, { quantity: number; revenue: number }>;
}

export function aggregateSalesByBaseProduct(sales: SalesData[]): AggregatedSales[] {
  const aggregated = new Map<string, AggregatedSales>();

  for (const sale of sales) {
    const baseProduct = findBaseProductBySku(sale.sku);
    if (!baseProduct) continue;

    const variant = baseProduct.variants.find(v => v.sku === sale.sku);
    if (!variant) continue;

    if (!aggregated.has(baseProduct.id)) {
      aggregated.set(baseProduct.id, {
        baseProduct,
        totalQuantity: 0,
        totalRevenue: 0,
        byFormat: {},
        byChannel: {},
      });
    }

    const agg = aggregated.get(baseProduct.id)!;
    agg.totalQuantity += sale.quantity;
    agg.totalRevenue += sale.revenue;

    // Agregar por formato
    if (!agg.byFormat[variant.format]) {
      agg.byFormat[variant.format] = { quantity: 0, revenue: 0 };
    }
    agg.byFormat[variant.format].quantity += sale.quantity;
    agg.byFormat[variant.format].revenue += sale.revenue;

    // Agregar por canal
    if (!agg.byChannel[variant.channel]) {
      agg.byChannel[variant.channel] = { quantity: 0, revenue: 0 };
    }
    agg.byChannel[variant.channel].quantity += sale.quantity;
    agg.byChannel[variant.channel].revenue += sale.revenue;
  }

  return Array.from(aggregated.values());
}

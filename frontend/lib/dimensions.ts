export const DIMENSIONS = {
  category: { key: 'category', label: 'Familia', dbField: 'mv.category' },
  channel: { key: 'channel', label: 'Canal', dbField: 'mv.channel_name' },
  customer: { key: 'customer', label: 'Cliente', dbField: 'mv.customer_name' },
  format: { key: 'format', label: 'Formato', dbField: 'mv.package_type' },
  sku_primario: { key: 'sku_primario', label: 'SKU Primario', dbField: 'mv.sku_primario' },
} as const

export type DimensionKey = keyof typeof DIMENSIONS

export function getDimensionLabel(key: string): string {
  return DIMENSIONS[key as DimensionKey]?.label ?? key
}

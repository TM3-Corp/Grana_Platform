import Fuse from 'fuse.js'

export interface SearchableProduct {
  id: number
  sku: string
  name: string
  category: string | null
  brand: string | null
  source: string
}

// Configuración optimizada para productos Grana multi-canal
export const fuseOptions: Fuse.IFuseOptions<SearchableProduct> = {
  // Campos donde buscar con pesos diferentes
  keys: [
    {
      name: 'name',
      weight: 0.7  // Nombre es más importante
    },
    {
      name: 'sku',
      weight: 0.2
    },
    {
      name: 'category',
      weight: 0.05
    },
    {
      name: 'brand',
      weight: 0.05
    }
  ],

  // Configuración de fuzzy matching
  // 0.5 es más tolerante para variaciones cross-channel (Shopify vs ML vs Manual)
  threshold: 0.5,

  // Máxima distancia para considerar match
  // 150 para nombres más largos de MercadoLibre
  distance: 150,

  // Mínimo 2 caracteres para empezar a buscar
  minMatchCharLength: 2,

  // Incluir score de relevancia para ordenar resultados
  includeScore: true,

  // Incluir qué partes hicieron match (para highlights)
  includeMatches: true,

  // CRÍTICO: Ignora dónde está el match en el string
  // Permite que "Display 5" esté al inicio o al final
  ignoreLocation: true,

  // Encuentra todos los matches posibles
  findAllMatches: true,

  // Deshabilitar búsqueda extendida para simplificar
  useExtendedSearch: false
}

// Normalización de términos para español
export const normalizeSearchTerm = (term: string): string => {
  return term
    .toLowerCase()
    .normalize('NFD')  // Descompone caracteres acentuados
    .replace(/[\u0300-\u036f]/g, '')  // Elimina acentos
    .trim()
}

// Normalización agresiva para matching cross-channel
// Esta función estandariza variaciones comunes entre canales
export const normalizeForMatching = (name: string): string => {
  return name
    .toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    // Estandarizar "barra" vs "barrita" vs "barritas"
    .replace(/\b(barritas?|barras?)\b/g, 'barra')
    // Estandarizar unidades de empaque
    .replace(/\b(display|disp|dis)\b/g, 'display')
    .replace(/\b(unidades|uds|un|u)\b/g, 'unidad')
    // Eliminar conectores comunes
    .replace(/\b(con|x|de)\b/g, ' ')
    // Estandarizar pesos
    .replace(/\b(grs|gr|gramos|g)\b/g, 'gr')
    // Normalizar "vegana" vs "vegan"
    .replace(/\b(vegana|vegan)\b/g, 'vegana')
    // Limpiar espacios múltiples
    .replace(/\s+/g, ' ')
    .trim()
}

// Sinónimos y variaciones comunes para búsqueda
export const termVariations: Record<string, string[]> = {
  // Variaciones de "barra" (muy común en productos Grana)
  'barra': ['barra', 'barras', 'barrita', 'barritas', 'bar'],
  'barrita': ['barra', 'barras', 'barrita', 'barritas'],
  'barras': ['barra', 'barras', 'barrita', 'barritas'],
  'barritas': ['barra', 'barras', 'barrita', 'barritas'],

  // Typos comunes de "keto"
  'keto': ['keto', 'queto', 'ceto', 'ketto'],
  'queto': ['keto', 'queto'],
  'ceto': ['keto', 'ceto'],

  // Singular/plural de ingredientes
  'nuez': ['nuez', 'nueces'],
  'nueces': ['nuez', 'nueces'],
  'berry': ['berry', 'berries'],
  'berries': ['berry', 'berries'],
  'galleta': ['galleta', 'galletas'],
  'galletas': ['galleta', 'galletas'],
  'cracker': ['cracker', 'crackers'],
  'crackers': ['cracker', 'crackers'],

  // Variaciones de categorías
  'lowcarb': ['low carb', 'lowcarb', 'low-carb'],
  'low carb': ['low carb', 'lowcarb', 'low-carb'],
  'low-carb': ['low carb', 'lowcarb', 'low-carb'],

  // Variaciones de unidades (cross-channel)
  'display': ['display', 'disp', 'dis'],
  'unidades': ['unidades', 'uds', 'un', 'u'],
  'uds': ['unidades', 'uds', 'un'],
  'un': ['unidades', 'uds', 'un'],

  // Términos específicos por canal
  'vegana': ['vegana', 'vegan'],
  'vegan': ['vegana', 'vegan'],

  // Sabores comunes
  'mani': ['maní', 'mani'],
  'maní': ['maní', 'mani'],
  'cacao': ['cacao', 'chocolate'],
  'chocolate': ['cacao', 'chocolate']
}

// Categorías detectables en el texto de búsqueda
export const categoryKeywords: Record<string, string> = {
  'keto': 'Keto',
  'low carb': 'Low Carb',
  'lowcarb': 'Low Carb',
  'low-carb': 'Low Carb',
  'crackers': 'Crackers',
  'cracker': 'Crackers',
  'granola': 'Granola',
  'galletas': 'Crackers',
  'galleta': 'Crackers',
  'barra': 'Barra',
  'barrita': 'Barritas',
  'barritas': 'Barritas'
}

// Configuración de badges por fuente (multi-canal)
export interface SourceBadge {
  icon: string
  color: string
  label: string
}

export const getSourceBadge = (source: string): SourceBadge => {
  const badges: Record<string, SourceBadge> = {
    'shopify': {
      icon: '🛍️',
      color: 'bg-green-100 text-green-800',
      label: 'Shopify'
    },
    'mercadolibre': {
      icon: '🛒',
      color: 'bg-yellow-100 text-yellow-800',
      label: 'ML'
    },
    'manual': {
      icon: '✏️',
      color: 'bg-gray-100 text-gray-800',
      label: 'Manual'
    }
  }

  return badges[source] || badges['manual']
}

// Detectar si dos productos son potencialmente el mismo (para futura reconciliación)
export const areProductsSimilar = (name1: string, name2: string): boolean => {
  const normalized1 = normalizeForMatching(name1)
  const normalized2 = normalizeForMatching(name2)

  const words1 = new Set(normalized1.split(/\s+/).filter(w => w.length > 2))
  const words2 = new Set(normalized2.split(/\s+/).filter(w => w.length > 2))

  // Calcular intersección de palabras clave
  const intersection = new Set([...words1].filter(w => words2.has(w)))

  // Si comparten 70%+ de palabras clave, son similares
  const similarity = intersection.size / Math.min(words1.size, words2.size)

  return similarity >= 0.7
}

// Términos comunes a ignorar en comparaciones
export const stopWords = new Set([
  'de', 'del', 'la', 'el', 'los', 'las',
  'con', 'sin', 'para', 'por', 'en',
  'y', 'o', 'un', 'una', 'unos', 'unas'
])

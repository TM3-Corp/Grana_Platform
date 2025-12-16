/**
 * Utility functions for the Grana Platform frontend
 */

/**
 * Combines class names, filtering out falsy values
 * A simple alternative to clsx/classnames libraries
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ')
}

/**
 * Format a number as Chilean currency (abbreviated)
 */
export function formatCurrency(value: number): string {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`
  } else if (value >= 1000) {
    return `$${Math.round(value / 1000)}K`
  } else {
    return `$${value.toLocaleString('es-CL')}`
  }
}

/**
 * Format a number as Chilean currency with full thousand separators
 * Example: 430234567 -> "$430.234.567"
 */
export function formatCurrencyFull(value: number): string {
  return `$${Math.round(value).toLocaleString('es-CL')}`
}

/**
 * Format a number with Chilean locale
 */
export function formatNumber(value: number): string {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`
  } else if (value >= 1000) {
    return `${Math.round(value / 1000)}K`
  } else {
    return value.toLocaleString('es-CL')
  }
}

/**
 * Debounce a function
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}

/**
 * Convert text to Title Case
 * "CENCOSUD RETAIL S.A." -> "Cencosud Retail S.A."
 * Preserves acronyms like S.A., LTDA., etc.
 */
export function toTitleCase(str: string | null | undefined): string {
  if (!str) return ''

  // List of words that should stay uppercase (acronyms)
  const acronyms = ['S.A.', 'S.A', 'SA', 'LTDA', 'LTDA.', 'SPA', 'S.P.A.', 'CIA', 'CIA.', 'E.I.R.L', 'EIRL']

  return str
    .toLowerCase()
    .split(' ')
    .map(word => {
      // Check if this word (uppercase) is an acronym
      const upperWord = word.toUpperCase()
      if (acronyms.includes(upperWord)) {
        return upperWord
      }
      // Capitalize first letter
      return word.charAt(0).toUpperCase() + word.slice(1)
    })
    .join(' ')
}

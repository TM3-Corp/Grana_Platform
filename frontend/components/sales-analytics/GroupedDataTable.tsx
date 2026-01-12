'use client'

interface GroupedDataRow {
  group_value: string
  revenue: number
  units: number
  orders: number
  avg_ticket: number
}

interface PaginationInfo {
  current_page: number
  total_pages: number
  total_items: number
  page_size: number
}

interface GroupedDataTableProps {
  data: GroupedDataRow[] | null
  groupBy: string | null
  pagination: PaginationInfo | null
  onPageChange?: (page: number) => void
  onExportCSV?: () => void
  loading?: boolean
}

export default function GroupedDataTable({
  data,
  groupBy,
  pagination,
  onPageChange,
  onExportCSV,
  loading
}: GroupedDataTableProps) {
  // Helper functions - defined at the top to avoid hoisting issues
  const getGroupLabel = (group: string): string => {
    const labels: Record<string, string> = {
      category: 'Familia',
      channel: 'Canal',
      customer: 'Cliente',
      format: 'Formato',
      sku_primario: 'SKU Primario'
    }
    return labels[group] || 'Categoría'
  }

  const formatCurrency = (value: number): string => {
    return `$${Math.round(value).toLocaleString('es-CL')}`
  }

  const formatNumber = (value: number): string => {
    return Math.round(value).toLocaleString('es-CL')
  }

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-lg p-6">
        <div className="h-96 bg-gray-200 animate-pulse rounded-lg" />
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-2xl shadow-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          📊 Datos Agrupados
        </h2>
        <div className="flex items-center justify-center h-64 text-gray-500">
          No hay datos disponibles
        </div>
      </div>
    )
  }

  const handlePreviousPage = () => {
    if (pagination && pagination.current_page > 1 && onPageChange) {
      onPageChange(pagination.current_page - 1)
    }
  }

  const handleNextPage = () => {
    if (pagination && pagination.current_page < pagination.total_pages && onPageChange) {
      onPageChange(pagination.current_page + 1)
    }
  }

  const handlePageClick = (page: number) => {
    if (onPageChange) {
      onPageChange(page)
    }
  }

  // Generate page numbers to display
  const getPageNumbers = (): number[] => {
    if (!pagination) return []

    const { current_page, total_pages } = pagination
    const pages: number[] = []

    // Always show first page
    pages.push(1)

    // Show pages around current page
    const rangeStart = Math.max(2, current_page - 1)
    const rangeEnd = Math.min(total_pages - 1, current_page + 1)

    // Add ellipsis if needed
    if (rangeStart > 2) {
      pages.push(-1) // -1 represents ellipsis
    }

    // Add middle pages
    for (let i = rangeStart; i <= rangeEnd; i++) {
      pages.push(i)
    }

    // Add ellipsis if needed
    if (rangeEnd < total_pages - 1) {
      pages.push(-2) // -2 represents ellipsis
    }

    // Always show last page
    if (total_pages > 1) {
      pages.push(total_pages)
    }

    return pages
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg hover:shadow-xl transition-shadow duration-300 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-1">
            📊 Datos Agrupados
          </h2>
          <p className="text-sm text-gray-600">
            Agrupado por: <span className="font-medium text-gray-900">{groupBy ? getGroupLabel(groupBy) : 'Familia'}</span>
          </p>
        </div>

        {onExportCSV && (
          <button
            onClick={onExportCSV}
            className="
              px-4 py-2 bg-green-500 text-white rounded-lg
              hover:bg-green-600 transition-colors
              flex items-center gap-2 text-sm font-medium
            "
          >
            <span>📥</span>
            Exportar Excel
          </button>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b-2 border-gray-200">
              <th className="text-left py-3 px-4 font-semibold text-gray-700">
                {groupBy ? getGroupLabel(groupBy) : 'Categoría'}
              </th>
              <th className="text-right py-3 px-4 font-semibold text-gray-700">
                Ingresos
              </th>
              <th className="text-right py-3 px-4 font-semibold text-gray-700">
                Unidades
              </th>
              <th className="text-right py-3 px-4 font-semibold text-gray-700">
                Órdenes
              </th>
              <th className="text-right py-3 px-4 font-semibold text-gray-700">
                Ticket Prom.
              </th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, index) => (
              <tr
                key={index}
                className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
              >
                <td className="py-3 px-4 text-gray-900 font-medium">
                  {row.group_value || 'Sin clasificar'}
                </td>
                <td className="py-3 px-4 text-right text-gray-900 font-medium">
                  {formatCurrency(row.revenue)}
                </td>
                <td className="py-3 px-4 text-right text-gray-700">
                  {formatNumber(row.units)}
                </td>
                <td className="py-3 px-4 text-right text-gray-700">
                  {formatNumber(row.orders)}
                </td>
                <td className="py-3 px-4 text-right text-gray-700">
                  {formatCurrency(row.avg_ticket)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination && pagination.total_pages > 1 && (
        <div className="flex items-center justify-between mt-6 pt-6 border-t border-gray-200">
          {/* Info */}
          <div className="text-sm text-gray-600">
            Mostrando página <span className="font-medium text-gray-900">{pagination.current_page}</span> de{' '}
            <span className="font-medium text-gray-900">{pagination.total_pages}</span>
            {' '}({pagination.total_items} items totales)
          </div>

          {/* Controls */}
          <div className="flex items-center gap-2">
            {/* Previous button */}
            <button
              onClick={handlePreviousPage}
              disabled={pagination.current_page === 1}
              className={`
                px-3 py-1 rounded-lg text-sm font-medium transition-colors
                ${pagination.current_page === 1
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                }
              `}
            >
              ← Anterior
            </button>

            {/* Page numbers */}
            {getPageNumbers().map((page, index) => {
              if (page < 0) {
                // Ellipsis
                return (
                  <span key={`ellipsis-${index}`} className="px-2 text-gray-400">
                    ...
                  </span>
                )
              }

              return (
                <button
                  key={page}
                  onClick={() => handlePageClick(page)}
                  className={`
                    px-3 py-1 rounded-lg text-sm font-medium transition-colors
                    ${page === pagination.current_page
                      ? 'bg-green-500 text-white'
                      : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                    }
                  `}
                >
                  {page}
                </button>
              )
            })}

            {/* Next button */}
            <button
              onClick={handleNextPage}
              disabled={pagination.current_page === pagination.total_pages}
              className={`
                px-3 py-1 rounded-lg text-sm font-medium transition-colors
                ${pagination.current_page === pagination.total_pages
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                }
              `}
            >
              Siguiente →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

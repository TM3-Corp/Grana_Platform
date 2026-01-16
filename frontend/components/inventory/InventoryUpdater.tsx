'use client';

import React, { useState } from 'react';

interface PreviewData {
  status: string;
  filename: string;
  total_rows: number;
  columns: {
    sku: string;
    descripcion: string;
    cantidad: string;
  };
  rows: Array<{
    sku: string;
    descripcion: string;
    cantidad: number;
  }>;
  message?: string;
}

export default function InventoryUpdater() {
  const [uploading, setUploading] = useState(false);
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      alert('Por favor selecciona un archivo Excel (.xlsx o .xls)');
      return;
    }

    try {
      setUploading(true);
      setPreviewData(null);

      const formData = new FormData();
      formData.append('file', file);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://granaplatform-production.up.railway.app';
      const response = await fetch(`${apiUrl}/api/v1/inventory/preview`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'Error al procesar el archivo');
      }

      setPreviewData(data);

    } catch (error) {
      console.error('Error uploading file:', error);
      alert('Error al procesar el archivo. Por favor verifica el formato y vuelve a intentar.');
    } finally {
      setUploading(false);
      // Reset file input
      event.target.value = '';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white p-6 rounded-lg shadow-lg">
        <h2 className="text-3xl font-bold mb-2">📄 Vista Previa de Inventario</h2>
        <p className="text-blue-100">
          Carga un archivo Excel para ver su contenido antes de actualizar
        </p>
      </div>

      {/* Instructions Card */}
      <div className="bg-white border border-gray-300 rounded-lg p-6 shadow">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">📋 Instrucciones</h3>
        <div className="space-y-4">
          <p className="text-gray-700">
            El archivo Excel debe contener las siguientes columnas:
          </p>
          <div className="bg-gray-50 p-4 rounded-lg">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-300">
                  <th className="text-left py-2 px-3 text-gray-700">Columna</th>
                  <th className="text-left py-2 px-3 text-gray-700">Descripción</th>
                  <th className="text-left py-2 px-3 text-gray-700">Ejemplo</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-gray-200">
                  <td className="py-2 px-3 font-mono">Artículo / SKU</td>
                  <td className="py-2 px-3">Código del producto</td>
                  <td className="py-2 px-3 font-mono text-blue-600">BAKC_U04010</td>
                </tr>
                <tr className="border-b border-gray-200">
                  <td className="py-2 px-3 font-mono">Descripción</td>
                  <td className="py-2 px-3">Nombre del producto</td>
                  <td className="py-2 px-3">BARRA KETO NUEZ X1</td>
                </tr>
                <tr>
                  <td className="py-2 px-3 font-mono">Cantidad</td>
                  <td className="py-2 px-3">Stock en bodega</td>
                  <td className="py-2 px-3 font-mono text-green-600">198</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <p className="text-sm text-yellow-800">
              ⚠️ <strong>Modo Preview:</strong> El archivo solo se leerá y mostrará en pantalla.
              NO se actualizará la base de datos hasta que Macarena defina el proceso exacto.
            </p>
          </div>
        </div>
      </div>

      {/* Upload Section */}
      <div className="bg-white border-2 border-blue-300 rounded-lg p-8 shadow-lg">
        <div className="flex flex-col items-center gap-6">
          <div className="text-center">
            <div className="text-6xl mb-4">📤</div>
            <h3 className="text-2xl font-semibold text-gray-900 mb-2">Cargar Archivo Excel</h3>
            <p className="text-gray-600 mb-6">
              Sube tu archivo WMS o Excel de inventario para ver su contenido
            </p>
          </div>

          <label
            className={`px-8 py-4 rounded-lg font-semibold text-lg transition-all cursor-pointer flex items-center justify-center min-w-[300px] ${
              uploading
                ? 'bg-gray-300 text-gray-500'
                : 'bg-blue-500 text-white hover:bg-blue-600 shadow-md hover:shadow-lg'
            }`}
          >
            {uploading ? (
              <span className="flex items-center gap-3">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
                Leyendo archivo...
              </span>
            ) : (
              '📤 Seleccionar Archivo Excel'
            )}
            <input
              type="file"
              accept=".xlsx,.xls"
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>

          <p className="text-sm text-gray-500">
            Formatos aceptados: .xlsx, .xls
          </p>
        </div>
      </div>

      {/* Preview Display */}
      {previewData && previewData.status === 'success' && (
        <div className="bg-white border border-gray-300 rounded-lg p-6 shadow-lg">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-2xl font-semibold text-gray-900 flex items-center gap-2">
              <span>📄</span> Contenido del Archivo Excel
            </h3>
            <button
              onClick={() => setPreviewData(null)}
              className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg text-gray-700 font-medium"
            >
              ✕ Cerrar
            </button>
          </div>

          {/* File Info */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <div className="text-sm text-blue-600 font-medium">Archivo</div>
                <div className="text-blue-900 font-semibold">{previewData.filename}</div>
              </div>
              <div>
                <div className="text-sm text-blue-600 font-medium">Total de Filas</div>
                <div className="text-2xl text-blue-900 font-bold">{previewData.total_rows}</div>
              </div>
              <div>
                <div className="text-sm text-blue-600 font-medium">Columnas Detectadas</div>
                <div className="text-xs text-blue-700 space-y-1 mt-1">
                  <div>SKU: <span className="font-mono">{previewData.columns.sku}</span></div>
                  <div>Descripción: <span className="font-mono">{previewData.columns.descripcion}</span></div>
                  <div>Cantidad: <span className="font-mono">{previewData.columns.cantidad}</span></div>
                </div>
              </div>
            </div>
          </div>

          {/* Data Table */}
          <div className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="max-h-[600px] overflow-y-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">#</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">SKU</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">Descripción</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-600 uppercase tracking-wider">Cantidad</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {previewData.rows.map((row, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm text-gray-500">{idx + 1}</td>
                      <td className="px-4 py-3 text-sm font-mono text-gray-900">{row.sku}</td>
                      <td className="px-4 py-3 text-sm text-gray-900">{row.descripcion || '-'}</td>
                      <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900">{row.cantidad.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Footer Note */}
          <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              💡 <strong>Nota:</strong> Esta es solo una vista previa. Los datos NO han sido guardados en la base de datos.
              Cuando Macarena defina el proceso, se implementará la funcionalidad de actualización.
            </p>
          </div>
        </div>
      )}

      {previewData && previewData.status === 'error' && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-xl font-semibold text-red-900 mb-3">❌ Error al Leer el Archivo</h3>
          <p className="text-red-700">{previewData.message}</p>
        </div>
      )}
    </div>
  );
}

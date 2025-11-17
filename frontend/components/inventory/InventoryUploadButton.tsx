'use client';

import { useState, useRef } from 'react';

interface InventoryUploadButtonProps {
  warehouseCode: string;
  warehouseName: string;
  onUploadSuccess: () => void;
}

export default function InventoryUploadButton({
  warehouseCode,
  warehouseName,
  onUploadSuccess,
}: InventoryUploadButtonProps) {
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<{
    status: 'success' | 'error';
    message: string;
    details?: any;
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      setUploadResult({
        status: 'error',
        message: 'Por favor selecciona un archivo Excel (.xlsx o .xls)',
      });
      return;
    }

    setUploading(true);
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(
        `http://localhost:8000/api/v1/warehouse-inventory/upload?warehouse_code=${warehouseCode}`,
        {
          method: 'POST',
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Error al subir el archivo');
      }

      setUploadResult({
        status: 'success',
        message: `✅ Inventario actualizado: ${data.products_updated} productos actualizados${
          data.products_not_found > 0 ? `, ${data.products_not_found} no encontrados` : ''
        }`,
        details: data,
      });

      // Call success callback to refresh data
      setTimeout(() => {
        onUploadSuccess();
      }, 1500);
    } catch (error: any) {
      setUploadResult({
        status: 'error',
        message: error.message || 'Error al subir el archivo',
      });
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="flex flex-col gap-2">
      {/* Upload Button */}
      <button
        onClick={handleClick}
        disabled={uploading}
        className={`
          flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all duration-300
          ${
            uploading
              ? 'bg-gray-300 text-gray-600 cursor-not-allowed'
              : 'bg-gradient-to-r from-green-500 to-green-600 text-white hover:from-green-600 hover:to-green-700 shadow-sm hover:shadow-md'
          }
        `}
      >
        {uploading ? (
          <>
            <svg
              className="w-4 h-4 animate-spin"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            <span>Subiendo...</span>
          </>
        ) : (
          <>
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
            <span>Subir Excel</span>
          </>
        )}
      </button>

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx,.xls"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Upload Result */}
      {uploadResult && (
        <div
          className={`
            p-3 rounded-lg text-sm border-l-4 ${
              uploadResult.status === 'success'
                ? 'bg-green-50 border-green-500 text-green-800'
                : 'bg-red-50 border-red-500 text-red-800'
            }
          `}
        >
          <p className="font-medium">{uploadResult.message}</p>
          {uploadResult.details && uploadResult.details.products_not_found > 0 && (
            <button
              onClick={() => {
                console.log('Products not found:', uploadResult.details.details);
                alert(
                  'SKUs no encontrados:\n' +
                    uploadResult.details.details
                      .filter((d: any) => d.status === 'not_found')
                      .map((d: any) => d.sku)
                      .join(', ')
                );
              }}
              className="text-xs underline mt-1 hover:text-green-900"
            >
              Ver productos no encontrados
            </button>
          )}
        </div>
      )}

      {/* Info */}
      <p className="text-xs text-gray-500 mt-1">
        Formato esperado:{' '}
        <span className="font-mono">
          {warehouseCode.startsWith('amplifica')
            ? 'SKU, Nombre, Stock Disponible'
            : 'Articulo, Descripción, Cantidad'}
        </span>
      </p>
    </div>
  );
}

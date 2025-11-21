'use client';

import { useState, useRef } from 'react';

interface InventoryUploadButtonProps {
  warehouseCode: string;
  warehouseName?: string;
  onUploadSuccess?: () => void;
}

export default function InventoryUploadButton({ warehouseCode, warehouseName, onUploadSuccess }: InventoryUploadButtonProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<{
    type: 'success' | 'error' | null;
    message: string;
    details?: any;
  }>({ type: null, message: '' });
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file type
    const fileName = file.name.toLowerCase();
    if (!fileName.endsWith('.xlsx') && !fileName.endsWith('.xls')) {
      setUploadStatus({
        type: 'error',
        message: 'Por favor selecciona un archivo Excel (.xlsx o .xls)'
      });
      return;
    }

    setIsUploading(true);
    setUploadStatus({ type: null, message: '' });

    try {
      const formData = new FormData();
      formData.append('file', file);

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(
        `${apiUrl}/api/v1/warehouse-inventory/upload?warehouse_code=${warehouseCode}`,
        {
          method: 'POST',
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Error al subir el archivo');
      }

      // Success
      setUploadStatus({
        type: 'success',
        message: `✅ Inventario actualizado exitosamente`,
        details: {
          productos_actualizados: data.products_updated,
          productos_no_encontrados: data.products_not_found,
        }
      });

      // Call success callback
      if (onUploadSuccess) {
        setTimeout(() => {
          onUploadSuccess();
        }, 1500);
      }

    } catch (error: any) {
      setUploadStatus({
        type: 'error',
        message: error.message || 'Error al subir el archivo'
      });
    } finally {
      setIsUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="flex flex-col gap-2">
      <input
        ref={fileInputRef}
        type="file"
        accept=".xlsx,.xls"
        onChange={handleFileSelect}
        className="hidden"
      />

      <button
        onClick={handleButtonClick}
        disabled={isUploading || !warehouseCode}
        className={`
          px-4 py-2 rounded-lg font-medium transition-all
          ${isUploading || !warehouseCode
            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
            : 'bg-blue-600 hover:bg-blue-700 text-white hover:shadow-lg'
          }
        `}
      >
        {isUploading ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Subiendo...
          </span>
        ) : (
          <span className="flex items-center gap-2">
            📤 Subir Excel
          </span>
        )}
      </button>

      {/* Status messages */}
      {uploadStatus.type && (
        <div className={`
          p-3 rounded-lg text-sm
          ${uploadStatus.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : ''}
          ${uploadStatus.type === 'error' ? 'bg-red-50 text-red-800 border border-red-200' : ''}
        `}>
          <p className="font-medium">{uploadStatus.message}</p>
          {uploadStatus.details && (
            <div className="mt-2 text-xs space-y-1">
              <p>✅ Productos actualizados: {uploadStatus.details.productos_actualizados}</p>
              {uploadStatus.details.productos_no_encontrados > 0 && (
                <p>⚠️ Productos no encontrados: {uploadStatus.details.productos_no_encontrados}</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Help text */}
      {!uploadStatus.type && (
        <p className="text-xs text-gray-500">
          Formato: Excel con columnas [SKU, Nombre, Stock Disponible]
        </p>
      )}
    </div>
  );
}

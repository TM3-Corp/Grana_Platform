'use client';

import React from 'react';
import Navigation from '@/components/Navigation';
import StatsCards from './components/StatsCards';
import TopProductsChart from './components/TopProductsChart';
import MappingsTable from './components/MappingsTable';

export default function RelbaseMappingPage() {
  return (
    <>
      <Navigation />
      <div className="min-h-screen bg-gray-50 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Auditoría de Mapeo Relbase
            </h1>
            <p className="text-gray-600">
              Visualización y validación de mapeos de productos Relbase 2025
            </p>
          </div>

          {/* Info Banner */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <div className="flex items-start gap-3">
              <span className="text-2xl">📊</span>
              <div>
                <h3 className="font-semibold text-blue-900 mb-1">
                  Sistema de Auditoría de Mapeos
                </h3>
                <p className="text-sm text-blue-700 mb-2">
                  Este dashboard permite visualizar y auditar todos los productos fetched de Relbase,
                  entender su volumen de ventas, y validar la precisión de los mapeos al catálogo oficial.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-xs text-blue-600 mt-2">
                  <div>
                    <span className="font-semibold">Periodo:</span> Enero - Octubre 2025
                  </div>
                  <div>
                    <span className="font-semibold">Documentos:</span> 5,274 (facturas + boletas)
                  </div>
                  <div>
                    <span className="font-semibold">Line Items:</span> 11,595 productos vendidos
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Stats Cards */}
          <StatsCards />

          {/* Top Products Chart */}
          <TopProductsChart />

          {/* Mappings Table */}
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Tabla Completa de Mapeos
            </h2>
            <MappingsTable />
          </div>

          {/* Key Insights */}
          <div className="bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">💡 Insights Clave</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <h4 className="font-semibold text-purple-900 mb-2">Alta Prioridad para Mapeo:</h4>
                <ul className="space-y-1 text-gray-700">
                  <li>• ANU-3322808180 (706 ventas) - MIX GRANA CLÁSICO</li>
                  <li>• ANU-3322808177 (594 ventas) - MIX GRANA CACAO</li>
                  <li>• ANU-4322808039 (430 ventas) - MIX GRANA BERRIES</li>
                  <li>• KEEPER_PIONEROS (278 ventas) - Edición especial</li>
                </ul>
              </div>
              <div>
                <h4 className="font-semibold text-green-900 mb-2">Productos Bien Mapeados:</h4>
                <ul className="space-y-1 text-gray-700">
                  <li>• BAKC_U20010 (242 ventas) - ✅ 100% confianza</li>
                  <li>• BABE_U20010 (230 ventas) - ✅ 100% confianza</li>
                  <li>• CRRO_U13510 (223 ventas) - ✅ 100% confianza</li>
                  <li>• KSMC_U03010 (187 ventas) - ✅ 100% confianza</li>
                </ul>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-purple-200">
              <p className="text-sm text-gray-700">
                <span className="font-semibold">Próximo paso:</span> Implementar fuzzy matching por nombre
                para mapear los códigos ANU- legacy (puede agregar +50-55% de cobertura → ~80% total).
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Navigation from '@/components/Navigation';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Product {
  id: number;
  sku: string;
  product_name: string;
  sku_master: string | null;
  master_box_name: string | null;
  category: string | null;
  brand: string | null;
  language: string | null;
  package_type: string | null;
  units_per_display: number | null;
  units_per_master_box: number | null;
  items_per_master_box: number | null;
  is_master_sku: boolean | null;
  base_code: string | null;
  sku_primario: string | null;
  peso_film: number | null;
  peso_display_total: number | null;
  peso_caja_master_total: number | null;
  peso_etiqueta_total: number | null;
  sku_value: number | null;
  sku_master_value: number | null;
  is_active: boolean | null;
  is_inventory_active: boolean | null;
  created_at: string | null;
  updated_at: string | null;
}

interface Stats {
  total_products: number;
  active_products: number;
  inactive_products: number;
  inventory_active: number;
  total_categories: number;
  has_master_box: number;
  category_breakdown: { category: string; count: number }[];
}

const emptyProduct: Partial<Product> = {
  sku: '',
  product_name: '',
  sku_master: null,
  master_box_name: null,
  category: null,
  brand: 'GRANA',
  language: 'ES',
  package_type: null,
  units_per_display: 1,
  units_per_master_box: null,
  items_per_master_box: null,
  is_master_sku: false,
  base_code: null,
  sku_primario: null,
  peso_film: null,
  peso_display_total: null,
  peso_caja_master_total: null,
  peso_etiqueta_total: null,
  sku_value: null,
  sku_master_value: null,
  is_active: true,
  is_inventory_active: true,
};

export default function ProductCatalogPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(50);
  const [totalCount, setTotalCount] = useState(0);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [filterCategory, setFilterCategory] = useState<string>('');
  const [filterActive, setFilterActive] = useState<string>('');
  const [sortBy, setSortBy] = useState('sku');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [formData, setFormData] = useState<Partial<Product>>(emptyProduct);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Delete confirmation
  const [deleteConfirm, setDeleteConfirm] = useState<Product | null>(null);

  // Expanded view for product details
  const [expandedProductId, setExpandedProductId] = useState<number | null>(null);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setCurrentPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Fetch categories
  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/product-catalog/categories`);
      const data = await response.json();
      if (data.status === 'success') {
        setCategories(data.data);
      }
    } catch (err) {
      console.error('Error loading categories:', err);
    }
  };

  // Fetch stats
  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/product-catalog/stats`);
      const data = await response.json();
      if (data.status === 'success') {
        setStats(data.data);
      }
    } catch (err) {
      console.error('Error loading stats:', err);
    }
  };

  // Fetch products
  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: pageSize.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
      });

      if (debouncedSearch) {
        params.append('search', debouncedSearch);
      }
      if (filterCategory) {
        params.append('category', filterCategory);
      }
      if (filterActive) {
        params.append('is_active', filterActive);
      }

      const response = await fetch(`${API_URL}/api/v1/product-catalog/?${params}`);
      const data = await response.json();

      if (data.status === 'success') {
        setProducts(data.data);
        setTotalCount(data.meta.total);
      } else {
        setError(data.detail || 'Error loading products');
      }
    } catch (err) {
      setError('Failed to connect to API');
      console.error('Error loading products:', err);
    } finally {
      setLoading(false);
    }
  }, [currentPage, pageSize, debouncedSearch, filterCategory, filterActive, sortBy, sortOrder]);

  // Load data on mount and when filters change
  useEffect(() => {
    fetchCategories();
    fetchStats();
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  // Handle sort
  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
  };

  // Open modal for create/edit
  const openModal = (product?: Product) => {
    if (product) {
      setEditingProduct(product);
      setFormData(product);
    } else {
      setEditingProduct(null);
      setFormData(emptyProduct);
    }
    setSaveError(null);
    setIsModalOpen(true);
  };

  // Handle form input change
  const handleInputChange = (field: keyof Product, value: unknown) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  // Save product
  const handleSave = async () => {
    if (!formData.sku || !formData.product_name) {
      setSaveError('SKU and Product Name are required');
      return;
    }

    setIsSaving(true);
    setSaveError(null);

    try {
      const url = editingProduct
        ? `${API_URL}/api/v1/product-catalog/${editingProduct.id}`
        : `${API_URL}/api/v1/product-catalog/`;

      const method = editingProduct ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (response.ok && data.status === 'success') {
        setIsModalOpen(false);
        fetchProducts();
        fetchStats();
      } else {
        setSaveError(data.detail || 'Failed to save product');
      }
    } catch (err) {
      setSaveError('Failed to save product');
      console.error('Error saving product:', err);
    } finally {
      setIsSaving(false);
    }
  };

  // Delete product
  const handleDelete = async (product: Product) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/product-catalog/${product.id}`, {
        method: 'DELETE',
      });

      const data = await response.json();

      if (response.ok && data.status === 'success') {
        setDeleteConfirm(null);
        fetchProducts();
        fetchStats();
      } else {
        alert(data.detail || 'Failed to delete product');
      }
    } catch (err) {
      alert('Failed to delete product');
      console.error('Error deleting product:', err);
    }
  };

  // Toggle active status
  const handleToggleActive = async (product: Product) => {
    try {
      const response = await fetch(`${API_URL}/api/v1/product-catalog/${product.id}/toggle-active`, {
        method: 'POST',
      });

      const data = await response.json();

      if (response.ok && data.status === 'success') {
        fetchProducts();
        fetchStats();
      } else {
        alert(data.detail || 'Failed to toggle status');
      }
    } catch (err) {
      alert('Failed to toggle status');
      console.error('Error toggling status:', err);
    }
  };

  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Product Catalog</h1>
            <p className="text-gray-600 mt-1">Manage products in the catalog database</p>
          </div>
          <button
            onClick={() => openModal()}
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 flex items-center gap-2"
          >
            <span className="text-lg">+</span>
            Add Product
          </button>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-2xl font-bold text-blue-600">{stats.total_products}</div>
              <div className="text-sm text-gray-600">Total Products</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-2xl font-bold text-green-600">{stats.active_products}</div>
              <div className="text-sm text-gray-600">Active</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-2xl font-bold text-red-600">{stats.inactive_products}</div>
              <div className="text-sm text-gray-600">Inactive</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-2xl font-bold text-purple-600">{stats.total_categories}</div>
              <div className="text-sm text-gray-600">Categories</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-2xl font-bold text-orange-600">{stats.has_master_box}</div>
              <div className="text-sm text-gray-600">With Master Box</div>
            </div>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="text-2xl font-bold text-teal-600">{stats.inventory_active}</div>
              <div className="text-sm text-gray-600">Inventory Active</div>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-lg shadow p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-center">
            <div className="flex-1 min-w-[200px]">
              <input
                type="text"
                placeholder="Search SKU, name, or SKU primario..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full border rounded-lg px-3 py-2"
              />
            </div>
            <select
              value={filterCategory}
              onChange={(e) => { setFilterCategory(e.target.value); setCurrentPage(1); }}
              className="border rounded-lg px-3 py-2"
            >
              <option value="">All Categories</option>
              {categories.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
            <select
              value={filterActive}
              onChange={(e) => { setFilterActive(e.target.value); setCurrentPage(1); }}
              className="border rounded-lg px-3 py-2"
            >
              <option value="">All Status</option>
              <option value="true">Active</option>
              <option value="false">Inactive</option>
            </select>
            <div className="text-sm text-gray-500">
              {totalCount} products
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-700">
            {error}
          </div>
        )}

        {/* Products Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('sku')}
                  >
                    SKU {sortBy === 'sku' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('product_name')}
                  >
                    Product Name {sortBy === 'product_name' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th
                    className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                    onClick={() => handleSort('category')}
                  >
                    Category {sortBy === 'category' && (sortOrder === 'asc' ? '↑' : '↓')}
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                    SKU Primario
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Units/Display
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Master Box
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Active
                  </th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                      Loading...
                    </td>
                  </tr>
                ) : products.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                      No products found
                    </td>
                  </tr>
                ) : (
                  products.map(product => (
                    <React.Fragment key={product.id}>
                      <tr
                        className={`hover:bg-gray-50 ${expandedProductId === product.id ? 'bg-blue-50' : ''}`}
                      >
                        <td className="px-4 py-3">
                          <button
                            onClick={() => setExpandedProductId(expandedProductId === product.id ? null : product.id)}
                            className="font-mono text-sm text-blue-600 hover:underline"
                          >
                            {product.sku}
                          </button>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-900 max-w-xs truncate">
                          {product.product_name}
                        </td>
                        <td className="px-4 py-3">
                          {product.category && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                              {product.category}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 font-mono text-xs text-gray-600">
                          {product.sku_primario || '-'}
                        </td>
                        <td className="px-4 py-3 text-center text-sm">
                          {product.units_per_display || 1}
                        </td>
                        <td className="px-4 py-3 text-center">
                          {product.sku_master ? (
                            <span className="text-xs text-purple-600">{product.sku_master}</span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-center">
                          <button
                            onClick={() => handleToggleActive(product)}
                            className={`w-10 h-5 rounded-full transition-colors ${
                              product.is_active ? 'bg-green-500' : 'bg-gray-300'
                            }`}
                          >
                            <span
                              className={`block w-4 h-4 bg-white rounded-full shadow transform transition-transform ${
                                product.is_active ? 'translate-x-5' : 'translate-x-0.5'
                              }`}
                            />
                          </button>
                        </td>
                        <td className="px-4 py-3 text-center">
                          <div className="flex justify-center gap-2">
                            <button
                              onClick={() => openModal(product)}
                              className="text-blue-600 hover:text-blue-800 text-sm"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => setDeleteConfirm(product)}
                              className="text-red-600 hover:text-red-800 text-sm"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                      {/* Expanded details row */}
                      {expandedProductId === product.id && (
                        <tr className="bg-blue-50">
                          <td colSpan={8} className="px-4 py-4">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                              <div>
                                <span className="text-gray-500">Brand:</span>{' '}
                                <span className="font-medium">{product.brand || '-'}</span>
                              </div>
                              <div>
                                <span className="text-gray-500">Language:</span>{' '}
                                <span className="font-medium">{product.language || '-'}</span>
                              </div>
                              <div>
                                <span className="text-gray-500">Package Type:</span>{' '}
                                <span className="font-medium">{product.package_type || '-'}</span>
                              </div>
                              <div>
                                <span className="text-gray-500">Base Code:</span>{' '}
                                <span className="font-medium font-mono">{product.base_code || '-'}</span>
                              </div>
                              <div>
                                <span className="text-gray-500">Units/Master Box:</span>{' '}
                                <span className="font-medium">{product.units_per_master_box || '-'}</span>
                              </div>
                              <div>
                                <span className="text-gray-500">Items/Master Box:</span>{' '}
                                <span className="font-medium">{product.items_per_master_box || '-'}</span>
                              </div>
                              <div>
                                <span className="text-gray-500">Display Weight:</span>{' '}
                                <span className="font-medium">{product.peso_display_total ? `${product.peso_display_total} kg` : '-'}</span>
                              </div>
                              <div>
                                <span className="text-gray-500">Master Box Weight:</span>{' '}
                                <span className="font-medium">{product.peso_caja_master_total ? `${product.peso_caja_master_total} kg` : '-'}</span>
                              </div>
                              <div>
                                <span className="text-gray-500">SKU Value:</span>{' '}
                                <span className="font-medium">{product.sku_value ? `$${product.sku_value.toLocaleString()}` : '-'}</span>
                              </div>
                              <div>
                                <span className="text-gray-500">Master Value:</span>{' '}
                                <span className="font-medium">{product.sku_master_value ? `$${product.sku_master_value.toLocaleString()}` : '-'}</span>
                              </div>
                              <div>
                                <span className="text-gray-500">Inventory Active:</span>{' '}
                                <span className={`font-medium ${product.is_inventory_active ? 'text-green-600' : 'text-red-600'}`}>
                                  {product.is_inventory_active ? 'Yes' : 'No'}
                                </span>
                              </div>
                              <div>
                                <span className="text-gray-500">Is Master SKU:</span>{' '}
                                <span className="font-medium">{product.is_master_sku ? 'Yes' : 'No'}</span>
                              </div>
                              {product.master_box_name && (
                                <div className="col-span-2">
                                  <span className="text-gray-500">Master Box Name:</span>{' '}
                                  <span className="font-medium">{product.master_box_name}</span>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="px-4 py-3 border-t flex items-center justify-between">
              <div className="text-sm text-gray-500">
                Page {currentPage} of {totalPages}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setCurrentPage(1)}
                  disabled={currentPage === 1}
                  className="px-3 py-1 border rounded disabled:opacity-50"
                >
                  First
                </button>
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1 border rounded disabled:opacity-50"
                >
                  Prev
                </button>
                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1 border rounded disabled:opacity-50"
                >
                  Next
                </button>
                <button
                  onClick={() => setCurrentPage(totalPages)}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1 border rounded disabled:opacity-50"
                >
                  Last
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Create/Edit Modal */}
        {isModalOpen && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
              <div className="p-6">
                <h2 className="text-xl font-bold mb-4">
                  {editingProduct ? 'Edit Product' : 'Add New Product'}
                </h2>

                {saveError && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4 text-red-700 text-sm">
                    {saveError}
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Required fields */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      SKU <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.sku || ''}
                      onChange={(e) => handleInputChange('sku', e.target.value.toUpperCase())}
                      className="w-full border rounded-lg px-3 py-2 font-mono"
                      placeholder="BAKC_U04010"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Product Name <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={formData.product_name || ''}
                      onChange={(e) => handleInputChange('product_name', e.target.value)}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder="Barra Keto Nuez - 1 unidad"
                    />
                  </div>

                  {/* Category and Brand */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
                    <select
                      value={formData.category || ''}
                      onChange={(e) => handleInputChange('category', e.target.value || null)}
                      className="w-full border rounded-lg px-3 py-2"
                    >
                      <option value="">Select category...</option>
                      {categories.map(cat => (
                        <option key={cat} value={cat}>{cat}</option>
                      ))}
                      <option value="__new__">+ Add new category</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Brand</label>
                    <input
                      type="text"
                      value={formData.brand || ''}
                      onChange={(e) => handleInputChange('brand', e.target.value || null)}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder="GRANA"
                    />
                  </div>

                  {/* SKU Primario and Base Code */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">SKU Primario</label>
                    <input
                      type="text"
                      value={formData.sku_primario || ''}
                      onChange={(e) => handleInputChange('sku_primario', e.target.value.toUpperCase() || null)}
                      className="w-full border rounded-lg px-3 py-2 font-mono"
                      placeholder="BAKC_U04010"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Base Code</label>
                    <input
                      type="text"
                      value={formData.base_code || ''}
                      onChange={(e) => handleInputChange('base_code', e.target.value.toUpperCase() || null)}
                      className="w-full border rounded-lg px-3 py-2 font-mono"
                      placeholder="BAKC"
                    />
                  </div>

                  {/* Conversion factors */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Units per Display</label>
                    <input
                      type="number"
                      min="1"
                      value={formData.units_per_display || ''}
                      onChange={(e) => handleInputChange('units_per_display', e.target.value ? parseInt(e.target.value) : null)}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder="1"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Package Type</label>
                    <input
                      type="text"
                      value={formData.package_type || ''}
                      onChange={(e) => handleInputChange('package_type', e.target.value || null)}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder="1U, 5U, 16U, etc."
                    />
                  </div>

                  {/* Master box fields */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Master Box SKU</label>
                    <input
                      type="text"
                      value={formData.sku_master || ''}
                      onChange={(e) => handleInputChange('sku_master', e.target.value.toUpperCase() || null)}
                      className="w-full border rounded-lg px-3 py-2 font-mono"
                      placeholder="BAKC_C02810"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Master Box Name</label>
                    <input
                      type="text"
                      value={formData.master_box_name || ''}
                      onChange={(e) => handleInputChange('master_box_name', e.target.value || null)}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder="Caja Master Barra Keto Nuez"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Units per Master Box</label>
                    <input
                      type="number"
                      min="1"
                      value={formData.units_per_master_box || ''}
                      onChange={(e) => handleInputChange('units_per_master_box', e.target.value ? parseInt(e.target.value) : null)}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder="28"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Items per Master Box</label>
                    <input
                      type="number"
                      min="1"
                      value={formData.items_per_master_box || ''}
                      onChange={(e) => handleInputChange('items_per_master_box', e.target.value ? parseInt(e.target.value) : null)}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder="140"
                    />
                  </div>

                  {/* Weight fields */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Display Weight (kg)</label>
                    <input
                      type="number"
                      step="0.0001"
                      min="0"
                      value={formData.peso_display_total || ''}
                      onChange={(e) => handleInputChange('peso_display_total', e.target.value ? parseFloat(e.target.value) : null)}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder="0.0189"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Master Box Weight (kg)</label>
                    <input
                      type="number"
                      step="0.001"
                      min="0"
                      value={formData.peso_caja_master_total || ''}
                      onChange={(e) => handleInputChange('peso_caja_master_total', e.target.value ? parseFloat(e.target.value) : null)}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder="0.5292"
                    />
                  </div>

                  {/* Value fields */}
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">SKU Value (CLP)</label>
                    <input
                      type="number"
                      min="0"
                      value={formData.sku_value || ''}
                      onChange={(e) => handleInputChange('sku_value', e.target.value ? parseFloat(e.target.value) : null)}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder="640"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Master Value (CLP)</label>
                    <input
                      type="number"
                      min="0"
                      value={formData.sku_master_value || ''}
                      onChange={(e) => handleInputChange('sku_master_value', e.target.value ? parseFloat(e.target.value) : null)}
                      className="w-full border rounded-lg px-3 py-2"
                      placeholder="17920"
                    />
                  </div>

                  {/* Toggles */}
                  <div className="flex items-center gap-4">
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={formData.is_active ?? true}
                        onChange={(e) => handleInputChange('is_active', e.target.checked)}
                        className="w-4 h-4"
                      />
                      <span className="text-sm">Active</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={formData.is_inventory_active ?? true}
                        onChange={(e) => handleInputChange('is_inventory_active', e.target.checked)}
                        className="w-4 h-4"
                      />
                      <span className="text-sm">Show in Inventory</span>
                    </label>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={formData.is_master_sku ?? false}
                        onChange={(e) => handleInputChange('is_master_sku', e.target.checked)}
                        className="w-4 h-4"
                      />
                      <span className="text-sm">Is Master SKU</span>
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Language</label>
                    <select
                      value={formData.language || 'ES'}
                      onChange={(e) => handleInputChange('language', e.target.value)}
                      className="w-full border rounded-lg px-3 py-2"
                    >
                      <option value="ES">Spanish (ES)</option>
                      <option value="EN">English (EN)</option>
                    </select>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
                  <button
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                    disabled={isSaving}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={isSaving}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {isSaving ? 'Saving...' : (editingProduct ? 'Update' : 'Create')}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {deleteConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <h3 className="text-lg font-bold text-red-600 mb-2">Delete Product</h3>
              <p className="text-gray-600 mb-4">
                Are you sure you want to delete <strong>{deleteConfirm.sku}</strong>?
                This action cannot be undone.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDelete(deleteConfirm)}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

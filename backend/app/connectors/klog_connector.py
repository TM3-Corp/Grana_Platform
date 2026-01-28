"""
KLOG/INVAS API Connector
Handles inventory/warehouse management integration

Author: Claude Code
Date: 2025-01-22
Updated: 2025-01-22 - Fixed authentication pattern

API CONFIGURATION:
- Base URL: https://kwlinvas.impruvex.com
- Base Path: /api/invas/rest

AUTHENTICATION (IMPORTANT):
- Login: POST /api/invas/rest/usuario/loginWS
  - Body: {"usuario": "...", "password": "..."}
  - Returns: {"token": "..."}

- Data queries require BOTH:
  1. Bearer token in Authorization header
  2. usuario + password in request body

WORKING ENDPOINTS (confirmed 2025-01-22):
- POST /WmsResumenInventario/consultaInventarioSkuActivo - Active inventory
- POST /producto/consultar - Product query (requires SKU code)
- POST /oc/consultaOrdenDeCompra - Purchase orders (requires sitio code)
- POST /asn/consultaAsnws - ASN query (requires sitio code)

NON-WORKING ENDPOINTS:
- /dm/invas/rest/* - Requires special API permissions (web-only account)
- /WmsResumenInventario/consultaInventarioSku - "ENDPOINT NO DISPONIBLE"

See: docs/klog_api_discovery.md for full discovery process
"""
import os
from typing import Dict, Optional, Any
import httpx
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class KLOGConnector:
    """
    Connector for KLOG/INVAS API (warehouse management system)

    Handles:
    - Authentication (JWT-based)
    - Inventory queries
    - Stock consultation
    """

    BASE_URL = "https://kwlinvas.impruvex.com"
    API_BASE_PATH = "/api/invas/rest"  # For login and data endpoints
    WMS_BASE_PATH = "/dm/invas/rest"   # For WMS endpoints (requires special permissions)
    LOGIN_PATH = "/api/invas/rest/usuario/loginWS"
    DEFAULT_SITIO = "1KW BOD 7 LAMPA"  # Grana warehouse site code

    def __init__(self, usuario: str = None, password: str = None):
        """
        Initialize KLOG connector

        Args:
            usuario: KLOG username (not email!)
            password: KLOG user password
        """
        self.usuario = usuario or os.getenv('KLOG_USUARIO')
        self.password = password or os.getenv('KLOG_PASSWORD')
        self._token: Optional[str] = None
        self._user: Optional[Dict] = None
        self._token_expires: Optional[datetime] = None

        if not self.usuario or not self.password:
            raise ValueError(
                "KLOG credentials not configured. "
                "Set KLOG_USUARIO and KLOG_PASSWORD environment variables"
            )

    @property
    def _headers(self) -> Dict[str, str]:
        """Get headers with authentication token"""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    async def _login(self) -> bool:
        """
        Authenticate with KLOG API

        Returns:
            True if login successful
        """
        url = f"{self.BASE_URL}{self.LOGIN_PATH}"
        payload = {
            "usuario": self.usuario,  # Note: field is "usuario", not "email"
            "password": self.password
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()

                self._token = data.get("token")
                self._user = data.get("user")

                if self._token:
                    logger.info(f"KLOG login successful for user: {self._user}")
                    return True
                else:
                    logger.error("KLOG login response missing token")
                    return False

            except httpx.HTTPStatusError as e:
                logger.error(f"KLOG login failed: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"KLOG login error: {e}")
                raise

    async def _ensure_authenticated(self):
        """Ensure we have a valid authentication token"""
        if not self._token:
            await self._login()

    def _get_auth_payload(self, extra_data: Dict = None) -> Dict:
        """
        Get payload with authentication credentials.

        IMPORTANT: INVAS API requires usuario+password in the request body
        for data queries, not just Bearer token in headers.
        """
        payload = {
            "usuario": self.usuario,
            "password": self.password
        }
        if extra_data:
            payload.update(extra_data)
        return payload

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        payload: Dict = None,
        params: Dict = None,
        include_auth_in_body: bool = True
    ) -> Dict:
        """
        Make an authenticated API request

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (will be prefixed with /api/invas/rest)
            payload: Request body for POST/PUT
            params: Query parameters
            include_auth_in_body: Include usuario/password in body (default True)

        Returns:
            Response data as dict
        """
        await self._ensure_authenticated()

        # All API endpoints use /api/invas/rest base path
        url = f"{self.BASE_URL}{self.API_BASE_PATH}{endpoint}"

        # IMPORTANT: Include credentials in body for data queries
        if include_auth_in_body:
            request_payload = self._get_auth_payload(payload)
        else:
            request_payload = payload

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    json=request_payload,
                    params=params,
                    headers=self._headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"KLOG API error: {e.response.status_code} - {e.response.text}")
                # If 401, try to re-authenticate and retry once
                if e.response.status_code == 401 and self._token:
                    logger.info("Token expired, attempting re-authentication...")
                    self._token = None
                    await self._ensure_authenticated()
                    # Retry the request
                    response = await client.request(
                        method=method,
                        url=url,
                        json=request_payload,
                        params=params,
                        headers=self._headers,
                        timeout=30.0
                    )
                    response.raise_for_status()
                    return response.json()
                raise
            except Exception as e:
                logger.error(f"KLOG request error: {e}")
                raise

    async def _make_wms_request(
        self,
        method: str,
        endpoint: str,
        payload: Dict = None,
        params: Dict = None
    ) -> Dict:
        """
        Make an authenticated WMS API request (uses /dm/invas/rest base path)

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (will be prefixed with /dm/invas/rest)
            payload: Request body for POST/PUT
            params: Query parameters

        Returns:
            Response data as dict
        """
        await self._ensure_authenticated()

        # WMS endpoints use /dm/invas/rest base path
        url = f"{self.BASE_URL}{self.WMS_BASE_PATH}{endpoint}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    json=payload,
                    params=params,
                    headers=self._headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                logger.error(f"KLOG WMS API error: {e.response.status_code} - {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"KLOG WMS request error: {e}")
                raise

    # ==========================================
    # Working Endpoints (confirmed 2025-01-22)
    # ==========================================

    # KLOG API has a batch size limit - more than 6 SKUs returns registros=None
    BATCH_SIZE_LIMIT = 6

    async def get_active_inventory(
        self,
        sku_list: list = None,
        sitio: str = None,
        page: int = 1,
        use_default_sitio: bool = False
    ) -> Dict:
        """
        Get inventory for specific SKUs (single batch, max 6 SKUs).

        IMPORTANT: This endpoint has quirks:
        - Max 6 SKUs per request (more returns registros=None)
        - Invalid SKUs in batch cause entire batch to fail
        - Empty sku_list only returns SKUs with totalDisponible > 0

        For querying many SKUs, use get_inventory_for_skus() instead.

        Args:
            sku_list: List of SKU dicts [{"sku": "..."}] - MAX 6!
            sitio: Optional site filter (e.g., "KW BOD 7 LAMPA")
            page: Page number for pagination
            use_default_sitio: If True and sitio not provided, use DEFAULT_SITIO

        Returns:
            Dict with:
            - registros: total count (None if error/invalid SKU)
            - listainvsku: array of inventory items
        """
        payload = {
            "listasku": sku_list or [],
            "page": page
        }

        effective_sitio = sitio or (self.DEFAULT_SITIO if use_default_sitio else None)
        if effective_sitio:
            payload["sitio"] = effective_sitio

        return await self._make_request(
            "POST",
            "/WmsResumenInventario/consultaInventarioSkuActivo",
            payload=payload
        )

    async def get_inventory_for_skus(
        self,
        skus: list[str],
        sitio: str = None,
        retry_failed: bool = True
    ) -> Dict:
        """
        Get inventory for a list of SKUs, handling batch limits and errors.

        This method:
        1. Splits SKUs into batches of 6 (API limit)
        2. If a batch fails (invalid SKU), retries each SKU individually
        3. Aggregates all results

        Args:
            skus: List of SKU codes (strings)
            sitio: Optional site filter
            retry_failed: If True, retry failed batches individually

        Returns:
            Dict with:
            - listainvsku: Combined inventory items from all batches
            - total_queried: Number of SKUs queried
            - failed_skus: List of SKUs that failed

        Example:
            result = await connector.get_inventory_for_skus(
                ["GRAL_U26010", "BABE_C02810", "BACM_U20010"]
            )
            for item in result['listainvsku']:
                print(f"{item['sku']}: {item['totalDisponible']} disponible")
        """
        all_results = []
        failed_skus = []

        # Process in batches of BATCH_SIZE_LIMIT
        for i in range(0, len(skus), self.BATCH_SIZE_LIMIT):
            batch = skus[i:i + self.BATCH_SIZE_LIMIT]
            sku_list = [{"sku": s} for s in batch]

            result = await self.get_active_inventory(sku_list, sitio=sitio)

            # Check if batch succeeded (registros is not None)
            if result.get('registros') is not None:
                all_results.extend(result.get('listainvsku', []))
            elif retry_failed:
                # Batch failed - retry each SKU individually to find the bad one
                for sku in batch:
                    single_result = await self.get_active_inventory(
                        [{"sku": sku}], sitio=sitio
                    )
                    if single_result.get('registros') is not None:
                        all_results.extend(single_result.get('listainvsku', []))
                    else:
                        failed_skus.append(sku)
            else:
                failed_skus.extend(batch)

        return {
            "listainvsku": all_results,
            "total_queried": len(skus),
            "found": len(all_results),
            "failed_skus": failed_skus
        }

    async def get_product(self, sku: str) -> Dict:
        """
        Query a specific product by SKU

        Args:
            sku: Product SKU code (REQUIRED)

        Returns:
            Product data or error if SKU not found
        """
        if not sku:
            return {"error": "204", "mensaje": "CAMPO SKU OBLIGATORIO"}

        return await self._make_request(
            "POST",
            "/producto/consultar",
            payload={"codigoSku": sku}
        )

    async def consulta_orden_compra(self, sitio: str, **kwargs) -> Dict:
        """
        Query purchase orders (Órdenes de Compra)

        Args:
            sitio: Site code (REQUIRED - get this from KLOG)
            **kwargs: Additional parameters (e.g., fechaDesde, fechaHasta)

        Returns:
            Purchase order data or error with "SITIO NO EXISTE" if sitio is invalid
        """
        payload = {"sitio": sitio, **kwargs}
        return await self._make_request("POST", "/oc/consultaOrdenDeCompra", payload=payload)

    async def consulta_asn(
        self,
        sitio: str,
        fecha_inicio: str = None,
        fecha_fin: str = None,
        **kwargs
    ) -> Dict:
        """
        Query ASN (Advanced Shipping Notices)

        Args:
            sitio: Site code (REQUIRED)
            fecha_inicio: Start date (YYYY-MM-DD)
            fecha_fin: End date (YYYY-MM-DD)

        Returns:
            ASN list or error if sitio invalid
        """
        payload = {"sitio": sitio, **kwargs}
        if fecha_inicio:
            payload["fechaInicio"] = fecha_inicio
        if fecha_fin:
            payload["fechaFin"] = fecha_fin

        return await self._make_request("POST", "/asn/consultaAsnws", payload=payload)

    async def consulta_usuario(self, sitio: str = None, lista_rut: list = None) -> Dict:
        """
        Query users

        Args:
            sitio: Site code
            lista_rut: List of RUT numbers to query

        Returns:
            User data or error if neither sitio nor lista_rut provided
        """
        payload = {}
        if sitio:
            payload["sitio"] = sitio
        if lista_rut:
            payload["listaRut"] = lista_rut

        if not payload:
            return {"error": "625", "mensaje": "Must provide sitio or listaRut"}

        return await self._make_request("POST", "/usuario/consultaUsuarioWS", payload=payload)

    async def upload_orden_compra(self, data: Dict) -> Dict:
        """
        Upload purchase order

        Args:
            data: Purchase order data (structure TBD - get from KLOG docs)

        Returns:
            Upload result
        """
        return await self._make_request("POST", "/oc/upload", payload=data)

    # ==========================================
    # WMS Inventory Endpoints (at /dm/invas/rest)
    # ==========================================
    # Note: These endpoints require API permissions from KLOG

    async def get_inventory_summary(
        self,
        page: int = 1,
        page_size: int = 100,
        sitio_select: Dict = None
    ) -> Dict:
        """
        Get inventory summary (WmsResumenInventario)

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            sitio_select: Site filter (e.g., {"nombresitio": "TODOS"})

        Returns:
            Dict with listaWmsResumenInventario array

        Note: Requires API permissions from KLOG
        """
        payload = {
            "pagination": {
                "pageNumber": page,
                "pageSize": page_size
            }
        }
        if sitio_select:
            payload["sitioSelect"] = sitio_select

        return await self._make_wms_request("POST", "/WmsResumenInventario/listar", payload=payload)

    async def get_sites(self) -> Dict:
        """
        Get list of sites

        Note: Requires API permissions from KLOG
        """
        return await self._make_wms_request("POST", "/sitio/listar", payload={})

    async def get_products(self) -> Dict:
        """
        Get list of products

        Note: Requires API permissions from KLOG
        """
        return await self._make_wms_request("POST", "/producto/listar", payload={})

    async def get_warehouses(self) -> Dict:
        """
        Get list of warehouses/locations

        Note: Requires API permissions from KLOG
        """
        return await self._make_wms_request("POST", "/WmsUbicacion/listar", payload={})

    # ==========================================
    # Connection Test & Discovery
    # ==========================================

    async def test_connection(self) -> Dict:
        """
        Test KLOG connection by attempting login

        Returns:
            Dict with connection status and user info
        """
        try:
            await self._login()
            return {
                "success": True,
                "user": self._user,
                "message": "Login successful"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Login failed"
            }

    async def discover_endpoints(self) -> Dict[str, Any]:
        """
        Attempt to discover available API endpoints

        This method tries common endpoint patterns to see what's available.
        Results can help identify the correct API structure.
        """
        await self._ensure_authenticated()

        results = {}
        # Common endpoint patterns to try
        endpoints_to_try = [
            ("GET", "/"),
            ("GET", "/inventario"),
            ("GET", "/inventario/consulta"),
            ("GET", "/stock"),
            ("POST", "/stock/consulta"),
            ("GET", "/bodegas"),
            ("GET", "/bodega"),
            ("GET", "/productos"),
            ("GET", "/producto"),
            ("GET", "/articulos"),
            ("GET", "/items"),
            ("GET", "/movimientos"),
            ("GET", "/help"),
            ("GET", "/swagger"),
            ("GET", "/docs"),
        ]

        async with httpx.AsyncClient() as client:
            for method, endpoint in endpoints_to_try:
                url = f"{self.BASE_URL}{self.API_BASE_PATH}{endpoint}"
                try:
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=self._headers,
                        timeout=10.0
                    )
                    results[endpoint] = {
                        "status": response.status_code,
                        "success": response.status_code < 400,
                        "response_preview": response.text[:200] if response.text else None
                    }
                except Exception as e:
                    results[endpoint] = {
                        "status": "error",
                        "success": False,
                        "error": str(e)
                    }

        return results

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
    DEFAULT_SITIO = "KW BOD 7 LAMPA"  # Grana warehouse site code (confirmed 2026-02-03)

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

    async def get_all_active_inventory(self, sitio: str = None) -> Dict:
        """
        Get ALL inventory with stock > 0 from KLOG.

        This is the preferred method for syncing. Instead of querying specific
        SKUs (which may not exist in KLOG), we let KLOG tell us what inventory
        it has. This eliminates:
        - Batch size limits (no need for batching)
        - Failed SKUs (only returns what exists)
        - Guessing which SKUs are in KLOG

        According to INVAS API docs (line 3167-3170):
        "Si solo se quieren obtener los registros de SKU con Inventario > 0
        unidades, se puede consultar la misma URL añadiendo la palabra
        'Activo' al final de la URL, con el mismo request."

        Args:
            sitio: Optional site filter (e.g., "KW BOD 7 LAMPA")

        Returns:
            Dict with:
            - listainvsku: All inventory items with stock > 0
            - registros: Total count
            - page: Pagination info

        Example:
            result = await connector.get_all_active_inventory()
            for item in result['listainvsku']:
                print(f"{item['sku']}: {item['totalDisponible']} disponible")
        """
        # Empty listasku = return ALL SKUs with inventory > 0
        return await self.get_active_inventory(sku_list=[], sitio=sitio)

    async def get_inventory_for_skus(
        self,
        skus: list[str],
        sitio: str = None,
        retry_failed: bool = True
    ) -> Dict:
        """
        Get inventory for a list of SKUs, handling batch limits and errors.

        NOTE: Prefer get_all_active_inventory() for syncing. This method is
        useful when you need inventory for specific SKUs only.

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

    # ==========================================
    # Lot/Expiration Inventory Endpoints
    # ==========================================
    # Box-level inventory with lot numbers and expiration dates

    async def get_inventory_by_lot(
        self,
        sitio: str = None,
        desde: str = None,
        hasta: str = None,
        empresa: str = None
    ) -> Dict:
        """
        Get box-level inventory with lot and expiration details.

        This endpoint returns LPN (License Plate Number) level data including:
        - lote: Lot/batch number
        - fechaVencimiento: Expiration date
        - unidadesDisponibles: Available units per LPN

        Args:
            sitio: Warehouse site code (defaults to DEFAULT_SITIO)
            desde: Start date for storage filter (YYYY-MM-DD), defaults to 2024-01-01
            hasta: End date for storage filter (YYYY-MM-DD), defaults to today
            empresa: Filter by company name (e.g., "GRANA")

        Returns:
            Dict with:
            - listaWmsCaja: List of box/LPN records with lot and expiration data

        Example response item:
            {
                "idLpn": "GRALPN0096",
                "sku": "BACM_U64010",
                "lote": "11489",
                "fechaVencimiento": "2026-11-13 09:00:00.0",
                "unidadesDisponibles": 2,
                "nombre": "BARRA LOW CARB CACAO MANÍ X16 DISPLAY",
                "empresa": "GRANA",
                "sitio": "KW BOD 7 LAMPA",
                "estado": "UBICADO",
                "ubicacion": "ESTANTERIA-FS-08-01-04"
            }
        """
        payload = {
            "sitio": sitio or self.DEFAULT_SITIO,
            "desde": desde or "2024-01-01",
            "hasta": hasta or datetime.now().strftime("%Y-%m-%d")
        }

        result = await self._make_request(
            "POST",
            "/wmscaja/consultaWmsCajaAlmacenadasWS",
            payload=payload
        )

        # Optionally filter by empresa (company)
        if empresa and result.get('listaWmsCaja'):
            result['listaWmsCaja'] = [
                box for box in result['listaWmsCaja']
                if box.get('empresa', '').upper() == empresa.upper()
            ]

        return result

    async def get_inventory_with_lots(
        self,
        sitio: str = None,
        empresa: str = "GRANA",
        include_zero_stock: bool = False
    ) -> list[Dict]:
        """
        Get inventory aggregated by SKU, lot, and expiration date.

        This method fetches box-level data and aggregates it into a useful format
        for inventory management and expiration tracking.

        Args:
            sitio: Warehouse site code (defaults to DEFAULT_SITIO)
            empresa: Filter by company name (defaults to "GRANA")
            include_zero_stock: Include records with 0 available units

        Returns:
            List of aggregated inventory records:
            [
                {
                    "sku": "BACM_U64010",
                    "lot_number": "11489",
                    "expiration_date": "2026-11-13",
                    "total_units": 50,
                    "lpn_count": 5,
                    "product_name": "BARRA LOW CARB CACAO MANÍ X16 DISPLAY",
                    "sitio": "KW BOD 7 LAMPA"
                },
                ...
            ]
        """
        raw = await self.get_inventory_by_lot(sitio=sitio, empresa=empresa)

        boxes = raw.get('listaWmsCaja', [])
        if not boxes:
            logger.warning(f"No boxes returned from KLOG for empresa={empresa}")
            return []

        # Aggregate by (sku, lote, fechaVencimiento)
        aggregated: Dict[tuple, Dict] = {}

        for box in boxes:
            sku = box.get('sku')
            lote = box.get('lote')
            fecha_venc = box.get('fechaVencimiento')
            units = float(box.get('unidadesDisponibles') or 0)

            # Skip zero-stock if not requested
            if not include_zero_stock and units <= 0:
                continue

            # Parse expiration date if present
            exp_date = None
            if fecha_venc:
                try:
                    # Format: "2026-11-13 09:00:00.0"
                    exp_date = fecha_venc.split(' ')[0]  # Just the date part
                except (ValueError, AttributeError):
                    exp_date = str(fecha_venc)

            key = (sku, lote, exp_date)

            if key not in aggregated:
                aggregated[key] = {
                    'sku': sku,
                    'lot_number': lote,
                    'expiration_date': exp_date,
                    'total_units': 0,
                    'lpn_count': 0,
                    'product_name': box.get('nombre'),
                    'sitio': box.get('sitio'),
                    'empresa': box.get('empresa')
                }

            aggregated[key]['total_units'] += units
            aggregated[key]['lpn_count'] += 1

        result = list(aggregated.values())

        # Sort by expiration date (soonest first), then by SKU
        def sort_key(x):
            exp = x.get('expiration_date') or '9999-99-99'
            return (exp, x.get('sku', ''))

        result.sort(key=sort_key)

        logger.info(
            f"KLOG lot inventory: {len(result)} unique SKU/lot combinations "
            f"from {len(boxes)} boxes"
        )

        return result

    async def get_expiring_inventory(
        self,
        days_threshold: int = 90,
        sitio: str = None,
        empresa: str = "GRANA"
    ) -> list[Dict]:
        """
        Get inventory that expires within the specified number of days.

        Useful for:
        - FEFO (First Expired, First Out) picking prioritization
        - Expiration alerts and notifications
        - Markdown/clearance planning

        Args:
            days_threshold: Number of days to look ahead (default 90)
            sitio: Warehouse site code (defaults to DEFAULT_SITIO)
            empresa: Filter by company name (defaults to "GRANA")

        Returns:
            List of inventory records expiring within threshold, sorted by
            expiration date (soonest first)
        """
        from datetime import timedelta

        all_lots = await self.get_inventory_with_lots(
            sitio=sitio,
            empresa=empresa,
            include_zero_stock=False
        )

        cutoff_date = (datetime.now() + timedelta(days=days_threshold)).strftime("%Y-%m-%d")

        expiring = [
            lot for lot in all_lots
            if lot.get('expiration_date') and lot['expiration_date'] <= cutoff_date
        ]

        logger.info(
            f"Found {len(expiring)} lot records expiring within {days_threshold} days"
        )

        return expiring

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

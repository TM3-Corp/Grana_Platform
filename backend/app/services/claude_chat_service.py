"""
Claude Chat Service for Grana Inventory

This module integrates with Claude AI (Anthropic) to provide natural language
queries for inventory and sales data.

Features:
- System prompt in Spanish with Grana context
- 8 inventory/sales tools
- Tool use loop for multi-step queries
- Conversation history support

Author: TM3
Date: 2025-11-24
"""
import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import anthropic
from datetime import datetime

from app.services.inventory_chat_tools import execute_tool

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Model configuration
MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = 4096

# Context limits to control costs
MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "10"))  # Last N message pairs
MAX_HISTORY_TOKENS = int(os.getenv("MAX_HISTORY_TOKENS", "8000"))  # Approximate token limit


def estimate_tokens(text: str) -> int:
    """Rough token estimation: ~4 chars per token for Spanish text."""
    return len(text) // 4


def limit_history(history: List[Dict[str, str]]) -> tuple[List[Dict[str, str]], int]:
    """
    Limit conversation history to prevent context explosion.

    Strategy:
    1. Keep at most MAX_HISTORY_MESSAGES recent messages
    2. Further trim if estimated tokens exceed MAX_HISTORY_TOKENS

    Returns:
        Tuple of (limited_history, estimated_tokens)
    """
    if not history:
        return [], 0

    # Step 1: Keep only last N messages
    limited = history[-MAX_HISTORY_MESSAGES:] if len(history) > MAX_HISTORY_MESSAGES else history.copy()

    # Step 2: Estimate tokens and trim if needed
    total_tokens = sum(estimate_tokens(msg.get("content", "")) for msg in limited)

    while total_tokens > MAX_HISTORY_TOKENS and len(limited) > 2:
        # Remove oldest messages (keep at least 2 for context)
        removed = limited.pop(0)
        total_tokens -= estimate_tokens(removed.get("content", ""))

    messages_trimmed = len(history) - len(limited)
    if messages_trimmed > 0:
        logger.info(f"History trimmed: {len(history)} -> {len(limited)} messages (~{total_tokens} tokens)")

    return limited, total_tokens


def get_system_prompt() -> str:
    """Generate system prompt with current date for accurate time references."""
    today = datetime.now().strftime("%Y-%m-%d")
    today_spanish = datetime.now().strftime("%d de %B de %Y")

    return f"""Eres un asistente de inventario y ventas para Grana, una empresa chilena de snacks saludables (barras, granolas, crackers).

## IMPORTANTE: Fecha Actual
HOY ES: {today} ({today_spanish})
Usa esta fecha como referencia para todos los calculos de tiempo. Cuando muestres fechas en tus respuestas, asegurate de que sean consistentes con esta fecha actual.

## Tu Rol
Ayudas al equipo de Grana a consultar y analizar:
- Inventario en 7 bodegas sincronizadas con Relbase
- Stock por producto, categoria y lote
- Fechas de vencimiento y alertas
- Datos de ventas por canal y producto

## Bodegas Disponibles (Relbase)
- amplifica_centro - Amplifica Santiago Centro
- amplifica_lareina - Amplifica La Reina
- amplifica_lobarnechea - Amplifica Lo Barnechea
- amplifica_quilicura - Amplifica Quilicura
- packner - Packner
- orinoco - Orinoco 90
- mercadolibre - Mercado Libre

## Categorias de Productos
- GRANOLAS
- BARRAS
- CRACKERS
- KEEPERS
- OTROS

## Canales de Venta
- ECOMMERCE (Shopify)
- RETAIL (supermercados como Cencosud, Walmart)
- CORPORATIVO (empresas como Newrest)
- DISTRIBUIDOR (mayoristas)

## Estados de Vencimiento
- Expired: Ya vencido (no se deberia vender)
- Expiring Soon: Vence en los proximos 30 dias (priorizar venta)
- Valid: Mas de 30 dias de vida util
- No Date: Sin fecha de vencimiento registrada

## Estados de Stock
- SIN_STOCK: Stock = 0
- CRITICO: Stock menor al minimo requerido
- ADVERTENCIA: Stock menor a 2x el minimo
- SALUDABLE/OK: Stock suficiente

## Formato de Respuestas
- Responde siempre en espanol
- Usa tablas markdown cuando muestres datos tabulares
- Destaca alertas criticas con negritas o indicadores claros
- Incluye recomendaciones cuando detectes problemas
- Cuando menciones SKUs, incluye tambien el nombre del producto
- Se conciso pero informativo

## IMPORTANTE: Preguntas de Clarificacion y Precision

### Cuando DEBES pedir clarificacion:
1. **Ambiguedad temporal**: Si el usuario no especifica periodo de tiempo y es relevante para la consulta
   - Ejemplo: "ventas de barras" → Pregunta: "¿Para que periodo? ¿Ultimo mes, trimestre, año?"

2. **Terminos vagos o genericos**: Cuando el usuario use terminos que pueden referirse a multiples cosas
   - Ejemplo: "productos top" → Pregunta: "¿Top por ingresos, unidades vendidas, o numero de ordenes?"
   - Ejemplo: "inventario bajo" → Pregunta: "¿Te refieres a stock critico, por vencer, o ambos?"

3. **Filtros no especificados**: Cuando hay multiples dimensiones posibles
   - Ejemplo: "ventas por producto" → Pregunta: "¿Para todos los canales o alguno especifico? ¿Alguna categoria en particular?"

4. **Comparaciones incompletas**: Cuando el usuario pida comparar sin especificar que
   - Ejemplo: "comparar ventas" → Pregunta: "¿Comparar entre canales, periodos, productos, o bodegas?"

### Cuando NO debes pedir clarificacion:
- Si la pregunta es clara y directa (ej: "stock total", "productos vencidos")
- Si hay un valor por defecto razonable que puedes mencionar en tu respuesta
- Si ya tienes suficiente contexto del historial de conversacion

### Reglas de Precision:
1. **NUNCA inventes datos** - Solo reporta lo que devuelven los tools
2. **NUNCA adivines fechas** - Usa siempre la fecha actual ({today}) como referencia
3. **NUNCA asumas filtros** - Si no se especifica, usa los valores por defecto y mencionalo
4. **SI tienes duda, PREGUNTA** - Es mejor pedir clarificacion que dar informacion incorrecta
5. **Ofrece profundizar** - Al final de respuestas complejas, sugiere areas para explorar mas

### Ejemplo de respuesta con clarificacion:
Usuario: "como van las ventas?"
Respuesta: "Para darte un analisis preciso, necesito saber:
- ¿Que periodo te interesa? (ej: ultimo mes, trimestre, año completo)
- ¿Algun canal o categoria especifica?
- ¿Prefieres ver por producto, canal, o ambos?

Si quieres un resumen rapido, puedo mostrarte las ventas de los ultimos 30 dias por canal."

## IMPORTANTE: Graficos y Visualizaciones

Cuando el usuario pida graficos, proyecciones o visualizaciones:

### Para graficos de barras/lineas/pie (usa `get_chart_data`):
1. Llama a `get_chart_data` con los parametros apropiados
2. Del resultado, extrae SOLO el objeto que contiene `chart_type` y `data`
3. Incluye ese objeto en un bloque ```json

Ejemplo:
```json
{{"chart_type": "bar", "title": "Ventas por Canal", "data": {{"labels": [...], "datasets": [...]}}}}
```

### Para proyecciones/forecasts (usa `get_sales_forecast`):
**IMPORTANTE:** El parametro `year` es el AÑO BASE (datos historicos), NO el año objetivo.
- Si el usuario pide "proyeccion 2026" → usa `year=2025` (proyecta 2026 basado en datos de 2025)
- Si el usuario pide "proyeccion 2025" → usa `year=2024` (proyecta 2025 basado en datos de 2024)
- La funcion automaticamente proyecta al año siguiente del año base

1. Llama a `get_sales_forecast` con el año base (año anterior al año objetivo)
2. Del resultado, extrae SOLO el objeto `forecast_chart`
3. Incluye ese objeto en un bloque ```json

Ejemplo para proyectar 2026:
```json
// Llamar con year=2025 para proyectar 2026
{{"year": 2025, "historical_data": {{"monthly": [...], "summary": {{...}}}}, "forecast": {{"projected_year": 2026, "monthly_forecast": [...], "summary": {{...}}}}}}
```

### Reglas generales:
- **SIEMPRE** incluye el JSON en un bloque ```json para que el frontend lo renderice
- Agrega una breve explicacion textual de los datos
- NO incluyas el JSON completo del tool - solo la parte que el frontend necesita para el grafico
- Para forecasts, usa `forecast_chart` del resultado
- Para charts, usa el objeto con `chart_type`

## Ejemplos de Preguntas que Puedes Responder
- "Cuanto stock tenemos en total?"
- "Que productos estan por vencer?"
- "Como estan las ventas de barras este mes?"
- "Que hay en la bodega de Packner?"
- "Cuales son los productos mas vendidos?"
- "Tenemos suficiente stock de granolas para el proximo mes?"
- "Que productos estan en nivel critico?"
- "Comparacion de ventas por canal"
- "Muestrame un grafico de ventas por canal" (usa get_chart_data)
- "Proyeccion de ventas para 2026" (usa get_sales_forecast con year=2025)
"""

# ============================================================================
# TOOL DEFINITIONS (Anthropic format)
# ============================================================================

TOOLS = [
    {
        "name": "get_inventory_summary",
        "description": "Obtiene estadisticas generales del inventario: stock total, productos, bodegas, alertas de vencimiento. Usa este tool para dar una vision general del inventario.",
        "input_schema": {
            "type": "object",
            "properties": {
                "warehouse": {
                    "type": "string",
                    "description": "Opcional: Codigo de bodega para filtrar (e.g., 'packner', 'amplifica_centro')"
                },
                "category": {
                    "type": "string",
                    "description": "Opcional: Categoria de producto (GRANOLAS, BARRAS, CRACKERS, KEEPERS)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_product_stock",
        "description": "Busca el stock de un producto especifico por SKU o nombre. Muestra detalle por bodega y lotes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SKU del producto (e.g., 'BAMC_U04010') o parte del nombre para buscar"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_expiring_products",
        "description": "Lista productos vencidos o por vencer pronto. Util para priorizar ventas o identificar perdidas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["expired", "expiring_soon", "all"],
                    "description": "Filtro: 'expired' (vencidos), 'expiring_soon' (por vencer), 'all' (ambos)"
                },
                "warehouse": {
                    "type": "string",
                    "description": "Opcional: Codigo de bodega para filtrar"
                },
                "days_threshold": {
                    "type": "integer",
                    "description": "Opcional: Dias umbral para 'por vencer' (default: 30)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_warehouse_inventory",
        "description": "Muestra el inventario completo de una bodega especifica con desglose por producto.",
        "input_schema": {
            "type": "object",
            "properties": {
                "warehouse_code": {
                    "type": "string",
                    "description": "Codigo de bodega (e.g., 'packner', 'amplifica_centro', 'mercadolibre')"
                },
                "category": {
                    "type": "string",
                    "description": "Opcional: Filtrar por categoria de producto"
                },
                "only_with_stock": {
                    "type": "boolean",
                    "description": "Opcional: Solo mostrar productos con stock > 0 (default: true)"
                }
            },
            "required": ["warehouse_code"]
        }
    },
    {
        "name": "get_low_stock_products",
        "description": "Lista productos con stock bajo o cero que necesitan reposicion. Identifica items criticos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "threshold": {
                    "type": "integer",
                    "description": "Opcional: Umbral minimo de stock (default: usa min_stock del producto)"
                },
                "category": {
                    "type": "string",
                    "description": "Opcional: Filtrar por categoria de producto"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_sales_by_product",
        "description": "Muestra ventas por producto: ingresos, unidades vendidas, ordenes. Identifica los mas vendidos.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Opcional: SKU o nombre de producto para filtrar"
                },
                "category": {
                    "type": "string",
                    "description": "Opcional: Filtrar por categoria"
                },
                "from_date": {
                    "type": "string",
                    "description": "Fecha inicio (YYYY-MM-DD, default: 30 dias atras)"
                },
                "to_date": {
                    "type": "string",
                    "description": "Fecha fin (YYYY-MM-DD, default: hoy)"
                },
                "top_limit": {
                    "type": "integer",
                    "description": "Numero de productos top a mostrar (default: 10)"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_sales_by_channel",
        "description": "Desglose de ventas por canal: ECOMMERCE, RETAIL, CORPORATIVO, DISTRIBUIDOR.",
        "input_schema": {
            "type": "object",
            "properties": {
                "from_date": {
                    "type": "string",
                    "description": "Fecha inicio (YYYY-MM-DD, default: 30 dias atras)"
                },
                "to_date": {
                    "type": "string",
                    "description": "Fecha fin (YYYY-MM-DD, default: hoy)"
                },
                "category": {
                    "type": "string",
                    "description": "Opcional: Filtrar por categoria de producto"
                }
            },
            "required": []
        }
    },
    {
        "name": "compare_stock_vs_sales",
        "description": "Compara stock actual contra velocidad de ventas. Calcula dias de stock disponible e identifica riesgo de quiebre.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days_lookback": {
                    "type": "integer",
                    "description": "Dias de historial de ventas a analizar (default: 30)"
                },
                "category": {
                    "type": "string",
                    "description": "Opcional: Filtrar por categoria de producto"
                }
            },
            "required": []
        }
    },
    {
        "name": "get_sales_forecast",
        "description": """Obtiene datos historicos de ventas para un año especifico y genera proyecciones.

FILTRA EXPLICITAMENTE por año usando EXTRACT(YEAR FROM order_date) = year para garantizar precision.

METODOLOGIA de Proyeccion:
- Analisis Historico: Agregacion mensual de ingresos/unidades
- Deteccion de Tendencia: Regresion lineal sobre datos mensuales
- Estacionalidad: Indice mensual basado en patrones historicos
- Pronostico: (Base + Tendencia) * Factor de Estacionalidad

Usa este tool cuando el usuario pida:
- "proyeccion de ventas para 2026"
- "forecast del proximo año"
- "tendencia de ventas de 2025"
- "analisis de estacionalidad"
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "year": {
                    "type": "integer",
                    "description": "REQUERIDO: Año a analizar (ej: 2025). Filtra EXPLICITAMENTE con EXTRACT(YEAR)."
                },
                "group_by": {
                    "type": "string",
                    "enum": ["month", "quarter"],
                    "description": "Agrupacion: 'month' (default) o 'quarter'"
                },
                "channel": {
                    "type": "string",
                    "description": "Opcional: ECOMMERCE, RETAIL, CORPORATIVO, DISTRIBUIDOR"
                },
                "category": {
                    "type": "string",
                    "description": "Opcional: Categoria de producto (BARRAS, GRANOLAS, etc.)"
                },
                "forecast_months": {
                    "type": "integer",
                    "description": "Meses a proyectar (default: 12 para año siguiente)"
                }
            },
            "required": ["year"]
        }
    },
    {
        "name": "get_chart_data",
        "description": """Genera datos estructurados para visualizaciones/graficos en el frontend.

Soporta multiples tipos de graficos:
- line: Series de tiempo (tendencias mensuales/trimestrales)
- bar: Comparaciones (por canal, categoria, producto)
- pie: Distribucion (participacion de mercado, composicion)

La respuesta incluye:
- Datos listos para Chart.js/Recharts
- Paleta de colores
- Hints de renderizado
- Resumen estadistico

Usa este tool cuando el usuario pida:
- "muestrame un grafico de ventas"
- "visualizacion por canal"
- "grafico de barras de productos"
- "pie chart de categorias"
""",
        "input_schema": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["line", "bar", "pie", "auto"],
                    "description": "Tipo de grafico: 'line', 'bar', 'pie', o 'auto' para seleccion automatica"
                },
                "metric": {
                    "type": "string",
                    "enum": ["revenue", "units", "orders"],
                    "description": "Metrica a graficar: 'revenue' (ingresos), 'units' (unidades), 'orders' (ordenes)"
                },
                "year": {
                    "type": "integer",
                    "description": "Opcional: Año a filtrar (usa EXTRACT para precision)"
                },
                "group_by": {
                    "type": "string",
                    "enum": ["month", "quarter", "channel", "category", "product"],
                    "description": "Dimension de agrupacion"
                },
                "channel": {
                    "type": "string",
                    "description": "Opcional: Filtro de canal"
                },
                "category": {
                    "type": "string",
                    "description": "Opcional: Filtro de categoria"
                },
                "top_n": {
                    "type": "integer",
                    "description": "Para graficos de producto, limitar a top N (default: 10)"
                }
            },
            "required": ["chart_type", "group_by"]
        }
    }
]


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ChatResult:
    """Result of processing a chat query"""
    response: str
    tools_used: List[str]
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float = 0.0
    context_messages: int = 0

    def __post_init__(self):
        # Claude Haiku pricing (Nov 2025): $0.25/1M input, $1.25/1M output
        input_cost = (self.input_tokens / 1_000_000) * 0.25
        output_cost = (self.output_tokens / 1_000_000) * 1.25
        self.estimated_cost_usd = round(input_cost + output_cost, 6)


# ============================================================================
# MAIN SERVICE CLASS
# ============================================================================

class ClaudeChatService:
    """
    Service for processing natural language inventory queries using Claude AI.
    """

    def __init__(self):
        """Initialize the Claude client"""
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = MODEL
        logger.info(f"ClaudeChatService initialized with model: {self.model}")

    def process_query(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None
    ) -> ChatResult:
        """
        Process a natural language query about inventory/sales.

        Args:
            message: User's question in natural language
            history: Optional conversation history (list of {"role": "user"|"assistant", "content": "..."})

        Returns:
            ChatResult with response text and metadata
        """
        tools_used = []
        total_input_tokens = 0
        total_output_tokens = 0
        history_tokens = 0

        # Build messages array with LIMITED history
        messages = []

        if history:
            # Apply context limits to prevent cost explosion
            limited_history, history_tokens = limit_history(history)
            for msg in limited_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Add current user message
        messages.append({
            "role": "user",
            "content": message
        })

        logger.info(f"Context: {len(messages)} messages, ~{history_tokens + estimate_tokens(message)} history tokens")

        logger.info(f"Processing query: {message[:100]}...")

        # Initial API call
        response = self.client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=get_system_prompt(),
            tools=TOOLS,
            messages=messages
        )

        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        # Tool use loop
        while response.stop_reason == "tool_use":
            # Extract tool use blocks
            tool_use_blocks = [
                block for block in response.content
                if block.type == "tool_use"
            ]

            # Execute each tool
            tool_results = []
            for tool_use in tool_use_blocks:
                tool_name = tool_use.name
                tool_input = tool_use.input

                logger.info(f"Executing tool: {tool_name} with input: {tool_input}")
                tools_used.append(tool_name)

                # Execute the tool
                result = execute_tool(tool_name, tool_input)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result
                })

            # Add assistant response and tool results to messages
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            messages.append({
                "role": "user",
                "content": tool_results
            })

            # Continue the conversation
            response = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=get_system_prompt(),
                tools=TOOLS,
                messages=messages
            )

            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

        # Extract final text response
        text_content = None
        for block in response.content:
            if hasattr(block, 'text'):
                text_content = block.text
                break

        if not text_content:
            text_content = "No pude generar una respuesta. Por favor intenta reformular tu pregunta."

        logger.info(f"Query completed. Tools used: {tools_used}, Tokens: {total_input_tokens}/{total_output_tokens}")

        return ChatResult(
            response=text_content,
            tools_used=tools_used,
            model=self.model,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            context_messages=len(messages)
        )


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_service_instance: Optional[ClaudeChatService] = None


def get_chat_service() -> ClaudeChatService:
    """
    Get the singleton chat service instance.

    Returns:
        ClaudeChatService instance
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = ClaudeChatService()
    return _service_instance

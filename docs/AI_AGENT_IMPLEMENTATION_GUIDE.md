# AI Agent Implementation Guide

## Extrapolation for SocialMap: Sociometry Platform for School Climate

This document analyzes the AI agent architecture used in Grana Platform and provides a comprehensive guide for implementing similar functionality in **SocialMap**, a sociometry platform that monitors student relationships and socio-emotional situations.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Core Components](#2-core-components)
3. [The Tool-Use Pattern](#3-the-tool-use-pattern)
4. [System Prompt Design](#4-system-prompt-design)
5. [SocialMap Tool Definitions](#5-socialmap-tool-definitions)
6. [Frontend Integration](#6-frontend-integration)
7. [Cost Management](#7-cost-management)
8. [Security Considerations](#8-security-considerations)
9. [Implementation Checklist](#9-implementation-checklist)

---

## 1. Architecture Overview

### Grana Platform Pattern

The Grana Platform uses Claude AI as an **intelligent query layer** between users and database. Instead of building complex UI for every possible query, users ask natural language questions and Claude translates them into structured database operations.

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE                          │
│  FloatingChatWidget.tsx - Natural language input            │
└─────────────────────┬───────────────────────────────────────┘
                      │ POST /api/v1/inventory/chat
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  CLAUDE CHAT SERVICE                         │
│  claude_chat_service.py                                     │
│  • Receives natural language query                           │
│  • System prompt provides domain context                     │
│  • Claude decides which tools to use                         │
│  • Tool-use loop executes database queries                   │
│  • Claude formats response for user                          │
└─────────────────────┬───────────────────────────────────────┘
                      │ Tool calls
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    TOOL FUNCTIONS                            │
│  inventory_chat_tools.py                                    │
│  • 10 specialized functions                                  │
│  • Each executes SQL queries                                 │
│  • Returns JSON data to Claude                               │
└─────────────────────┬───────────────────────────────────────┘
                      │ SQL queries
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     DATABASE                                 │
│  PostgreSQL/Supabase                                        │
│  • Orders, products, inventory, channels...                  │
└─────────────────────────────────────────────────────────────┘
```

### SocialMap Adaptation

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE                          │
│  Chat widget for teachers/counselors/administrators         │
└─────────────────────┬───────────────────────────────────────┘
                      │ POST /api/v1/insights/chat
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  CLAUDE CHAT SERVICE                         │
│  sociometry_chat_service.py                                 │
│  • Receives questions about student relationships            │
│  • System prompt provides school context + ethics            │
│  • Claude decides which analysis tools to use                │
│  • Returns insights with appropriate sensitivity             │
└─────────────────────┬───────────────────────────────────────┘
                      │ Tool calls
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                 SOCIOMETRY TOOLS                             │
│  sociometry_tools.py                                        │
│  • Network analysis functions                                │
│  • Risk detection algorithms                                 │
│  • Trend analysis over time                                  │
│  • Group dynamics calculations                               │
└─────────────────────┬───────────────────────────────────────┘
                      │ Queries
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     DATABASE                                 │
│  • students, classrooms, relationships                       │
│  • sociogram_responses, surveys                              │
│  • intervention_logs, risk_assessments                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Core Components

### 2.1 Backend: Chat Service (Python/FastAPI)

**Grana Implementation:** `backend/app/services/claude_chat_service.py`

Key patterns to replicate:

```python
# SocialMap: sociometry_chat_service.py

import os
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import anthropic
from datetime import datetime

from app.services.sociometry_tools import execute_tool

logger = logging.getLogger(__name__)

# Configuration
MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
MAX_TOKENS = 4096
MAX_HISTORY_MESSAGES = 10
MAX_HISTORY_TOKENS = 8000


@dataclass
class ChatResult:
    """Result of processing a chat query"""
    response: str
    tools_used: List[str]
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float = 0.0

    def __post_init__(self):
        # Claude Haiku pricing: $0.25/1M input, $1.25/1M output
        input_cost = (self.input_tokens / 1_000_000) * 0.25
        output_cost = (self.output_tokens / 1_000_000) * 1.25
        self.estimated_cost_usd = round(input_cost + output_cost, 6)


class SociometryChatService:
    """Service for processing natural language queries about student relationships."""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = MODEL

    def process_query(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        user_role: str = "teacher"  # teacher, counselor, admin
    ) -> ChatResult:
        """Process a natural language query about students."""
        tools_used = []
        total_input_tokens = 0
        total_output_tokens = 0

        # Build messages with limited history
        messages = self._build_messages(message, history)

        # Initial API call
        response = self.client.messages.create(
            model=self.model,
            max_tokens=MAX_TOKENS,
            system=get_system_prompt(user_role),
            tools=TOOLS,
            messages=messages
        )

        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        # Tool-use loop
        while response.stop_reason == "tool_use":
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            tool_results = []
            for tool_use in tool_use_blocks:
                logger.info(f"Executing tool: {tool_use.name}")
                tools_used.append(tool_use.name)

                result = execute_tool(tool_use.name, tool_use.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result
                })

            # Continue conversation with tool results
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            response = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=get_system_prompt(user_role),
                tools=TOOLS,
                messages=messages
            )

            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens

        # Extract final text
        text_content = next(
            (b.text for b in response.content if hasattr(b, 'text')),
            "No pude generar una respuesta."
        )

        return ChatResult(
            response=text_content,
            tools_used=tools_used,
            model=self.model,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens
        )
```

### 2.2 Tool Definitions

**Grana Implementation:** `backend/app/services/inventory_chat_tools.py`

Tools are defined in Anthropic's format and registered for execution:

```python
# Tool definition structure
TOOLS = [
    {
        "name": "tool_name",
        "description": "What this tool does and when to use it",
        "input_schema": {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "What this parameter means"
                },
                "param2": {
                    "type": "integer",
                    "description": "Another parameter"
                }
            },
            "required": ["param1"]  # Required parameters
        }
    }
]

# Tool execution registry
TOOL_FUNCTIONS = {
    "tool_name": tool_function,
}

def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> str:
    """Execute a tool by name with given input."""
    if tool_name not in TOOL_FUNCTIONS:
        return json.dumps({"error": f"Tool '{tool_name}' not found"})

    try:
        return TOOL_FUNCTIONS[tool_name](**tool_input)
    except Exception as e:
        return json.dumps({"error": str(e)})
```

### 2.3 API Endpoint

**Grana Implementation:** `backend/app/api/chat.py`

```python
# SocialMap: api/insights.py

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Literal
from datetime import datetime

from app.services.sociometry_chat_service import get_chat_service
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/v1/insights", tags=["insights-chat"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    history: List[ChatMessage] = Field(default=[])
    classroom_id: Optional[int] = None  # Context filter


class ChatResponse(BaseModel):
    success: bool
    response: str
    tools_used: List[str]
    model: str
    usage: dict
    timestamp: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user = Depends(get_current_user)
):
    """Process natural language query about student relationships."""
    try:
        chat_service = get_chat_service()
        history = [{"role": m.role, "content": m.content} for m in request.history]

        result = chat_service.process_query(
            message=request.message,
            history=history,
            user_role=current_user.role
        )

        return ChatResponse(
            success=True,
            response=result.response,
            tools_used=result.tools_used,
            model=result.model,
            usage={
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "estimated_cost_usd": result.estimated_cost_usd
            },
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 3. The Tool-Use Pattern

### How It Works

1. **User asks a question** in natural language
2. **Claude receives** the question + system prompt + available tools
3. **Claude decides** which tool(s) to call and with what parameters
4. **Backend executes** the tool function (database query)
5. **Tool returns** JSON data to Claude
6. **Claude interprets** the data and formats a human-friendly response
7. **If needed**, Claude calls more tools (loop continues)
8. **Final response** sent to user

### Why This Pattern Is Powerful

| Traditional Approach | Tool-Use Pattern |
|---------------------|------------------|
| Build UI for every query type | One chat interface handles all queries |
| User must know exact filters | User asks naturally, AI figures out filters |
| Complex dashboard navigation | Conversational, intuitive |
| Rigid predefined reports | Flexible, ad-hoc analysis |
| Requires training | Self-explanatory |

### Tool Design Principles

1. **Single Responsibility**: Each tool does one thing well
2. **Clear Descriptions**: Claude uses descriptions to decide when to use tools
3. **Sensible Defaults**: Most parameters should be optional with good defaults
4. **JSON Output**: Tools return structured JSON that Claude can interpret
5. **Error Handling**: Always return useful error messages in JSON format

---

## 4. System Prompt Design

### Grana's System Prompt Structure

```python
def get_system_prompt() -> str:
    today = datetime.now().strftime("%Y-%m-%d")

    return f"""Eres un asistente de inventario para Grana...

## IMPORTANTE: Fecha Actual
HOY ES: {today}

## Tu Rol
[What the AI should do]

## Contexto del Dominio
[Domain-specific knowledge: warehouses, categories, channels]

## Formato de Respuestas
[How to format answers: language, tables, highlights]

## Reglas de Clarificacion
[When to ask for more info vs. when to proceed]

## Ejemplos
[Sample questions the AI can answer]
"""
```

### SocialMap System Prompt

```python
def get_system_prompt(user_role: str = "teacher") -> str:
    today = datetime.now().strftime("%Y-%m-%d")

    # Role-based permissions
    if user_role == "admin":
        access_level = "full access to all classrooms and historical data"
    elif user_role == "counselor":
        access_level = "access to all students with focus on at-risk cases"
    else:  # teacher
        access_level = "access to your assigned classrooms only"

    return f"""Eres un asistente de análisis sociométrico para SocialMap, una plataforma que ayuda a entender las dinámicas sociales en escuelas.

## FECHA ACTUAL
HOY ES: {today}

## TU ROL
Ayudas a {user_role}s a comprender las relaciones entre estudiantes y el clima escolar. Tienes {access_level}.

Puedes analizar:
- Redes de amistad y popularidad
- Estudiantes en riesgo de aislamiento social
- Dinámicas de grupo y subgrupos
- Evolución de relaciones en el tiempo
- Respuestas a encuestas socioemocionales

## PRINCIPIOS ETICOS FUNDAMENTALES

### NUNCA debes:
1. **Etiquetar negativamente**: No llames a ningún estudiante "rechazado", "impopular", o términos despectivos
2. **Hacer predicciones deterministas**: Las situaciones sociales son dinámicas y pueden cambiar
3. **Revelar información sensible**: Respuestas individuales son confidenciales
4. **Sugerir intervenciones clínicas**: Solo profesionales pueden hacer diagnósticos

### SIEMPRE debes:
1. **Usar lenguaje constructivo**: "Estudiante que podría beneficiarse de más conexiones"
2. **Enfocarte en oportunidades**: No problemas, sino áreas de crecimiento
3. **Contextualizar datos**: Los números no cuentan toda la historia
4. **Sugerir próximos pasos**: Observación, conversación, no conclusiones

## CONCEPTOS SOCIOMETRICOS

### Métricas de Red
- **Grado de entrada**: Cuántos compañeros eligen a un estudiante
- **Grado de salida**: A cuántos compañeros elige un estudiante
- **Reciprocidad**: Relaciones bidireccionales
- **Centralidad**: Posición en la red social

### Perfiles Sociométricos (usar con sensibilidad)
- **Bien conectado**: Alto grado de entrada y salida
- **Selectivo**: Pocos pero recíprocos vínculos
- **En proceso de integración**: Necesita apoyo para formar conexiones
- **Influyente**: Alta centralidad en la red

### Tipos de Preguntas Sociométricas
- Nominación positiva: "¿Con quién te gusta trabajar?"
- Nominación negativa: "¿Con quién prefieres no trabajar?" (usar con precaución)
- Percepción: "¿Quién crees que te elegiría?"
- Actividades: "¿Con quién juegas/estudias?"

## FORMATO DE RESPUESTAS
- Responde siempre en español
- Usa lenguaje profesional pero accesible
- Incluye visualizaciones cuando ayuden (grafos, tablas)
- Sugiere acciones concretas y realizables
- Respeta la confidencialidad: datos agregados, no individuales (salvo casos de riesgo)

## CUANDO PEDIR CLARIFICACION
- Si no especifican el aula o período
- Si la pregunta podría interpretarse de múltiples formas
- Si necesitas más contexto para dar una respuesta útil

## EJEMPLOS DE PREGUNTAS QUE PUEDES RESPONDER
- "¿Cómo está el clima social en 5° básico?"
- "¿Hay estudiantes que podrían necesitar apoyo para integrarse?"
- "¿Cómo han evolucionado las relaciones este semestre?"
- "Muéstrame la red de amistad de 3°A"
- "¿Qué actividades grupales podrían ayudar a fortalecer vínculos?"
"""
```

---

## 5. SocialMap Tool Definitions

### Tool 1: get_classroom_network

```python
{
    "name": "get_classroom_network",
    "description": """Obtiene la red social de un aula específica.

Devuelve:
- Lista de estudiantes con sus métricas (grado entrada/salida, reciprocidad)
- Conexiones entre estudiantes
- Subgrupos detectados
- Estudiantes que podrían beneficiarse de más conexiones

Usa este tool cuando pregunten sobre:
- "¿Cómo está la red social de 5°A?"
- "Muéstrame las conexiones del curso"
- "¿Hay grupos aislados?"
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "classroom_id": {
                "type": "integer",
                "description": "ID del aula a analizar"
            },
            "question_type": {
                "type": "string",
                "enum": ["friendship", "work", "play", "all"],
                "description": "Tipo de relación a analizar (amistad, trabajo, juego, todas)"
            },
            "period": {
                "type": "string",
                "description": "Período a analizar (ej: '2025-Q1', 'current')"
            }
        },
        "required": ["classroom_id"]
    }
}
```

### Tool 2: get_student_profile

```python
{
    "name": "get_student_profile",
    "description": """Obtiene el perfil sociométrico de un estudiante específico.

IMPORTANTE: Solo devuelve datos si hay una razón educativa válida.
Los datos se presentan de forma constructiva, enfocándose en oportunidades.

Incluye:
- Posición en la red social
- Evolución en el tiempo
- Conexiones recíprocas
- Áreas de fortaleza social

NO incluye:
- Rechazos explícitos
- Comparaciones negativas
- Etiquetas diagnósticas
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "student_id": {
                "type": "integer",
                "description": "ID del estudiante"
            },
            "include_history": {
                "type": "boolean",
                "description": "Incluir evolución histórica (default: true)"
            }
        },
        "required": ["student_id"]
    }
}
```

### Tool 3: get_at_risk_students

```python
{
    "name": "get_at_risk_students",
    "description": """Identifica estudiantes que podrían beneficiarse de apoyo en integración social.

Criterios (configurables):
- Bajo número de conexiones recíprocas
- Disminución en nominaciones positivas
- Respuestas en encuestas que indican malestar
- Ausencia prolongada de nominaciones

IMPORTANTE: Esta herramienta es para detección temprana y apoyo,
NO para etiquetar o excluir estudiantes.

Devuelve:
- Lista priorizada de estudiantes
- Indicadores específicos para cada uno
- Sugerencias de intervención positiva
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "classroom_id": {
                "type": "integer",
                "description": "ID del aula (opcional, si no se especifica analiza todas)"
            },
            "risk_threshold": {
                "type": "string",
                "enum": ["high", "medium", "all"],
                "description": "Nivel de prioridad a mostrar (default: medium)"
            },
            "include_recommendations": {
                "type": "boolean",
                "description": "Incluir sugerencias de intervención (default: true)"
            }
        },
        "required": []
    }
}
```

### Tool 4: get_group_dynamics

```python
{
    "name": "get_group_dynamics",
    "description": """Analiza la dinámica de subgrupos dentro de un aula.

Identifica:
- Subgrupos cohesivos
- Puentes entre grupos
- Estudiantes centrales en cada grupo
- Estudiantes periféricos que podrían integrarse mejor

Útil para:
- Planificar trabajo en equipo
- Entender conflictos grupales
- Diseñar actividades de integración
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "classroom_id": {
                "type": "integer",
                "description": "ID del aula"
            },
            "min_group_size": {
                "type": "integer",
                "description": "Tamaño mínimo de grupo a considerar (default: 3)"
            }
        },
        "required": ["classroom_id"]
    }
}
```

### Tool 5: get_relationship_trends

```python
{
    "name": "get_relationship_trends",
    "description": """Analiza cómo han evolucionado las relaciones en el tiempo.

Muestra:
- Cambios en cohesión del grupo
- Estudiantes cuya situación ha mejorado/empeorado
- Efectividad de intervenciones previas
- Comparación entre períodos

Períodos disponibles:
- Semestres
- Trimestres
- Mediciones específicas
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "classroom_id": {
                "type": "integer",
                "description": "ID del aula"
            },
            "period_from": {
                "type": "string",
                "description": "Período inicial (ej: '2024-S2')"
            },
            "period_to": {
                "type": "string",
                "description": "Período final (ej: '2025-S1')"
            },
            "focus": {
                "type": "string",
                "enum": ["cohesion", "individual", "groups"],
                "description": "Enfoque del análisis (default: cohesion)"
            }
        },
        "required": ["classroom_id"]
    }
}
```

### Tool 6: get_survey_summary

```python
{
    "name": "get_survey_summary",
    "description": """Resume respuestas de encuestas socioemocionales (NO sociométricas).

Analiza respuestas a preguntas como:
- "¿Cómo te sientes en el colegio?"
- "¿Te sientes incluido en actividades?"
- "¿Hay algo que te preocupa?"

CONFIDENCIALIDAD: Solo devuelve datos agregados.
Las respuestas individuales NO se muestran excepto para alertas críticas.

Alertas críticas (sí se reportan):
- Indicadores de bullying
- Señales de malestar significativo
- Solicitudes de ayuda explícitas
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "classroom_id": {
                "type": "integer",
                "description": "ID del aula"
            },
            "survey_type": {
                "type": "string",
                "enum": ["wellbeing", "inclusion", "safety", "all"],
                "description": "Tipo de encuesta a resumir"
            },
            "period": {
                "type": "string",
                "description": "Período a analizar"
            }
        },
        "required": ["classroom_id"]
    }
}
```

### Tool 7: get_network_visualization

```python
{
    "name": "get_network_visualization",
    "description": """Genera datos para visualizar la red social como un grafo.

Devuelve datos estructurados que el frontend puede renderizar:
- Nodos (estudiantes) con atributos
- Aristas (relaciones) con pesos
- Posiciones sugeridas para layout
- Colores según métricas

Tipos de visualización:
- force: Layout de fuerzas (relaciones naturales)
- circular: Todos en círculo (equitativo)
- hierarchical: Por popularidad (usar con cuidado)
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "classroom_id": {
                "type": "integer",
                "description": "ID del aula"
            },
            "layout": {
                "type": "string",
                "enum": ["force", "circular", "hierarchical"],
                "description": "Tipo de layout (default: force)"
            },
            "highlight": {
                "type": "string",
                "enum": ["none", "reciprocity", "centrality", "groups"],
                "description": "Qué resaltar visualmente"
            },
            "anonymize": {
                "type": "boolean",
                "description": "Mostrar con números en vez de nombres (default: false)"
            }
        },
        "required": ["classroom_id"]
    }
}
```

### Tool 8: get_intervention_suggestions

```python
{
    "name": "get_intervention_suggestions",
    "description": """Sugiere intervenciones basadas en el análisis sociométrico.

Tipos de sugerencias:
- Actividades grupales para fortalecer vínculos
- Estrategias de integración para estudiantes específicos
- Cambios en distribución de asientos/equipos
- Temas para abordar en orientación

IMPORTANTE: Las sugerencias son recomendaciones, no prescripciones.
Siempre debe haber evaluación profesional antes de implementar.
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "classroom_id": {
                "type": "integer",
                "description": "ID del aula"
            },
            "focus_area": {
                "type": "string",
                "enum": ["integration", "conflict", "cohesion", "general"],
                "description": "Área de enfoque para las sugerencias"
            },
            "student_id": {
                "type": "integer",
                "description": "Opcional: estudiante específico para sugerencias focalizadas"
            }
        },
        "required": ["classroom_id"]
    }
}
```

### Complete Tools Registry

```python
# sociometry_tools.py

TOOL_FUNCTIONS = {
    "get_classroom_network": get_classroom_network,
    "get_student_profile": get_student_profile,
    "get_at_risk_students": get_at_risk_students,
    "get_group_dynamics": get_group_dynamics,
    "get_relationship_trends": get_relationship_trends,
    "get_survey_summary": get_survey_summary,
    "get_network_visualization": get_network_visualization,
    "get_intervention_suggestions": get_intervention_suggestions,
}
```

---

## 6. Frontend Integration

### Chat Widget Component

Based on Grana's `FloatingChatWidget.tsx`:

```tsx
// SocialMap: components/InsightsChatWidget.tsx

'use client';

import { useState, useEffect, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import dynamic from 'next/dynamic';

const NetworkGraph = dynamic(() => import('./NetworkGraph'), { ssr: false });

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  toolsUsed?: string[];
  graphData?: NetworkGraphData;
}

const QUICK_ACTIONS = [
  { label: 'Clima Social', query: 'Dame un resumen del clima social de mi curso' },
  { label: 'Atención', query: '¿Hay estudiantes que necesiten apoyo en integración?' },
  { label: 'Red Social', query: 'Muéstrame la red de amistades del curso' },
  { label: 'Evolución', query: '¿Cómo han evolucionado las relaciones este semestre?' },
  { label: 'Sugerencias', query: '¿Qué actividades podrían mejorar la cohesión grupal?' },
];

export default function InsightsChatWidget() {
  const { status, data: session } = useSession();
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;

    setInput('');
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const history = messages.map(m => ({
        role: m.role,
        content: m.content,
      }));

      const response = await fetch('/api/v1/insights/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history,
          classroom_id: session?.user?.defaultClassroom
        }),
      });

      const data = await response.json();

      if (data.success) {
        // Parse network graph data if present
        const graphData = parseGraphData(data.response);
        const cleanContent = graphData
          ? removeGraphData(data.response)
          : data.response;

        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: cleanContent,
          timestamp: new Date(),
          toolsUsed: data.tools_used,
          graphData,
        };
        setMessages(prev => [...prev, assistantMessage]);
      }
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Render logic similar to Grana's FloatingChatWidget
  // ...
}
```

### Network Graph Component

```tsx
// components/NetworkGraph.tsx

import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface Node {
  id: string;
  name: string;
  group?: number;
  reciprocity?: number;
  centrality?: number;
}

interface Link {
  source: string;
  target: string;
  weight?: number;
  reciprocal?: boolean;
}

interface NetworkGraphData {
  nodes: Node[];
  links: Link[];
  layout: 'force' | 'circular';
}

export default function NetworkGraph({ data }: { data: NetworkGraphData }) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!data || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    const width = 400;
    const height = 300;

    // Clear previous
    svg.selectAll('*').remove();

    // Create force simulation
    const simulation = d3.forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.links).id((d: any) => d.id))
      .force('charge', d3.forceManyBody().strength(-100))
      .force('center', d3.forceCenter(width / 2, height / 2));

    // Draw links
    const link = svg.append('g')
      .selectAll('line')
      .data(data.links)
      .join('line')
      .attr('stroke', d => d.reciprocal ? '#10B981' : '#CBD5E1')
      .attr('stroke-width', d => d.reciprocal ? 2 : 1);

    // Draw nodes
    const node = svg.append('g')
      .selectAll('circle')
      .data(data.nodes)
      .join('circle')
      .attr('r', d => 5 + (d.centrality || 0) * 10)
      .attr('fill', d => d3.schemeCategory10[d.group || 0])
      .call(drag(simulation));

    // Labels
    const labels = svg.append('g')
      .selectAll('text')
      .data(data.nodes)
      .join('text')
      .text(d => d.name)
      .attr('font-size', 10)
      .attr('dx', 12);

    simulation.on('tick', () => {
      link
        .attr('x1', d => (d.source as any).x)
        .attr('y1', d => (d.source as any).y)
        .attr('x2', d => (d.target as any).x)
        .attr('y2', d => (d.target as any).y);

      node
        .attr('cx', d => (d as any).x)
        .attr('cy', d => (d as any).y);

      labels
        .attr('x', d => (d as any).x)
        .attr('y', d => (d as any).y);
    });

  }, [data]);

  return (
    <div className="bg-white rounded-lg border p-2">
      <svg ref={svgRef} width={400} height={300} />
    </div>
  );
}
```

---

## 7. Cost Management

### Grana's Cost Tracking

```python
@dataclass
class ChatResult:
    # ...
    def __post_init__(self):
        # Claude Haiku 4.5: $0.25/1M input, $1.25/1M output
        input_cost = (self.input_tokens / 1_000_000) * 0.25
        output_cost = (self.output_tokens / 1_000_000) * 1.25
        self.estimated_cost_usd = round(input_cost + output_cost, 6)
```

### Model Selection Strategy

| Model | Cost (Input/Output per 1M) | Use Case |
|-------|---------------------------|----------|
| **Haiku 4.5** | $0.25 / $1.25 | Production queries, quick responses |
| **Sonnet 3.5** | $3.00 / $15.00 | Complex analysis, detailed reports |
| **Opus 4** | $15.00 / $75.00 | Critical decisions, nuanced situations |

### SocialMap Recommendation

```python
def get_model_for_query(query_type: str) -> str:
    """Select model based on query complexity."""

    # Quick queries: use Haiku (10-20x cheaper)
    quick_patterns = [
        "resumen", "cuántos", "lista", "mostrar",
        "summary", "how many", "list", "show"
    ]

    # Complex analysis: use Sonnet
    complex_patterns = [
        "analizar", "por qué", "tendencias", "comparar",
        "analyze", "why", "trends", "compare"
    ]

    # Sensitive/critical: use Opus
    critical_patterns = [
        "riesgo", "bullying", "intervención", "urgente",
        "risk", "intervention", "urgent"
    ]

    query_lower = query_type.lower()

    if any(p in query_lower for p in critical_patterns):
        return "claude-opus-4-20250514"
    elif any(p in query_lower for p in complex_patterns):
        return "claude-sonnet-4-20250514"
    else:
        return "claude-haiku-4-5-20251001"
```

### Context Limiting (Critical for Cost Control)

```python
MAX_HISTORY_MESSAGES = 10  # Keep last 10 messages
MAX_HISTORY_TOKENS = 8000  # Approximate token limit

def limit_history(history: List[Dict]) -> List[Dict]:
    """Prevent context explosion."""
    if not history:
        return []

    # Keep only recent messages
    limited = history[-MAX_HISTORY_MESSAGES:]

    # Further trim if too long
    total_tokens = sum(len(m.get("content", "")) // 4 for m in limited)

    while total_tokens > MAX_HISTORY_TOKENS and len(limited) > 2:
        limited.pop(0)
        total_tokens = sum(len(m.get("content", "")) // 4 for m in limited)

    return limited
```

---

## 8. Security Considerations

### 8.1 Data Privacy for Minors

```python
# CRITICAL: Never expose individual student data in responses
# unless there's an explicit safeguarding concern

class DataPrivacyMiddleware:
    """Ensure student privacy in AI responses."""

    SENSITIVE_PATTERNS = [
        r"estudiante \d+ dijo",  # Individual quotes
        r"respuesta individual",  # Individual responses
        r"nombres completos",     # Full names in sensitive contexts
    ]

    def sanitize_response(self, response: str) -> str:
        """Remove potentially identifying information."""
        # Implementation depends on your privacy requirements
        pass
```

### 8.2 Role-Based Access Control

```python
def get_accessible_classrooms(user: User) -> List[int]:
    """Return classroom IDs user can access."""
    if user.role == "admin":
        return get_all_classroom_ids()
    elif user.role == "counselor":
        return get_all_classroom_ids()  # But with different view
    else:  # teacher
        return get_teacher_classrooms(user.id)

def validate_tool_access(user: User, tool_name: str, params: dict) -> bool:
    """Ensure user can access requested data."""
    classroom_id = params.get("classroom_id")
    if classroom_id:
        return classroom_id in get_accessible_classrooms(user)
    return True
```

### 8.3 Audit Logging

```python
def log_query(
    user_id: int,
    query: str,
    tools_used: List[str],
    accessed_students: List[int] = None
):
    """Log all AI queries for audit purposes."""
    db.audit_log.insert({
        "user_id": user_id,
        "query": query,
        "tools_used": tools_used,
        "accessed_students": accessed_students,
        "timestamp": datetime.utcnow(),
        "ip_address": get_client_ip()
    })
```

---

## 9. Implementation Checklist

### Phase 1: Backend Foundation

- [ ] Set up FastAPI with Claude integration
- [ ] Create `sociometry_chat_service.py`
- [ ] Define initial tools (3-4 core tools)
- [ ] Create API endpoint `/api/v1/insights/chat`
- [ ] Add authentication and role-based access
- [ ] Configure environment variables

### Phase 2: Database Integration

- [ ] Design sociometry data schema
- [ ] Create database queries for each tool
- [ ] Add appropriate indexes for performance
- [ ] Implement data aggregation functions
- [ ] Add privacy-preserving queries

### Phase 3: Frontend

- [ ] Create chat widget component
- [ ] Implement network graph visualization
- [ ] Add quick action buttons
- [ ] Handle loading and error states
- [ ] Mobile responsiveness

### Phase 4: Safety & Ethics

- [ ] Implement response sanitization
- [ ] Add content filtering
- [ ] Create audit logging
- [ ] Role-based tool access
- [ ] Privacy compliance review

### Phase 5: Testing & Refinement

- [ ] Test with various query types
- [ ] Refine system prompt based on results
- [ ] Adjust tool descriptions
- [ ] Performance optimization
- [ ] Cost monitoring

---

## Summary

The AI agent pattern used in Grana Platform is highly adaptable for SocialMap:

1. **Same Architecture**: Natural language → Claude → Tools → Database → Response
2. **Domain-Specific Tools**: Replace inventory tools with sociometry tools
3. **Ethical System Prompt**: Critical for working with minors
4. **Visualization Integration**: Network graphs instead of sales charts
5. **Role-Based Access**: Teachers, counselors, admins have different views
6. **Cost Management**: Use Haiku for quick queries, upgrade for complex analysis

The key difference is the **ethical layer**: SocialMap deals with sensitive data about minors, requiring careful attention to privacy, constructive language, and appropriate intervention suggestions.

---

*Document generated from Grana Platform AI implementation analysis.*
*For SocialMap implementation support, refer to the code examples above.*

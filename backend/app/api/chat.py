"""
API endpoint for inventory chat with Claude AI

Endpoint:
- POST /api/v1/inventory/chat - Process natural language inventory queries

Author: TM3
Date: 2025-11-24
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
import logging

from app.services.claude_chat_service import get_chat_service

logger = logging.getLogger(__name__)

# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory-chat"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ChatMessage(BaseModel):
    """A single message in the conversation history"""
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Request body for chat endpoint"""
    message: str = Field(..., min_length=1, max_length=1000, description="User's question")
    history: List[ChatMessage] = Field(default=[], description="Conversation history")


class ChatResponse(BaseModel):
    """Response from chat endpoint"""
    success: bool
    response: str
    tools_used: List[str]
    model: str
    usage: dict
    timestamp: str


# ============================================================================
# ENDPOINT: POST /api/v1/inventory/chat
# ============================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process a natural language query about inventory or sales.

    The AI assistant can answer questions about:
    - Inventory levels across warehouses
    - Product stock by SKU or name
    - Expiring products and alerts
    - Sales by product or channel
    - Stock vs sales velocity analysis

    Examples:
    - "Cuanto stock total tenemos?"
    - "Que productos estan por vencer?"
    - "Cuales son los productos mas vendidos este mes?"
    - "Que hay en la bodega de Packner?"

    Args:
        request: ChatRequest with message and optional history

    Returns:
        ChatResponse with AI-generated response
    """
    try:
        logger.info(f"Chat request received: {request.message[:50]}...")

        # Get chat service
        chat_service = get_chat_service()

        # Convert history to dict format
        history = [{"role": msg.role, "content": msg.content} for msg in request.history]

        # Process query
        result = chat_service.process_query(
            message=request.message,
            history=history
        )

        return ChatResponse(
            success=True,
            response=result.response,
            tools_used=result.tools_used,
            model=result.model,
            usage={
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "total_tokens": result.input_tokens + result.output_tokens,
                "estimated_cost_usd": result.estimated_cost_usd,
                "context_messages": result.context_messages
            },
            timestamp=datetime.utcnow().isoformat() + "Z"
        )

    except ValueError as e:
        # API key not configured
        logger.error(f"Configuration error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Chat service not configured. Please contact administrator."
        )

    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat: {str(e)}"
        )


# ============================================================================
# ENDPOINT: GET /api/v1/inventory/chat/health
# ============================================================================

@router.get("/chat/health")
async def chat_health():
    """
    Health check for chat service.

    Returns service status and configuration info.
    """
    try:
        import os

        api_key_configured = bool(os.getenv("ANTHROPIC_API_KEY"))
        model = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

        return {
            "status": "healthy" if api_key_configured else "not_configured",
            "api_key_configured": api_key_configured,
            "model": model,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

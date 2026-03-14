"""WebSocket endpoint for real-time document processing updates."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import ws_manager

logger = structlog.get_logger("ws_api")
router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/processing")
async def processing_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time document processing status.

    Clients connect with a JWT token as query parameter:
        ws://host/ws/processing?token=<jwt>

    The server authenticates the token, then sends processing events
    scoped to the user's tenant.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        user_id, tenant_id = await ws_manager.connect(websocket, token)
    except WebSocketDisconnect:
        return

    try:
        # Keep connection alive — client messages are ignored
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket, tenant_id)
        logger.info(
            "ws_disconnected",
            user_id=str(user_id),
            tenant_id=str(tenant_id),
        )

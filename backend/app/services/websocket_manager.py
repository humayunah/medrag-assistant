"""WebSocket connection manager for real-time document processing updates.

Provides tenant-scoped WebSocket connections with JWT authentication,
heartbeat keep-alive, and broadcast capabilities.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Final

import structlog
from fastapi import WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt

from app.core.config import settings

logger = structlog.get_logger(__name__)

_HEARTBEAT_INTERVAL_S: Final[float] = 30.0


class WebSocketManager:
    """Manages WebSocket connections grouped by tenant."""

    def __init__(self) -> None:
        # tenant_id -> set of active WebSocket connections
        self._connections: dict[uuid.UUID, set[WebSocket]] = {}
        # websocket -> asyncio task for its heartbeat
        self._heartbeat_tasks: dict[WebSocket, asyncio.Task[None]] = {}

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    @staticmethod
    def _authenticate_token(token: str) -> tuple[uuid.UUID, uuid.UUID]:
        """Verify a JWT and extract user_id and tenant_id.

        Returns:
            (user_id, tenant_id)

        Raises:
            ValueError: If the token is invalid, expired, or missing claims.
        """
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        except JWTError as exc:
            raise ValueError(f"JWT decode failed: {exc}") from exc

        sub = payload.get("sub")
        if not sub:
            raise ValueError("Token missing subject claim")

        app_metadata = payload.get("app_metadata", {})
        tenant_id_raw = app_metadata.get("tenant_id")
        if not tenant_id_raw:
            raise ValueError("Token missing tenant context")

        user_id = uuid.UUID(sub)
        tenant_id = (
            uuid.UUID(tenant_id_raw)
            if isinstance(tenant_id_raw, str)
            else uuid.UUID(str(tenant_id_raw))
        )
        return user_id, tenant_id

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(
        self, websocket: WebSocket, token: str
    ) -> tuple[uuid.UUID, uuid.UUID]:
        """Authenticate and register a WebSocket connection.

        Accepts the WebSocket handshake, verifies the JWT supplied via the
        ``token`` query parameter, and starts a background heartbeat task.

        Returns:
            (user_id, tenant_id)

        Raises:
            WebSocketDisconnect: If authentication fails (the socket is closed
                with code 4001 before the exception propagates).
        """
        try:
            user_id, tenant_id = self._authenticate_token(token)
        except ValueError as exc:
            logger.warning("ws_auth_failed", error=str(exc))
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            raise WebSocketDisconnect(code=status.WS_1008_POLICY_VIOLATION) from exc

        await websocket.accept()

        # Register in tenant group
        if tenant_id not in self._connections:
            self._connections[tenant_id] = set()
        self._connections[tenant_id].add(websocket)

        # Start heartbeat
        task = asyncio.create_task(self._heartbeat(websocket, tenant_id))
        self._heartbeat_tasks[websocket] = task

        logger.info(
            "ws_connected",
            user_id=str(user_id),
            tenant_id=str(tenant_id),
            active_connections=len(self._connections[tenant_id]),
        )
        return user_id, tenant_id

    def disconnect(self, websocket: WebSocket, tenant_id: uuid.UUID) -> None:
        """Remove a WebSocket connection and cancel its heartbeat task."""
        # Cancel heartbeat
        task = self._heartbeat_tasks.pop(websocket, None)
        if task is not None and not task.done():
            task.cancel()

        # Remove from tenant group
        tenant_connections = self._connections.get(tenant_id)
        if tenant_connections is not None:
            tenant_connections.discard(websocket)
            if not tenant_connections:
                del self._connections[tenant_id]

        logger.info(
            "ws_disconnected",
            tenant_id=str(tenant_id),
            active_connections=len(self._connections.get(tenant_id, set())),
        )

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    async def broadcast_to_tenant(self, tenant_id: uuid.UUID, message: dict) -> None:
        """Send a JSON message to every connection in a tenant.

        Stale connections that fail during send are automatically cleaned up.
        """
        connections = self._connections.get(tenant_id)
        if not connections:
            return

        stale: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                logger.debug("ws_send_failed", tenant_id=str(tenant_id))
                stale.append(ws)

        # Clean up any broken connections discovered during broadcast
        for ws in stale:
            self.disconnect(ws, tenant_id)

    async def send_processing_update(
        self,
        tenant_id: uuid.UUID,
        document_id: uuid.UUID,
        status: str,
        progress: float,
        message: str,
    ) -> None:
        """Send a document processing status update to all tenant connections.

        The event payload follows the canonical format::

            {
                "type": "processing_status",
                "document_id": "<uuid>",
                "status": "<status>",
                "progress": <0.0-1.0>,
                "message": "<human-readable message>",
                "timestamp": "<ISO-8601 UTC>"
            }
        """
        event: dict = {
            "type": "processing_status",
            "document_id": str(document_id),
            "status": status,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await self.broadcast_to_tenant(tenant_id, event)

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    async def _heartbeat(self, websocket: WebSocket, tenant_id: uuid.UUID) -> None:
        """Periodically send a ping frame to keep the connection alive.

        Runs until the connection is closed or an error occurs, at which point
        the connection is cleaned up automatically.
        """
        try:
            while True:
                await asyncio.sleep(_HEARTBEAT_INTERVAL_S)
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    logger.debug("ws_heartbeat_failed", tenant_id=str(tenant_id))
                    break
        except asyncio.CancelledError:
            # Task was cancelled during disconnect — nothing to clean up.
            return

        # If we broke out of the loop due to a send failure, clean up.
        self.disconnect(websocket, tenant_id)


# Module-level singleton
ws_manager = WebSocketManager()

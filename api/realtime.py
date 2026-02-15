"""WebSocket connection manager for live alert broadcasts."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket

from src.utils import get_logger


logger = get_logger("ids.ws")


class WebSocketManager:
    def __init__(self):
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, subprotocol: str | None = None) -> None:
        if subprotocol is not None:
            await websocket.accept(subprotocol=subprotocol)
        else:
            await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
        logger.info(f"ws connected — total={len(self._clients)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info(f"ws disconnected — total={len(self._clients)}")

    async def disconnect_all(self) -> None:
        async with self._lock:
            clients = list(self._clients)
            self._clients.clear()
        for c in clients:
            try:
                await c.close()
            except Exception:
                pass

    async def broadcast(self, payload: dict[str, Any]) -> None:
        """Fire-and-forget broadcast; dead sockets are pruned silently."""
        if not self._clients:
            return
        data = json.dumps(payload, default=str)
        async with self._lock:
            clients = list(self._clients)
        dead: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)


ws_manager = WebSocketManager()

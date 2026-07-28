"""In-process WebSocket connection manager."""
from typing import Dict, Set
from fastapi import WebSocket
import asyncio
import json


class ConnectionManager:
    def __init__(self):
        self._by_user: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        async with self._lock:
            self._by_user.setdefault(user_id, set()).add(ws)

    async def disconnect(self, user_id: str, ws: WebSocket):
        async with self._lock:
            if user_id in self._by_user:
                self._by_user[user_id].discard(ws)
                if not self._by_user[user_id]:
                    self._by_user.pop(user_id, None)

    async def send_to_user(self, user_id: str, payload: dict):
        sockets = list(self._by_user.get(user_id, set()))
        for ws in sockets:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                # silently drop broken sockets
                await self.disconnect(user_id, ws)

    async def send_to_users(self, user_ids, payload: dict):
        for uid in user_ids:
            await self.send_to_user(uid, payload)


manager = ConnectionManager()

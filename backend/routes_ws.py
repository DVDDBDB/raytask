"""WebSocket endpoint for real-time chat & notifications."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from ws_manager import manager
from auth import decode_token
from db import db

router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket, token: str = Query("")):
    payload = decode_token(token)
    if not payload:
        await ws.accept()
        await ws.close(code=4401)
        return
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user or user.get("status") != "active":
        await ws.accept()
        await ws.close(code=4403)
        return
    user_id = user["id"]
    await manager.connect(user_id, ws)
    try:
        await ws.send_json({"type": "ready", "user_id": user_id})
        while True:
            # We use client → server messages only for ping/pong keep-alive.
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(user_id, ws)

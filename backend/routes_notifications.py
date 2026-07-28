"""Notification & activity log routes."""
from fastapi import APIRouter, Depends
from auth import get_current_user, require_roles
from db import db
from utils import now_iso

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(user=Depends(get_current_user)):
    items = await db.notifications.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    unread = sum(1 for i in items if not i.get("read"))
    return {"items": items, "unread": unread}


@router.post("/{notif_id}/read")
async def mark_read(notif_id: str, user=Depends(get_current_user)):
    await db.notifications.update_one({"id": notif_id, "user_id": user["id"]}, {"$set": {"read": True}})
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(user=Depends(get_current_user)):
    await db.notifications.update_many({"user_id": user["id"]}, {"$set": {"read": True}})
    return {"ok": True}


activity_router = APIRouter(prefix="/activity", tags=["activity"])


@activity_router.get("")
async def list_activity(limit: int = 200, user=Depends(require_roles("super_admin", "admin"))):
    items = await db.activity_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return items

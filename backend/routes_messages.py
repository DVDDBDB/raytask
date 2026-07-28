"""Messaging routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from models import MessageCreate, ConversationCreate
from auth import get_current_user
from db import db
from utils import now_iso, push_notification
import uuid

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("/conversations")
async def list_conversations(user=Depends(get_current_user)):
    convs = await db.conversations.find(
        {"participant_ids": user["id"]}, {"_id": 0}
    ).sort("updated_at", -1).to_list(200)
    # attach last message and participant details
    users = {u["id"]: u for u in await db.users.find(
        {}, {"_id": 0, "id": 1, "first_name": 1, "designation": 1, "avatar_url": 1}).to_list(500)}
    for c in convs:
        c["participants"] = [users.get(pid) for pid in c["participant_ids"] if users.get(pid)]
        last = await db.messages.find_one({"conversation_id": c["id"]}, {"_id": 0}, sort=[("created_at", -1)])
        c["last_message"] = last
        # unread count for current user
        c["unread_count"] = await db.messages.count_documents({
            "conversation_id": c["id"], "read_by": {"$nin": [user["id"]]},
            "sender_id": {"$ne": user["id"]},
        })
    return convs


@router.post("/conversations")
async def create_conversation(payload: ConversationCreate, user=Depends(get_current_user)):
    participant_ids = list(set(payload.participant_ids + [user["id"]]))
    # For 1-1, reuse existing
    if len(participant_ids) == 2:
        existing = await db.conversations.find_one({
            "participant_ids": {"$all": participant_ids, "$size": 2},
        }, {"_id": 0})
        if existing:
            return existing
    doc = {
        "id": uuid.uuid4().hex,
        "name": payload.name,
        "participant_ids": participant_ids,
        "is_group": len(participant_ids) > 2,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.conversations.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/{conversation_id}")
async def get_messages(conversation_id: str, since: str = "", user=Depends(get_current_user)):
    conv = await db.conversations.find_one({"id": conversation_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if user["id"] not in conv["participant_ids"]:
        raise HTTPException(status_code=403, detail="Not a participant")
    q = {"conversation_id": conversation_id}
    if since:
        q["created_at"] = {"$gt": since}
    msgs = await db.messages.find(q, {"_id": 0}).sort("created_at", 1).to_list(1000)
    # Mark as read
    await db.messages.update_many(
        {"conversation_id": conversation_id, "read_by": {"$nin": [user["id"]]}},
        {"$addToSet": {"read_by": user["id"]}},
    )
    return msgs


@router.post("")
async def send_message(payload: MessageCreate, user=Depends(get_current_user)):
    conv_id = payload.conversation_id
    if not conv_id:
        # create new conversation
        participant_ids = list(set(payload.recipient_ids + [user["id"]]))
        conv = None
        if len(participant_ids) == 2:
            conv = await db.conversations.find_one({
                "participant_ids": {"$all": participant_ids, "$size": 2},
            })
        if not conv:
            conv = {
                "id": uuid.uuid4().hex,
                "name": "",
                "participant_ids": participant_ids,
                "is_group": len(participant_ids) > 2,
                "created_at": now_iso(),
                "updated_at": now_iso(),
            }
            await db.conversations.insert_one(conv)
        conv_id = conv["id"]
    conv = await db.conversations.find_one({"id": conv_id})
    if not conv or user["id"] not in conv["participant_ids"]:
        raise HTTPException(status_code=403, detail="Not a participant")
    msg = {
        "id": uuid.uuid4().hex,
        "conversation_id": conv_id,
        "sender_id": user["id"],
        "sender_first_name": user["first_name"],
        "sender_designation": user["designation"],
        "sender_avatar_url": user.get("avatar_url", ""),
        "body": payload.body,
        "attachments": payload.attachments,
        "tagged_task_id": payload.tagged_task_id,
        "tagged_project_id": payload.tagged_project_id,
        "read_by": [user["id"]],
        "created_at": now_iso(),
    }
    await db.messages.insert_one(msg)
    await db.conversations.update_one({"id": conv_id}, {"$set": {"updated_at": now_iso()}})
    # notify other participants
    for pid in conv["participant_ids"]:
        if pid != user["id"]:
            await push_notification(pid, "new_message",
                                    f"New message from {user['first_name']}",
                                    payload.body[:80],
                                    link_type="conversation", link_id=conv_id)
    msg.pop("_id", None)
    return msg

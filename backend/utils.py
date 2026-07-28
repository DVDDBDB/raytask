"""Shared utility helpers."""
from datetime import datetime, timezone
from db import db


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def strip_id(doc):
    if not doc:
        return doc
    doc.pop("_id", None)
    return doc


async def log_activity(actor: dict, action: str, target_type: str, target_id: str,
                       previous=None, new=None, reason: str = "", task_id: str = None):
    await db.activity_logs.insert_one({
        "id": __import__("uuid").uuid4().hex,
        "action": action,
        "actor_id": actor.get("id"),
        "actor_name": f"{actor.get('first_name', '')} {actor.get('last_name', '')}".strip(),
        "actor_designation": actor.get("designation", ""),
        "actor_role": actor.get("role"),
        "target_type": target_type,
        "target_id": target_id,
        "task_id": task_id,
        "previous_value": previous,
        "new_value": new,
        "reason": reason,
        "created_at": now_iso(),
    })


async def push_notification(user_id: str, kind: str, title: str, body: str,
                            link_type: str = "", link_id: str = ""):
    await db.notifications.insert_one({
        "id": __import__("uuid").uuid4().hex,
        "user_id": user_id,
        "kind": kind,
        "title": title,
        "body": body,
        "link_type": link_type,
        "link_id": link_id,
        "read": False,
        "created_at": now_iso(),
    })


def format_user_label(u: dict) -> str:
    """Employee First Name — Designation"""
    return f"{u.get('first_name', '')} — {u.get('designation', 'Other')}"

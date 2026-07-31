"""Recurring-task scheduler.

Runs every 5 minutes as a background asyncio task. For every task with
`recurrence.enabled == True` and `recurrence.next_run_at <= now`, it clones
the task (title/description/assignee/priority/etc.) into a new Task with
status='Assigned' and recomputes the next `next_run_at`.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from db import db
from utils import now_iso, push_notification

logger = logging.getLogger("raybotix.recurring")


def _iso_to_dt(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def compute_next_run(rec: dict, from_dt: datetime) -> datetime:
    """Given a recurrence config and a base datetime, return the next occurrence."""
    freq = rec.get("frequency", "weekly")
    if freq == "daily":
        return from_dt + timedelta(days=1)
    if freq == "monthly":
        # step 30 days for simplicity
        return from_dt + timedelta(days=30)
    # weekly
    return from_dt + timedelta(days=7)


async def _spawn_from(template: dict):
    """Clone a recurring-template task into a fresh assigned task."""
    now = now_iso()
    new_task = {
        "id": uuid.uuid4().hex,
        "title": template.get("title", ""),
        "description": template.get("description", ""),
        "project_id": template.get("project_id"),
        "assignee_id": template.get("assignee_id"),
        "creator_id": template.get("creator_id"),
        "priority": template.get("priority", "Medium"),
        "status": "Assigned",
        "estimated_duration_minutes": template.get("estimated_duration_minutes", 60),
        "tags": template.get("tags", []),
        "instructions": template.get("instructions", ""),
        "reference_links": template.get("reference_links", []),
        "attachments": template.get("attachments", []),
        "scheduled_start_date": now,
        "due_date": (datetime.now(timezone.utc) + timedelta(
            minutes=template.get("estimated_duration_minutes", 60) or 60,
        )).isoformat(),
        "parent_task_id": template.get("id"),
        "recurrence": None,
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "review_status": None,
        "workflow": [],
        "reassignment_history": [],
        "spawned_from_recurring": template.get("id"),
    }
    if template.get("assignee_id"):
        assignee = await db.users.find_one({"id": template["assignee_id"]}, {"_id": 0})
        if assignee:
            new_task["workflow"] = [{
                "user_id": assignee["id"],
                "first_name": assignee["first_name"],
                "designation": assignee["designation"],
                "avatar_url": assignee.get("avatar_url", ""),
                "assigned_at": now,
                "handoff_remarks": f"Auto-created from recurring: {template.get('title', '')}",
                "status": "assigned",
            }]
            await push_notification(
                assignee["id"], "task_assigned",
                "Recurring task ready",
                new_task["title"],
                link_type="task", link_id=new_task["id"],
            )
    await db.tasks.insert_one(new_task)
    return new_task


async def _tick():
    now = datetime.now(timezone.utc)
    templates = await db.tasks.find(
        {"recurrence.enabled": True}, {"_id": 0}
    ).to_list(500)
    for t in templates:
        rec = t.get("recurrence") or {}
        nxt = _iso_to_dt(rec.get("next_run_at"))
        if nxt and nxt > now:
            continue
        try:
            await _spawn_from(t)
        except Exception as e:
            logger.exception("Failed to spawn recurring task %s: %s", t.get("id"), e)
            continue
        new_next = compute_next_run(rec, nxt or now)
        await db.tasks.update_one(
            {"id": t["id"]},
            {"$set": {"recurrence.next_run_at": new_next.isoformat(),
                      "recurrence.last_run_at": now.isoformat()}},
        )
    return len(templates)


async def loop(interval_seconds: int = 300):
    while True:
        try:
            await _tick()
        except Exception as e:
            logger.exception("Recurring tick failed: %s", e)
        await asyncio.sleep(interval_seconds)


_scheduler_task = None


def start_scheduler(loop_object):
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        return
    _scheduler_task = loop_object.create_task(loop())

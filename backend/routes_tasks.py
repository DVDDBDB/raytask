"""Task routes: CRUD, timer, handoff, workflow, review."""
from fastapi import APIRouter, Depends, HTTPException, Query
from models import TaskCreate, TaskUpdate, HandoffRequest, ReopenRequest, ReviewRequest
from auth import get_current_user, require_roles, can_see_costs
from db import db
from utils import now_iso, log_activity, push_notification
from datetime import datetime, timezone
import uuid

router = APIRouter(prefix="/tasks", tags=["tasks"])


PRIORITY_ORDER = {"Urgent": 0, "Medium": 1, "Low": 2}


def _iso_to_dt(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        # If naive (e.g. from HTML datetime-local input), assume UTC so
        # downstream comparisons with timezone-aware datetimes don't blow up.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


async def _enrich_tasks(tasks, user):
    users = {u["id"]: u for u in await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(500)}
    projects = {p["id"]: p for p in await db.projects.find({}, {"_id": 0}).to_list(500)}
    # timer aggregation per task
    sessions_by_task = {}
    task_ids = [t["id"] for t in tasks]
    if task_ids:
        sess = await db.timer_sessions.find({"task_id": {"$in": task_ids}}, {"_id": 0}).to_list(50000)
        for s in sess:
            sessions_by_task.setdefault(s["task_id"], []).append(s)
    for t in tasks:
        a = users.get(t.get("assignee_id"))
        t["assignee"] = {
            "id": a["id"], "first_name": a["first_name"], "designation": a["designation"],
            "avatar_url": a.get("avatar_url", ""),
        } if a else None
        c = users.get(t.get("creator_id"))
        t["creator"] = {
            "id": c["id"], "first_name": c["first_name"], "designation": c["designation"],
        } if c else None
        p = projects.get(t.get("project_id"))
        t["project"] = {
            "id": p["id"], "name": p["name"], "company_name": p.get("company_name", ""),
        } if p else None
        # Total team time (all sessions)
        sess = sessions_by_task.get(t["id"], [])
        total_seconds = sum(s.get("duration_seconds", 0) for s in sess)
        # Currently running session for assignee
        active_session = None
        for s in sess:
            if s.get("ended_at") is None:
                active_session = s
                break
        if active_session:
            started = _iso_to_dt(active_session["started_at"])
            if started:
                elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                total_seconds += int(elapsed)
        t["total_team_seconds"] = int(total_seconds)
        t["active_session"] = active_session
        # Compute cost only for admins
        if can_see_costs(user):
            cost = 0.0
            for s in sess:
                u = users.get(s.get("user_id"))
                if not u:
                    continue
                wh = u.get("working_hours_per_day", 8) or 8
                wd = u.get("working_days_per_month", 25) or 25
                salary = u.get("monthly_salary", 0) or 0
                mh = wh * wd
                if mh:
                    hourly = salary / mh
                    cost += (s.get("duration_seconds", 0) / 3600.0) * hourly
            t["cost"] = round(cost, 2)
    return tasks


@router.get("")
async def list_tasks(
    scope: str = Query("all"),
    project_id: str = "",
    assignee_id: str = "",
    status: str = "",
    priority: str = "",
    search: str = "",
    user=Depends(get_current_user),
):
    q = {}
    if scope == "mine":
        q["assignee_id"] = user["id"]
    if project_id:
        q["project_id"] = project_id
    if assignee_id:
        q["assignee_id"] = assignee_id
    if status:
        q["status"] = status
    if priority:
        q["priority"] = priority
    if search:
        q["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]
    tasks = await db.tasks.find(q, {"_id": 0}).to_list(2000)
    # Sort by priority then due_date then created_at
    tasks.sort(key=lambda t: (
        PRIORITY_ORDER.get(t.get("priority", "Medium"), 1),
        t.get("due_date") or "9999",
        t.get("created_at", ""),
    ))
    return await _enrich_tasks(tasks, user)


@router.post("")
async def create_task(payload: TaskCreate, user=Depends(get_current_user)):
    now = now_iso()
    doc = {
        "id": uuid.uuid4().hex,
        **payload.model_dump(),
        "creator_id": user["id"],
        "created_at": now,
        "updated_at": now,
        "completed_at": None,
        "review_status": "pending" if payload.status == "Waiting for Review" else None,
        "workflow": [],
        "reassignment_history": [],
    }
    # Seed recurrence next_run_at if enabled but unset
    if payload.recurrence and payload.recurrence.enabled and not payload.recurrence.next_run_at:
        from recurring import compute_next_run
        doc["recurrence"]["next_run_at"] = compute_next_run(payload.recurrence.model_dump(), datetime.now(timezone.utc)).isoformat()
    # If scheduled_start_date is in the future, mark as Scheduled
    sched = _iso_to_dt(payload.scheduled_start_date)
    if sched and sched > datetime.now(timezone.utc) and payload.status == "Assigned":
        doc["status"] = "Scheduled"
    await db.tasks.insert_one(doc)
    # Add initial workflow entry if assignee set
    if payload.assignee_id:
        assignee = await db.users.find_one({"id": payload.assignee_id}, {"_id": 0})
        if assignee:
            await db.tasks.update_one({"id": doc["id"]}, {"$push": {"workflow": {
                "user_id": assignee["id"],
                "first_name": assignee["first_name"],
                "designation": assignee["designation"],
                "avatar_url": assignee.get("avatar_url", ""),
                "assigned_at": now,
                "handoff_remarks": "",
                "status": "assigned",
            }}})
            await push_notification(
                assignee["id"], "task_assigned",
                "New task assigned", payload.title,
                link_type="task", link_id=doc["id"],
            )
    await log_activity(user, "task_created", "task", doc["id"],
                       new=payload.title, task_id=doc["id"])
    doc.pop("_id", None)
    return doc


@router.get("/{task_id}")
async def get_task(task_id: str, user=Depends(get_current_user)):
    t = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    enriched = await _enrich_tasks([t], user)
    # timer sessions
    sessions = await db.timer_sessions.find({"task_id": task_id}, {"_id": 0}).sort("started_at", 1).to_list(500)
    # comments
    comments = await db.task_comments.find({"task_id": task_id}, {"_id": 0}).sort("created_at", 1).to_list(500)
    # children
    children = await db.tasks.find({"parent_task_id": task_id}, {"_id": 0}).to_list(100)
    # parent
    parent = None
    if t.get("parent_task_id"):
        parent = await db.tasks.find_one({"id": t["parent_task_id"]}, {"_id": 0, "id": 1, "title": 1, "status": 1})
    result = enriched[0]
    result["timer_sessions"] = sessions
    result["comments"] = comments
    result["children"] = children
    result["parent"] = parent
    return result


@router.patch("/{task_id}")
async def update_task(task_id: str, payload: TaskUpdate, user=Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    # Regular users can update only their own tasks (limited fields)
    if user["role"] == "team_member" and task.get("assignee_id") != user["id"] and task.get("creator_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to modify this task")
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    # Track reassignment history if assignee changed
    if "assignee_id" in update and update["assignee_id"] != task.get("assignee_id"):
        prev = await db.users.find_one({"id": task.get("assignee_id")}, {"first_name": 1, "designation": 1, "id": 1})
        new = await db.users.find_one({"id": update["assignee_id"]}, {"first_name": 1, "designation": 1, "id": 1})
        history_entry = {
            "changed_by": user["id"],
            "changed_by_name": user.get("first_name", ""),
            "changed_at": now_iso(),
            "previous_id": task.get("assignee_id"),
            "previous_name": (prev or {}).get("first_name", ""),
            "new_id": update["assignee_id"],
            "new_name": (new or {}).get("first_name", ""),
            "reason": "manual_reassignment",
        }
        await db.tasks.update_one({"id": task_id}, {"$push": {"reassignment_history": history_entry}})
        if new:
            await push_notification(new["id"], "task_reassigned", "Task assigned to you",
                                    task["title"], link_type="task", link_id=task_id)
    update["updated_at"] = now_iso()
    await db.tasks.update_one({"id": task_id}, {"$set": update})
    await log_activity(user, "task_updated", "task", task_id, new=update, task_id=task_id)
    return {"ok": True}


@router.delete("/{task_id}")
async def delete_task(task_id: str, user=Depends(require_roles("super_admin", "admin"))):
    await db.tasks.update_one({"id": task_id}, {"$set": {"status": "Cancelled", "deleted": True, "updated_at": now_iso()}})
    await log_activity(user, "task_deleted", "task", task_id, task_id=task_id)
    return {"ok": True}


# ---------- Timer endpoints ----------
@router.post("/{task_id}/start")
async def start_task(task_id: str, user=Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.get("assignee_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only the assignee can start this task")
    # Check settings for allow_multiple_active_timers
    settings = await db.settings.find_one({"id": "company"}) or {}
    if not settings.get("allow_multiple_active_timers", False):
        active = await db.timer_sessions.find_one({"user_id": user["id"], "ended_at": None})
        if active and active.get("task_id") != task_id:
            raise HTTPException(
                status_code=400,
                detail="You already have an active task. Pause or complete the current task before starting another task.",
            )
    # if session already active for this task, ignore
    existing = await db.timer_sessions.find_one({"task_id": task_id, "user_id": user["id"], "ended_at": None})
    if not existing:
        session_doc = {
            "id": uuid.uuid4().hex,
            "task_id": task_id,
            "user_id": user["id"],
            "user_first_name": user["first_name"],
            "user_designation": user["designation"],
            "started_at": now_iso(),
            "ended_at": None,
            "duration_seconds": 0,
            "paused": False,
        }
        await db.timer_sessions.insert_one(session_doc)
    await db.tasks.update_one({"id": task_id}, {"$set": {"status": "In Progress", "updated_at": now_iso()}})
    await log_activity(user, "task_started", "task", task_id, task_id=task_id)
    return {"ok": True}


@router.post("/{task_id}/pause")
async def pause_task(task_id: str, user=Depends(get_current_user)):
    session = await db.timer_sessions.find_one({"task_id": task_id, "user_id": user["id"], "ended_at": None})
    if not session:
        raise HTTPException(status_code=400, detail="No active timer")
    started = _iso_to_dt(session["started_at"])
    duration = int((datetime.now(timezone.utc) - started).total_seconds()) + session.get("duration_seconds", 0)
    await db.timer_sessions.update_one(
        {"id": session["id"]},
        {"$set": {"ended_at": now_iso(), "duration_seconds": duration}},
    )
    await db.tasks.update_one({"id": task_id}, {"$set": {"status": "Paused", "updated_at": now_iso()}})
    await log_activity(user, "task_paused", "task", task_id, task_id=task_id)
    return {"ok": True}


@router.post("/{task_id}/resume")
async def resume_task(task_id: str, user=Depends(get_current_user)):
    return await start_task(task_id, user)


@router.post("/{task_id}/complete")
async def complete_task(task_id: str, user=Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    # End any active session by this user
    session = await db.timer_sessions.find_one({"task_id": task_id, "user_id": user["id"], "ended_at": None})
    if session:
        started = _iso_to_dt(session["started_at"])
        duration = int((datetime.now(timezone.utc) - started).total_seconds()) + session.get("duration_seconds", 0)
        await db.timer_sessions.update_one(
            {"id": session["id"]},
            {"$set": {"ended_at": now_iso(), "duration_seconds": duration}},
        )
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {"status": "Completed", "completed_at": now_iso(), "updated_at": now_iso()}},
    )
    # Mark current workflow step as completed
    await db.tasks.update_one(
        {"id": task_id, "workflow.user_id": user["id"], "workflow.status": {"$ne": "completed"}},
        {"$set": {"workflow.$.status": "completed", "workflow.$.completed_at": now_iso()}},
    )
    # Notify creator
    if task.get("creator_id") and task["creator_id"] != user["id"]:
        await push_notification(task["creator_id"], "task_completed",
                                "Task completed", task["title"],
                                link_type="task", link_id=task_id)
    await log_activity(user, "task_completed", "task", task_id, task_id=task_id)
    return {"ok": True}


@router.post("/{task_id}/handoff")
async def handoff_task(task_id: str, payload: HandoffRequest, user=Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    next_user = await db.users.find_one({"id": payload.next_assignee_id})
    if not next_user:
        raise HTTPException(status_code=404, detail="Next assignee not found")

    # Close current session
    session = await db.timer_sessions.find_one({"task_id": task_id, "user_id": user["id"], "ended_at": None})
    if session:
        started = _iso_to_dt(session["started_at"])
        duration = int((datetime.now(timezone.utc) - started).total_seconds()) + session.get("duration_seconds", 0)
        await db.timer_sessions.update_one(
            {"id": session["id"]},
            {"$set": {"ended_at": now_iso(), "duration_seconds": duration}},
        )

    if payload.create_next_task and payload.next_task:
        # Create a new linked task
        nt = payload.next_task.model_dump()
        nt["parent_task_id"] = task_id
        nt["creator_id"] = user["id"]
        nt["id"] = uuid.uuid4().hex
        nt["created_at"] = now_iso()
        nt["updated_at"] = now_iso()
        nt["completed_at"] = None
        nt["assignee_id"] = payload.next_assignee_id
        nt["review_status"] = None
        nt["workflow"] = [{
            "user_id": next_user["id"],
            "first_name": next_user["first_name"],
            "designation": next_user["designation"],
            "avatar_url": next_user.get("avatar_url", ""),
            "assigned_at": now_iso(),
            "handoff_remarks": payload.remarks,
            "status": "assigned",
        }]
        nt["reassignment_history"] = []
        # Mark current task as completed
        await db.tasks.update_one({"id": task_id}, {"$set": {
            "status": "Completed", "completed_at": now_iso(), "updated_at": now_iso()
        }})
        await db.tasks.update_one(
            {"id": task_id, "workflow.user_id": user["id"], "workflow.status": {"$ne": "completed"}},
            {"$set": {"workflow.$.status": "completed", "workflow.$.completed_at": now_iso(),
                      "workflow.$.handoff_remarks": payload.remarks}},
        )
        await db.tasks.insert_one(nt)
        await push_notification(next_user["id"], "next_task_created",
                                "New workflow task assigned", nt.get("title", ""),
                                link_type="task", link_id=nt["id"])
        await log_activity(user, "next_task_created", "task", nt["id"], task_id=task_id)
        nt.pop("_id", None)
        return {"ok": True, "next_task_id": nt["id"], "task": nt}
    else:
        # Continue same task: reassign to next
        await db.tasks.update_one(
            {"id": task_id, "workflow.user_id": user["id"], "workflow.status": {"$ne": "completed"}},
            {"$set": {"workflow.$.status": "completed", "workflow.$.completed_at": now_iso(),
                      "workflow.$.handoff_remarks": payload.remarks}},
        )
        await db.tasks.update_one({"id": task_id}, {
            "$set": {"assignee_id": payload.next_assignee_id, "status": "Assigned", "updated_at": now_iso()},
            "$push": {
                "workflow": {
                    "user_id": next_user["id"],
                    "first_name": next_user["first_name"],
                    "designation": next_user["designation"],
                    "avatar_url": next_user.get("avatar_url", ""),
                    "assigned_at": now_iso(),
                    "handoff_remarks": payload.remarks,
                    "status": "assigned",
                },
                "reassignment_history": {
                    "changed_by": user["id"],
                    "changed_by_name": user.get("first_name", ""),
                    "changed_at": now_iso(),
                    "previous_id": user["id"],
                    "previous_name": user.get("first_name", ""),
                    "new_id": next_user["id"],
                    "new_name": next_user["first_name"],
                    "reason": payload.remarks or "handoff",
                },
            },
        })
        await push_notification(next_user["id"], "task_handoff",
                                "Task handed off to you", task["title"],
                                link_type="task", link_id=task_id)
        await log_activity(user, "task_handoff", "task", task_id,
                           new=payload.next_assignee_id, task_id=task_id, reason=payload.remarks)
        return {"ok": True}


@router.post("/{task_id}/reopen")
async def reopen_task(task_id: str, payload: ReopenRequest,
                      user=Depends(require_roles("super_admin", "admin", "manager"))):
    next_user = await db.users.find_one({"id": payload.assignee_id})
    if not next_user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.tasks.update_one({"id": task_id}, {
        "$set": {
            "status": "Reopened",
            "assignee_id": payload.assignee_id,
            "scheduled_start_date": payload.scheduled_start_date,
            "due_date": payload.due_date,
            "priority": payload.priority,
            "instructions": payload.instructions,
            "completed_at": None,
            "updated_at": now_iso(),
        },
        "$push": {"workflow": {
            "user_id": next_user["id"],
            "first_name": next_user["first_name"],
            "designation": next_user["designation"],
            "avatar_url": next_user.get("avatar_url", ""),
            "assigned_at": now_iso(),
            "handoff_remarks": f"Reopened: {payload.reason}",
            "status": "assigned",
        }},
    })
    await push_notification(next_user["id"], "task_reopened",
                            "Task reopened & assigned to you", payload.reason,
                            link_type="task", link_id=task_id)
    await log_activity(user, "task_reopened", "task", task_id, reason=payload.reason, task_id=task_id)
    return {"ok": True}


@router.post("/{task_id}/review")
async def review_task(task_id: str, payload: ReviewRequest,
                      user=Depends(require_roles("super_admin", "admin", "manager"))):
    status_map = {"approve": "Approved", "request_changes": "Changes Requested", "reopen": "Reopened"}
    if payload.action not in status_map:
        raise HTTPException(status_code=400, detail="Invalid action")
    task_status = "Completed" if payload.action == "approve" else "Reopened" if payload.action == "reopen" else "Waiting for Review"
    await db.tasks.update_one({"id": task_id}, {"$set": {
        "review_status": status_map[payload.action],
        "status": task_status,
        "updated_at": now_iso(),
    }})
    if payload.comment:
        await db.task_comments.insert_one({
            "id": uuid.uuid4().hex,
            "task_id": task_id,
            "user_id": user["id"],
            "user_first_name": user["first_name"],
            "user_designation": user["designation"],
            "body": payload.comment,
            "created_at": now_iso(),
            "kind": "review",
        })
    await log_activity(user, f"task_review_{payload.action}", "task", task_id, task_id=task_id)
    return {"ok": True}


@router.post("/{task_id}/comments")
async def add_comment(task_id: str, payload: dict, user=Depends(get_current_user)):
    body = payload.get("body", "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="Empty comment")
    doc = {
        "id": uuid.uuid4().hex,
        "task_id": task_id,
        "user_id": user["id"],
        "user_first_name": user["first_name"],
        "user_designation": user["designation"],
        "body": body,
        "created_at": now_iso(),
        "kind": "comment",
    }
    await db.task_comments.insert_one(doc)
    doc.pop("_id", None)
    return doc


# Endpoint to promote scheduled tasks whose scheduled_start_date has arrived
@router.post("/system/promote-scheduled")
async def promote_scheduled(user=Depends(get_current_user)):
    now = datetime.now(timezone.utc)
    tasks = await db.tasks.find({"status": "Scheduled"}, {"_id": 0}).to_list(1000)
    promoted = 0
    for t in tasks:
        sched = _iso_to_dt(t.get("scheduled_start_date"))
        if sched and sched <= now:
            await db.tasks.update_one({"id": t["id"]}, {"$set": {"status": "Assigned", "updated_at": now_iso()}})
            promoted += 1
    return {"promoted": promoted}

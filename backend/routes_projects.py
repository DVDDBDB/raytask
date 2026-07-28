"""Project routes."""
from fastapi import APIRouter, Depends, HTTPException
from models import ProjectCreate, ProjectUpdate
from auth import get_current_user, require_roles, can_see_costs
from db import db
from utils import now_iso, log_activity
import uuid

router = APIRouter(prefix="/projects", tags=["projects"])


async def compute_project_cost(project_id: str) -> dict:
    """Return dict {total, monthly} project cost using timer sessions and user hourly rates."""
    users = {u["id"]: u for u in await db.users.find({}, {"_id": 0}).to_list(500)}
    tasks = await db.tasks.find({"project_id": project_id}, {"_id": 0, "id": 1}).to_list(2000)
    task_ids = [t["id"] for t in tasks]
    if not task_ids:
        return {"total": 0, "monthly": 0}
    sessions = await db.timer_sessions.find(
        {"task_id": {"$in": task_ids}}, {"_id": 0}
    ).to_list(20000)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")
    total = 0.0
    monthly = 0.0
    for s in sessions:
        u = users.get(s.get("user_id"))
        if not u:
            continue
        wh = u.get("working_hours_per_day", 8) or 8
        wd = u.get("working_days_per_month", 25) or 25
        salary = u.get("monthly_salary", 0) or 0
        monthly_hours = wh * wd
        if monthly_hours == 0:
            continue
        hourly = salary / monthly_hours
        dur_hours = (s.get("duration_seconds", 0) or 0) / 3600.0
        cost = dur_hours * hourly
        total += cost
        started = s.get("started_at", "")
        if isinstance(started, str) and started.startswith(month_key):
            monthly += cost
    return {"total": round(total, 2), "monthly": round(monthly, 2)}


@router.get("")
async def list_projects(user=Depends(get_current_user)):
    projects = await db.projects.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    # aggregate task counts
    task_stats = await db.tasks.aggregate([
        {"$group": {
            "_id": "$project_id",
            "total": {"$sum": 1},
            "completed": {"$sum": {"$cond": [{"$eq": ["$status", "Completed"]}, 1, 0]}},
        }},
    ]).to_list(1000)
    stat_map = {s["_id"]: s for s in task_stats}
    for p in projects:
        s = stat_map.get(p["id"], {})
        p["total_tasks"] = s.get("total", 0)
        p["completed_tasks"] = s.get("completed", 0)
        p["pending_tasks"] = p["total_tasks"] - p["completed_tasks"]
        if can_see_costs(user):
            cost = await compute_project_cost(p["id"])
            p["total_cost"] = cost["total"]
            p["monthly_cost"] = cost["monthly"]
    return projects


@router.post("")
async def create_project(payload: ProjectCreate,
                         user=Depends(require_roles("super_admin", "admin", "manager"))):
    doc = {
        "id": uuid.uuid4().hex,
        **payload.model_dump(),
        "created_by": user["id"],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.projects.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user, "project_created", "project", doc["id"], new=payload.name)
    return doc


@router.get("/{project_id}")
async def get_project(project_id: str, user=Depends(get_current_user)):
    p = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    if can_see_costs(user):
        cost = await compute_project_cost(project_id)
        p["total_cost"] = cost["total"]
        p["monthly_cost"] = cost["monthly"]
    return p


@router.patch("/{project_id}")
async def update_project(project_id: str, payload: ProjectUpdate,
                         user=Depends(require_roles("super_admin", "admin", "manager"))):
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    update["updated_at"] = now_iso()
    await db.projects.update_one({"id": project_id}, {"$set": update})
    await log_activity(user, "project_updated", "project", project_id, new=update)
    return {"ok": True}


@router.delete("/{project_id}")
async def delete_project(project_id: str, user=Depends(require_roles("super_admin"))):
    await db.projects.delete_one({"id": project_id})
    await log_activity(user, "project_deleted", "project", project_id)
    return {"ok": True}

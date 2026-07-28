"""Analytics & cost routes."""
from fastapi import APIRouter, Depends, Query
from auth import get_current_user, require_roles, can_see_costs
from db import db
from datetime import datetime, timezone, timedelta

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _iso_to_dt(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


async def _employee_costs():
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(500)
    cost_map = {}
    for u in users:
        wh = u.get("working_hours_per_day", 8) or 8
        wd = u.get("working_days_per_month", 25) or 25
        salary = u.get("monthly_salary", 0) or 0
        monthly_hours = wh * wd
        hourly = (salary / monthly_hours) if monthly_hours else 0
        cost_map[u["id"]] = {
            "user": u,
            "hourly": hourly,
            "monthly_hours": monthly_hours,
        }
    return cost_map


@router.get("/dashboard")
async def dashboard(user=Depends(get_current_user)):
    """Role-aware dashboard summary."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0).isoformat()

    is_admin = user["role"] in ("super_admin", "admin")

    if is_admin:
        base = {}
    else:
        base = {"assignee_id": user["id"]}

    total = await db.tasks.count_documents(base)
    in_progress = await db.tasks.count_documents({**base, "status": "In Progress"})
    completed = await db.tasks.count_documents({**base, "status": "Completed"})
    overdue_q = {**base, "due_date": {"$lt": now.isoformat()},
                 "status": {"$nin": ["Completed", "Cancelled"]}}
    overdue = await db.tasks.count_documents(overdue_q)
    urgent = await db.tasks.count_documents({**base, "priority": "Urgent",
                                              "status": {"$nin": ["Completed", "Cancelled"]}})
    planned = await db.tasks.count_documents({**base, "status": {"$in": ["Planned", "Scheduled"]}})
    review = await db.tasks.count_documents({**base, "status": "Waiting for Review"})

    # Time worked today / week (from sessions)
    if is_admin:
        sess_q_today = {"started_at": {"$gte": today_start}}
        sess_q_week = {"started_at": {"$gte": week_start}}
    else:
        sess_q_today = {"user_id": user["id"], "started_at": {"$gte": today_start}}
        sess_q_week = {"user_id": user["id"], "started_at": {"$gte": week_start}}
    today_sess = await db.timer_sessions.find(sess_q_today, {"_id": 0}).to_list(5000)
    week_sess = await db.timer_sessions.find(sess_q_week, {"_id": 0}).to_list(20000)
    def _sess_seconds(sessions):
        total_sec = 0
        for s in sessions:
            if s.get("ended_at"):
                total_sec += s.get("duration_seconds", 0)
            else:
                started = _iso_to_dt(s["started_at"])
                if started:
                    total_sec += int((datetime.now(timezone.utc) - started).total_seconds()) + s.get("duration_seconds", 0)
        return total_sec

    today_seconds = _sess_seconds(today_sess)
    week_seconds = _sess_seconds(week_sess)

    # Productivity: today_seconds / (working_hours_per_day * 3600) * 100
    wh = user.get("working_hours_per_day", 8) or 8
    productivity_today = round(min(100, (today_seconds / (wh * 3600)) * 100), 1) if wh else 0

    result = {
        "total": total, "in_progress": in_progress, "completed": completed,
        "overdue": overdue, "urgent": urgent, "planned": planned, "review": review,
        "today_seconds": today_seconds, "week_seconds": week_seconds,
        "productivity_today": productivity_today,
    }

    if is_admin:
        # Add employee workload + total cost this month
        active_users = await db.users.count_documents({"status": "active"})
        active_timers = await db.timer_sessions.count_documents({"ended_at": None})
        result["active_users"] = active_users
        result["active_timers"] = active_timers
        # monthly cost
        cost_map = await _employee_costs()
        month_key = now.strftime("%Y-%m")
        month_sess = await db.timer_sessions.find({"started_at": {"$regex": f"^{month_key}"}}, {"_id": 0}).to_list(50000)
        total_cost = 0.0
        for s in month_sess:
            c = cost_map.get(s.get("user_id"))
            if c:
                total_cost += (s.get("duration_seconds", 0) / 3600.0) * c["hourly"]
        result["monthly_cost"] = round(total_cost, 2)

    return result


@router.get("/employee/{user_id}")
async def employee_analytics(user_id: str, user=Depends(get_current_user)):
    # Team members can only see their own
    if user["role"] == "team_member" and user_id != user["id"]:
        user_id = user["id"]
    now = datetime.now(timezone.utc)
    seven_days_ago = (now - timedelta(days=7)).isoformat()
    sessions = await db.timer_sessions.find({"user_id": user_id}, {"_id": 0}).to_list(20000)
    # Group by date
    by_date = {}
    total_seconds = 0
    for s in sessions:
        started = _iso_to_dt(s["started_at"])
        if not started:
            continue
        key = started.strftime("%Y-%m-%d")
        by_date[key] = by_date.get(key, 0) + s.get("duration_seconds", 0)
        total_seconds += s.get("duration_seconds", 0)
    daily = sorted(
        [{"date": k, "seconds": v, "hours": round(v / 3600, 2)} for k, v in by_date.items()],
        key=lambda x: x["date"], reverse=True,
    )[:30]
    # Completed vs reopened counts
    completed = await db.tasks.count_documents({"assignee_id": user_id, "status": "Completed"})
    reopened = await db.tasks.count_documents({"assignee_id": user_id, "status": "Reopened"})
    overdue = await db.tasks.count_documents({
        "assignee_id": user_id, "due_date": {"$lt": now.isoformat()},
        "status": {"$nin": ["Completed", "Cancelled"]},
    })
    return {
        "user_id": user_id,
        "total_seconds": total_seconds,
        "daily": list(reversed(daily)),
        "completed": completed,
        "reopened": reopened,
        "overdue": overdue,
    }


@router.get("/productivity")
async def productivity(user=Depends(require_roles("super_admin", "admin", "manager"))):
    """Productivity per employee for this month."""
    cost_map = await _employee_costs()
    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")
    sessions = await db.timer_sessions.find({"started_at": {"$regex": f"^{month_key}"}}, {"_id": 0}).to_list(50000)
    by_user = {}
    for s in sessions:
        by_user.setdefault(s["user_id"], 0)
        by_user[s["user_id"]] += s.get("duration_seconds", 0)
    result = []
    for uid, secs in by_user.items():
        info = cost_map.get(uid)
        if not info:
            continue
        u = info["user"]
        expected_seconds = info["monthly_hours"] * 3600 or 1
        result.append({
            "user_id": uid,
            "first_name": u["first_name"],
            "designation": u.get("designation", ""),
            "avatar_url": u.get("avatar_url", ""),
            "seconds": secs,
            "hours": round(secs / 3600, 2),
            "productivity": round(min(100, (secs / expected_seconds) * 100), 1),
            "hourly_cost": round(info["hourly"], 2),
            "monthly_cost": round((secs / 3600.0) * info["hourly"], 2),
        })
    result.sort(key=lambda r: r["productivity"], reverse=True)
    return result


@router.get("/costs")
async def costs(user=Depends(require_roles("super_admin", "admin"))):
    """Overall cost analytics for this month by project & designation."""
    cost_map = await _employee_costs()
    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")
    sessions = await db.timer_sessions.find({"started_at": {"$regex": f"^{month_key}"}}, {"_id": 0}).to_list(50000)
    task_ids = list({s["task_id"] for s in sessions})
    tasks_map = {t["id"]: t for t in await db.tasks.find({"id": {"$in": task_ids}}, {"_id": 0}).to_list(5000)}
    projects_map = {p["id"]: p for p in await db.projects.find({}, {"_id": 0}).to_list(500)}
    by_project = {}
    by_designation = {}
    for s in sessions:
        info = cost_map.get(s["user_id"])
        if not info:
            continue
        c = (s.get("duration_seconds", 0) / 3600.0) * info["hourly"]
        task = tasks_map.get(s["task_id"])
        if task and task.get("project_id"):
            pid = task["project_id"]
            by_project.setdefault(pid, 0)
            by_project[pid] += c
        desig = info["user"].get("designation", "Other")
        by_designation.setdefault(desig, 0)
        by_designation[desig] += c
    project_costs = [
        {"project_id": pid, "name": (projects_map.get(pid) or {}).get("name", "Unknown"),
         "company_name": (projects_map.get(pid) or {}).get("company_name", ""),
         "cost": round(v, 2)} for pid, v in by_project.items()
    ]
    project_costs.sort(key=lambda r: r["cost"], reverse=True)
    designation_costs = [{"designation": k, "cost": round(v, 2)} for k, v in by_designation.items()]
    designation_costs.sort(key=lambda r: r["cost"], reverse=True)
    return {
        "month": month_key,
        "projects": project_costs,
        "designations": designation_costs,
        "total": round(sum(v for v in by_project.values()), 2),
    }

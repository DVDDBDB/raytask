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
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
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


def _range_window(range_key: str, start: str = "", end: str = ""):
    """Compute (start_dt, end_dt, label) for a requested range."""
    now = datetime.now(timezone.utc)
    if range_key == "custom":
        s_dt = _iso_to_dt(start) if start else None
        e_dt = _iso_to_dt(end) if end else None
        if s_dt is None:
            s_dt = now - timedelta(days=30)
        if e_dt is None:
            e_dt = now
        # If end date passed as date-only, include the whole day
        if e_dt.time() == datetime.min.time() and end and len(end) <= 10:
            e_dt = e_dt.replace(hour=23, minute=59, second=59)
        label = f"{s_dt.date().isoformat()} → {e_dt.date().isoformat()}"
        return s_dt, e_dt, label
    if range_key == "today":
        s_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return s_dt, now, "Today"
    if range_key == "week":
        s_dt = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        return s_dt, now, "This week"
    if range_key == "quarter":
        q_start_month = ((now.month - 1) // 3) * 3 + 1
        s_dt = now.replace(month=q_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
        return s_dt, now, f"Q{((now.month - 1)//3)+1} {now.year}"
    if range_key == "year":
        s_dt = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return s_dt, now, f"Year {now.year}"
    # default = month
    s_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return s_dt, now, now.strftime("%B %Y")


def _session_cost_and_seconds(sess: dict, hourly: float, window_start: datetime, window_end: datetime):
    """
    Return (cost, seconds) contributed by a session that overlaps the window.
    For live (open) sessions, we count the running time up to `window_end` (bounded by now).
    """
    started = _iso_to_dt(sess.get("started_at"))
    if not started:
        return 0.0, 0
    ended = _iso_to_dt(sess.get("ended_at")) if sess.get("ended_at") else None
    if ended is None:
        ended = min(datetime.now(timezone.utc), window_end)
    # Clip to window
    seg_start = max(started, window_start)
    seg_end = min(ended, window_end)
    if seg_end <= seg_start:
        return 0.0, 0
    seconds = int((seg_end - seg_start).total_seconds())
    cost = (seconds / 3600.0) * hourly
    return cost, seconds


@router.get("/costs")
async def costs(
    range: str = Query("month", pattern="^(today|week|month|quarter|year|custom)$"),
    start: str = "",
    end: str = "",
    project_id: str = "",
    user_id: str = "",
    user=Depends(require_roles("super_admin", "admin")),
):
    """Cost analytics with date-range + project/employee filters."""
    win_start, win_end, label = _range_window(range, start, end)
    cost_map = await _employee_costs()

    # Pull sessions that could overlap the window.
    # Use ISO string range on started_at; also include still-running sessions.
    sess_query = {
        "$or": [
            {"started_at": {"$gte": win_start.isoformat(), "$lte": win_end.isoformat()}},
            {"ended_at": None},
            {"ended_at": {"$gte": win_start.isoformat()}},
        ]
    }
    if user_id:
        sess_query = {"$and": [sess_query, {"user_id": user_id}]}

    sessions = await db.timer_sessions.find(sess_query, {"_id": 0}).to_list(200000)

    # Build task/project maps (single trip)
    task_ids = list({s["task_id"] for s in sessions if s.get("task_id")})
    tasks_map = {t["id"]: t for t in await db.tasks.find(
        {"id": {"$in": task_ids}}, {"_id": 0}).to_list(20000)}
    projects_map = {p["id"]: p for p in await db.projects.find({}, {"_id": 0}).to_list(1000)}

    by_project = {}
    by_designation = {}
    by_employee = {}
    by_task = {}
    total_cost = 0.0
    total_seconds = 0

    for s in sessions:
        info = cost_map.get(s.get("user_id"))
        if not info:
            continue
        task = tasks_map.get(s.get("task_id"))
        if not task:
            continue
        # Optional project filter
        if project_id and task.get("project_id") != project_id:
            continue
        cost, secs = _session_cost_and_seconds(s, info["hourly"], win_start, win_end)
        if secs <= 0:
            continue
        total_cost += cost
        total_seconds += secs

        # By project
        pid = task.get("project_id")
        if pid:
            row = by_project.setdefault(pid, {"cost": 0.0, "seconds": 0})
            row["cost"] += cost
            row["seconds"] += secs

        # By designation
        desig = info["user"].get("designation", "Other")
        drow = by_designation.setdefault(desig, {"cost": 0.0, "seconds": 0})
        drow["cost"] += cost
        drow["seconds"] += secs

        # By employee
        uid = s["user_id"]
        erow = by_employee.setdefault(uid, {"cost": 0.0, "seconds": 0})
        erow["cost"] += cost
        erow["seconds"] += secs

        # By task
        tid = task["id"]
        trow = by_task.setdefault(tid, {
            "cost": 0.0, "seconds": 0,
            "title": task.get("title", ""),
            "status": task.get("status", ""),
            "project_id": pid,
        })
        trow["cost"] += cost
        trow["seconds"] += secs

    # Compute each employee's TOTAL MONTHLY work cost (current calendar month)
    month_start, month_end, _ = _range_window("month")
    month_sess = await db.timer_sessions.find({
        "$or": [
            {"started_at": {"$gte": month_start.isoformat()}},
            {"ended_at": None},
        ]
    }, {"_id": 0}).to_list(200000)
    monthly_by_user = {}
    for s in month_sess:
        info = cost_map.get(s.get("user_id"))
        if not info:
            continue
        cost, secs = _session_cost_and_seconds(s, info["hourly"], month_start, month_end)
        if secs <= 0:
            continue
        row = monthly_by_user.setdefault(s["user_id"], {"cost": 0.0, "seconds": 0})
        row["cost"] += cost
        row["seconds"] += secs

    project_costs = [
        {
            "project_id": pid,
            "name": (projects_map.get(pid) or {}).get("name", "Unknown"),
            "company_name": (projects_map.get(pid) or {}).get("company_name", ""),
            "cost": round(v["cost"], 2),
            "seconds": v["seconds"],
            "hours": round(v["seconds"] / 3600, 2),
        }
        for pid, v in by_project.items()
    ]
    project_costs.sort(key=lambda r: r["cost"], reverse=True)

    designation_costs = [
        {"designation": k, "cost": round(v["cost"], 2), "seconds": v["seconds"]}
        for k, v in by_designation.items()
    ]
    designation_costs.sort(key=lambda r: r["cost"], reverse=True)

    employee_costs = []
    for uid, v in by_employee.items():
        info = cost_map.get(uid)
        if not info:
            continue
        u = info["user"]
        month_row = monthly_by_user.get(uid, {"cost": 0.0, "seconds": 0})
        employee_costs.append({
            "user_id": uid,
            "first_name": u.get("first_name", ""),
            "last_name": u.get("last_name", ""),
            "designation": u.get("designation", ""),
            "avatar_url": u.get("avatar_url", ""),
            "hourly": round(info["hourly"], 2),
            "cost": round(v["cost"], 2),
            "seconds": v["seconds"],
            "hours": round(v["seconds"] / 3600, 2),
            "monthly_cost": round(month_row["cost"], 2),
            "monthly_hours": round(month_row["seconds"] / 3600, 2),
        })
    employee_costs.sort(key=lambda r: r["cost"], reverse=True)

    # Task rows: also enrich with project & assignee names
    task_rows = []
    users_all = {u["id"]: u for u in await db.users.find(
        {}, {"_id": 0, "password_hash": 0}).to_list(1000)}
    for tid, v in by_task.items():
        t = tasks_map.get(tid, {})
        p = projects_map.get(v.get("project_id"))
        a = users_all.get(t.get("assignee_id"))
        task_rows.append({
            "task_id": tid,
            "title": v["title"],
            "status": v["status"],
            "project_id": v.get("project_id"),
            "project_name": (p or {}).get("name", "No project"),
            "assignee_id": t.get("assignee_id"),
            "assignee_name": (a or {}).get("first_name", "Unassigned"),
            "cost": round(v["cost"], 2),
            "seconds": v["seconds"],
            "hours": round(v["seconds"] / 3600, 2),
        })
    task_rows.sort(key=lambda r: r["cost"], reverse=True)

    return {
        "range": range,
        "range_label": label,
        "start": win_start.isoformat(),
        "end": win_end.isoformat(),
        "filters": {"project_id": project_id or None, "user_id": user_id or None},
        "total": round(total_cost, 2),
        "total_seconds": total_seconds,
        "total_hours": round(total_seconds / 3600, 2),
        "projects": project_costs,
        "designations": designation_costs,
        "employees": employee_costs,
        "tasks": task_rows,
        # Backwards-compat: legacy consumers used data.month
        "month": datetime.now(timezone.utc).strftime("%Y-%m"),
    }

"""Excel export routes (openpyxl)."""
from fastapi import APIRouter, Depends, Response
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from io import BytesIO
from auth import require_roles, get_current_user
from db import db
from datetime import datetime, timezone

router = APIRouter(prefix="/exports", tags=["exports"])

HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="E63946", end_color="E63946", fill_type="solid")
CENTER = Alignment(horizontal="center", vertical="center")


def _apply_header(ws, headers):
    for i, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=i, value=h)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = CENTER
    ws.freeze_panes = "A2"


def _autosize(ws):
    for col in ws.columns:
        max_len = 8
        letter = col[0].column_letter
        for cell in col:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[letter].width = min(max_len + 2, 60)


def _wb_response(wb: Workbook, filename: str) -> Response:
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/tasks.xlsx")
async def export_tasks(user=Depends(require_roles("super_admin", "admin", "manager"))):
    tasks = await db.tasks.find({}, {"_id": 0}).sort("created_at", -1).to_list(5000)
    users = {u["id"]: u for u in await db.users.find({}, {"_id": 0}).to_list(500)}
    projects = {p["id"]: p for p in await db.projects.find({}, {"_id": 0}).to_list(500)}
    sess_by_task = {}
    for s in await db.timer_sessions.find({}, {"_id": 0}).to_list(50000):
        sess_by_task[s["task_id"]] = sess_by_task.get(s["task_id"], 0) + (s.get("duration_seconds", 0) or 0)
    wb = Workbook()
    ws = wb.active
    ws.title = "Tasks"
    headers = ["Task ID", "Title", "Project", "Company", "Assignee", "Designation",
               "Priority", "Status", "Scheduled", "Due", "Estimate (min)",
               "Time spent (h)", "Created"]
    _apply_header(ws, headers)
    for t in tasks:
        a = users.get(t.get("assignee_id"))
        p = projects.get(t.get("project_id"))
        secs = sess_by_task.get(t["id"], 0)
        ws.append([
            t["id"], t.get("title", ""), (p or {}).get("name", ""),
            (p or {}).get("company_name", ""),
            (a or {}).get("first_name", ""), (a or {}).get("designation", ""),
            t.get("priority", ""), t.get("status", ""),
            t.get("scheduled_start_date", ""), t.get("due_date", ""),
            t.get("estimated_duration_minutes", 0),
            round(secs / 3600, 2), t.get("created_at", ""),
        ])
    _autosize(ws)
    return _wb_response(wb, "raybotix-tasks.xlsx")


@router.get("/costs.xlsx")
async def export_costs(user=Depends(require_roles("super_admin", "admin"))):
    users = {u["id"]: u for u in await db.users.find({}, {"_id": 0}).to_list(500)}
    tasks = {t["id"]: t for t in await db.tasks.find({}, {"_id": 0}).to_list(5000)}
    projects = {p["id"]: p for p in await db.projects.find({}, {"_id": 0}).to_list(500)}
    sessions = await db.timer_sessions.find({}, {"_id": 0}).to_list(50000)

    wb = Workbook()
    # Sheet 1: Task cost breakdown
    ws = wb.active
    ws.title = "Task cost"
    _apply_header(ws, ["Task", "Project", "Employee", "Designation", "Hours",
                       "Hourly (₹)", "Contribution (₹)"])
    for s in sessions:
        u = users.get(s["user_id"])
        t = tasks.get(s["task_id"])
        if not u or not t:
            continue
        wh = u.get("working_hours_per_day", 8) or 8
        wd = u.get("working_days_per_month", 25) or 25
        salary = u.get("monthly_salary", 0) or 0
        mh = wh * wd
        hourly = (salary / mh) if mh else 0
        hours = (s.get("duration_seconds", 0) or 0) / 3600.0
        p = projects.get(t.get("project_id"))
        ws.append([
            t.get("title", ""), (p or {}).get("name", ""),
            u.get("first_name", ""), u.get("designation", ""),
            round(hours, 2), round(hourly, 2), round(hours * hourly, 2),
        ])
    _autosize(ws)

    # Sheet 2: Project totals
    ws2 = wb.create_sheet("Project cost")
    _apply_header(ws2, ["Project", "Company", "Total ₹", "This month ₹"])
    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")
    proj_totals = {}
    proj_month = {}
    for s in sessions:
        u = users.get(s["user_id"])
        t = tasks.get(s["task_id"])
        if not u or not t:
            continue
        wh = u.get("working_hours_per_day", 8) or 8
        wd = u.get("working_days_per_month", 25) or 25
        salary = u.get("monthly_salary", 0) or 0
        mh = wh * wd
        hourly = (salary / mh) if mh else 0
        cost = (s.get("duration_seconds", 0) / 3600.0) * hourly
        pid = t.get("project_id")
        if not pid:
            continue
        proj_totals[pid] = proj_totals.get(pid, 0) + cost
        started = s.get("started_at", "")
        if isinstance(started, str) and started.startswith(month_key):
            proj_month[pid] = proj_month.get(pid, 0) + cost
    for pid, total in proj_totals.items():
        p = projects.get(pid, {})
        ws2.append([p.get("name", ""), p.get("company_name", ""),
                    round(total, 2), round(proj_month.get(pid, 0), 2)])
    _autosize(ws2)
    return _wb_response(wb, "raybotix-costs.xlsx")


@router.get("/productivity.xlsx")
async def export_productivity(user=Depends(require_roles("super_admin", "admin", "manager"))):
    users = await db.users.find({"status": "active"}, {"_id": 0}).to_list(500)
    sessions = await db.timer_sessions.find({}, {"_id": 0}).to_list(50000)
    tasks_map = {}
    for t in await db.tasks.find({}, {"_id": 0, "id": 1, "assignee_id": 1, "status": 1}).to_list(5000):
        tasks_map[t["id"]] = t
    by_user = {}
    for s in sessions:
        by_user.setdefault(s["user_id"], 0)
        by_user[s["user_id"]] += s.get("duration_seconds", 0) or 0

    wb = Workbook()
    ws = wb.active
    ws.title = "Productivity"
    _apply_header(ws, ["Employee", "Designation", "Total hours", "Completed tasks",
                       "Reopened tasks", "Hourly ₹", "Total cost ₹", "Productivity %"])
    for u in users:
        secs = by_user.get(u["id"], 0)
        hours = secs / 3600.0
        wh = u.get("working_hours_per_day", 8) or 8
        wd = u.get("working_days_per_month", 25) or 25
        salary = u.get("monthly_salary", 0) or 0
        mh = wh * wd
        hourly = (salary / mh) if mh else 0
        completed = sum(1 for t in tasks_map.values() if t.get("assignee_id") == u["id"] and t.get("status") == "Completed")
        reopened = sum(1 for t in tasks_map.values() if t.get("assignee_id") == u["id"] and t.get("status") == "Reopened")
        productivity = round(min(100, (secs / (mh * 3600)) * 100), 1) if mh else 0
        ws.append([
            u["first_name"], u.get("designation", ""), round(hours, 2),
            completed, reopened, round(hourly, 2),
            round(hours * hourly, 2), productivity,
        ])
    _autosize(ws)
    return _wb_response(wb, "raybotix-productivity.xlsx")

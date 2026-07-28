"""Seed default super admin, employees, projects, and demo tasks."""
import uuid
from datetime import datetime, timezone, timedelta
from db import db
from auth import hash_password
from models import CompanySettings


def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat()


async def _ensure_super_admin(email: str, first_name: str, last_name: str, password: str = "Raybotix@2026"):
    """Idempotently ensure a Super Admin exists (created active, ready to sign in)."""
    existing = await db.users.find_one({"email": email.lower()})
    now = _iso(_now())
    if existing:
        await db.users.update_one(
            {"id": existing["id"]},
            {"$set": {
                "role": "super_admin", "status": "active",
                "first_name": first_name, "last_name": last_name,
                "updated_at": now,
            }},
        )
        return
    await db.users.insert_one({
        "id": uuid.uuid4().hex,
        "email": email.lower(),
        "first_name": first_name, "last_name": last_name,
        "designation": "Manager", "role": "super_admin",
        "status": "active", "avatar_url": "",
        "monthly_salary": 0.0,
        "working_hours_per_day": 8.0, "working_days_per_month": 25,
        "theme": "system", "permissions": [],
        "password_hash": hash_password(password),
        "last_login": None,
        "created_at": now, "updated_at": now,
    })


async def seed():
    # Company settings
    if not await db.settings.find_one({"id": "company"}):
        s = CompanySettings().model_dump()
        s["id"] = "company"
        await db.settings.insert_one(s)

    # Additional Super Admins — always ensured (idempotent, does not overwrite password)
    await _ensure_super_admin("ai.jaineel@gmail.com", "Jaineel", "Gandhi")
    await _ensure_super_admin("web.raybotix@gmail.com", "Jinal", "Dodiya")

    # Super admin
    existing_sa = await db.users.find_one({"email": "superadmin@raybotix.com"})
    if not existing_sa:
        users_data = [
            {
                "email": "superadmin@raybotix.com", "password": "Admin@123",
                "first_name": "Aditya", "last_name": "Sharma",
                "designation": "Manager", "role": "super_admin",
                "monthly_salary": 120000, "avatar_url":
                    "https://images.pexels.com/photos/37148308/pexels-photo-37148308.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
            },
            {
                "email": "priya@raybotix.com", "password": "Password@123",
                "first_name": "Priya", "last_name": "Iyer",
                "designation": "Content Writer", "role": "team_member",
                "monthly_salary": 45000,
                "avatar_url":
                    "https://images.unsplash.com/photo-1494790108377-be9c29b29330?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTF8MHwxfHNlYXJjaHwzfHxwcm9mZXNzaW9uYWwlMjBoZWFkc2hvdCUyMHBvcnRyYWl0fGVufDB8fHx8MTc4NTE1MTY3Nnww&ixlib=rb-4.1.0&q=85",
            },
            {
                "email": "rahul@raybotix.com", "password": "Password@123",
                "first_name": "Rahul", "last_name": "Verma",
                "designation": "Video Editor", "role": "team_member",
                "monthly_salary": 55000,
                "avatar_url":
                    "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTF8MHwxfHNlYXJjaHwxfHxwcm9mZXNzaW9uYWwlMjBoZWFkc2hvdCUyMHBvcnRyYWl0fGVufDB8fHx8MTc4NTE1MTY3Nnww&ixlib=rb-4.1.0&q=85",
            },
            {
                "email": "amit@raybotix.com", "password": "Password@123",
                "first_name": "Amit", "last_name": "Kumar",
                "designation": "Graphic Designer", "role": "team_member",
                "monthly_salary": 50000,
                "avatar_url": "",
            },
            {
                "email": "neha@raybotix.com", "password": "Password@123",
                "first_name": "Neha", "last_name": "Kapoor",
                "designation": "Social Media Manager", "role": "manager",
                "monthly_salary": 70000,
                "avatar_url":
                    "https://images.unsplash.com/photo-1699899657680-421c2c2d5064?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxOTF8MHwxfHNlYXJjaHw0fHxwcm9mZXNzaW9uYWwlMjBoZWFkc2hvdCUyMHBvcnRyYWl0fGVufDB8fHx8MTc4NTE1MTY3Nnww&ixlib=rb-4.1.0&q=85",
            },
            {
                "email": "karan@raybotix.com", "password": "Password@123",
                "first_name": "Karan", "last_name": "Mehta",
                "designation": "SEO Executive", "role": "team_member",
                "monthly_salary": 40000, "avatar_url": "",
            },
        ]
        user_ids = {}
        for u in users_data:
            uid = uuid.uuid4().hex
            doc = {
                "id": uid,
                "email": u["email"],
                "first_name": u["first_name"],
                "last_name": u["last_name"],
                "designation": u["designation"],
                "role": u["role"],
                "status": "active",
                "avatar_url": u.get("avatar_url", ""),
                "monthly_salary": u["monthly_salary"],
                "working_hours_per_day": 8.0,
                "working_days_per_month": 25,
                "theme": "system",
                "permissions": [],
                "password_hash": hash_password(u["password"]),
                "last_login": None,
                "created_at": _iso(_now()),
                "updated_at": _iso(_now()),
            }
            await db.users.insert_one(doc)
            user_ids[u["first_name"]] = uid

        # Projects
        projects = [
            {"name": "XYZ Bakery Launch", "company_name": "XYZ Bakery",
             "client_name": "Ravi Nair", "description": "Instagram + YouTube launch campaign"},
            {"name": "Aurora Wellness Rebrand", "company_name": "Aurora Wellness",
             "client_name": "Meera Joshi", "description": "New logo, tone of voice, and social kit"},
            {"name": "Internal — Growth Blog", "company_name": "Raybotix Digital",
             "client_name": "", "description": "Weekly SEO articles for the agency blog"},
        ]
        project_ids = {}
        for p in projects:
            pid = uuid.uuid4().hex
            await db.projects.insert_one({
                "id": pid, **p, "start_date": _iso(_now()), "end_date": None,
                "status": "active", "member_ids": list(user_ids.values()),
                "created_by": user_ids["Aditya"], "created_at": _iso(_now()), "updated_at": _iso(_now()),
            })
            project_ids[p["name"]] = pid

        # Tasks
        base_now = _now()
        tasks = [
            {"title": "Write Reel Script — Bakery Launch",
             "description": "45-sec reel script highlighting sourdough range.",
             "project_id": project_ids["XYZ Bakery Launch"],
             "assignee_id": user_ids["Priya"], "priority": "Urgent",
             "status": "Assigned",
             "due_date": _iso(base_now + timedelta(days=1)),
             "estimated_duration_minutes": 90},
            {"title": "Design Reel Cover — Bakery Launch",
             "description": "Brand-aligned cover in ember red.",
             "project_id": project_ids["XYZ Bakery Launch"],
             "assignee_id": user_ids["Amit"], "priority": "Medium",
             "status": "Assigned",
             "due_date": _iso(base_now + timedelta(days=2)),
             "estimated_duration_minutes": 120},
            {"title": "Edit Reel — Bakery Launch",
             "description": "Cut & assemble reel with music and captions.",
             "project_id": project_ids["XYZ Bakery Launch"],
             "assignee_id": user_ids["Rahul"], "priority": "Medium",
             "status": "Scheduled",
             "scheduled_start_date": _iso(base_now + timedelta(days=1)),
             "due_date": _iso(base_now + timedelta(days=3)),
             "estimated_duration_minutes": 180},
            {"title": "SEO audit — Aurora Wellness",
             "description": "Baseline audit + keyword shortlist.",
             "project_id": project_ids["Aurora Wellness Rebrand"],
             "assignee_id": user_ids["Karan"], "priority": "Low",
             "status": "Assigned",
             "due_date": _iso(base_now + timedelta(days=4)),
             "estimated_duration_minutes": 240},
            {"title": "Blog: 5 growth loops for D2C brands",
             "description": "1200-word article, SEO-optimised.",
             "project_id": project_ids["Internal — Growth Blog"],
             "assignee_id": user_ids["Priya"], "priority": "Medium",
             "status": "Assigned",
             "due_date": _iso(base_now + timedelta(days=5)),
             "estimated_duration_minutes": 180},
            {"title": "Schedule social posts — Wellness week",
             "description": "Batch schedule Instagram & LinkedIn posts.",
             "project_id": project_ids["Aurora Wellness Rebrand"],
             "assignee_id": user_ids["Neha"], "priority": "Medium",
             "status": "Waiting for Review",
             "due_date": _iso(base_now + timedelta(days=1)),
             "estimated_duration_minutes": 60},
        ]
        for t in tasks:
            tid = uuid.uuid4().hex
            assignee = await db.users.find_one({"id": t["assignee_id"]}, {"_id": 0})
            doc = {
                "id": tid,
                "creator_id": user_ids["Aditya"],
                "created_at": _iso(base_now), "updated_at": _iso(base_now),
                "completed_at": None,
                "tags": [], "instructions": "", "reference_links": [], "attachments": [],
                "parent_task_id": None,
                "review_status": None,
                "workflow": [{
                    "user_id": assignee["id"],
                    "first_name": assignee["first_name"],
                    "designation": assignee["designation"],
                    "avatar_url": assignee.get("avatar_url", ""),
                    "assigned_at": _iso(base_now),
                    "handoff_remarks": "",
                    "status": "assigned",
                }],
                "reassignment_history": [],
                **t,
            }
            await db.tasks.insert_one(doc)

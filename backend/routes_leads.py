"""CRM leads / inquiries routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from db import db
from auth import get_current_user, require_crm_access, has_crm_access
from models import (
    LeadCreate, LeadUpdate, LeadActivityCreate, LeadActivity,
    LeadOnboardRequest, LEAD_STAGES, LEAD_PRIORITIES,
)
from utils import now_iso, log_activity, push_notification
import uuid

router = APIRouter(prefix="/leads", tags=["leads"])


async def _resolve_assignee(assignee_id: Optional[str]):
    if not assignee_id:
        return None
    u = await db.users.find_one({"id": assignee_id}, {"_id": 0, "password_hash": 0})
    return u


def _serialize(lead: dict):
    # ensure activities is a list, hide _id
    lead.pop("_id", None)
    lead["activities"] = lead.get("activities", [])
    return lead


@router.get("")
async def list_leads(
    stage: str = "",
    assigned_to_id: str = "",
    q: str = "",
    include_onboarded: bool = False,
    user=Depends(require_crm_access),
):
    query = {}
    if stage:
        query["stage"] = stage
    if assigned_to_id:
        query["assigned_to_id"] = assigned_to_id
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"company": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
            {"phone": {"$regex": q, "$options": "i"}},
        ]
    # Hide Onboarded leads by default unless explicitly requested
    if not include_onboarded:
        query["stage"] = {"$ne": "Onboarded"} if "stage" not in query else query["stage"]
    docs = await db.leads.find(query, {"_id": 0}).sort("updated_at", -1).to_list(5000)
    return [_serialize(d) for d in docs]


@router.get("/stages")
async def get_stages(user=Depends(require_crm_access)):
    return LEAD_STAGES


@router.get("/team")
async def crm_team(user=Depends(require_crm_access)):
    """Users who can be assigned as owner of a lead (have CRM access or are admin)."""
    users = await db.users.find(
        {"$or": [{"crm_access": True}, {"role": {"$in": ["super_admin", "admin"]}}],
         "status": "active"},
        {"_id": 0, "password_hash": 0},
    ).to_list(500)
    return users


@router.post("")
async def create_lead(payload: LeadCreate, user=Depends(require_crm_access)):
    if payload.stage not in LEAD_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Allowed: {LEAD_STAGES}")
    assignee = await _resolve_assignee(payload.assigned_to_id) if payload.assigned_to_id else None
    if payload.assigned_to_id and not assignee:
        raise HTTPException(status_code=404, detail="Assigned user not found")
    if assignee and not has_crm_access(assignee):
        raise HTTPException(status_code=400, detail="Assigned user does not have CRM access")

    doc = {
        "id": uuid.uuid4().hex,
        **payload.model_dump(),
        "assigned_to_name": (assignee or {}).get("first_name", "") if assignee else "",
        "created_by_id": user["id"],
        "created_by_name": user.get("first_name", ""),
        "project_id": None,
        "activities": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.leads.insert_one(doc)
    await log_activity(user, "lead_created", "lead", doc["id"], new={"name": doc["name"]})
    if assignee and assignee["id"] != user["id"]:
        await push_notification(
            assignee["id"], "lead_assigned",
            "New lead assigned to you",
            f"{doc['name']} ({doc.get('company','')})",
            link_type="lead", link_id=doc["id"],
        )
    return _serialize(doc)


@router.get("/{lead_id}")
async def get_lead(lead_id: str, user=Depends(require_crm_access)):
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _serialize(lead)


@router.patch("/{lead_id}")
async def update_lead(lead_id: str, payload: LeadUpdate, user=Depends(require_crm_access)):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if "stage" in update and update["stage"] not in LEAD_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Allowed: {LEAD_STAGES}")
    if "priority" in update and update["priority"] not in LEAD_PRIORITIES:
        raise HTTPException(status_code=400, detail=f"Invalid priority. Allowed: {LEAD_PRIORITIES}")

    prev_stage = lead.get("stage")
    prev_assignee = lead.get("assigned_to_id")

    if "assigned_to_id" in update:
        assignee = await _resolve_assignee(update["assigned_to_id"])
        if update["assigned_to_id"] and not assignee:
            raise HTTPException(status_code=404, detail="Assigned user not found")
        if assignee and not has_crm_access(assignee):
            raise HTTPException(status_code=400, detail="Assigned user does not have CRM access")
        update["assigned_to_name"] = (assignee or {}).get("first_name", "") if assignee else ""

    update["updated_at"] = now_iso()

    # When a lead is marked Lost, clear all pending follow-ups + next_step.
    if update.get("stage") == "Lost":
        update["follow_up_date"] = None
        update["next_step"] = ""
        update["lost_at"] = now_iso()
        # Mark all activities done and drop their due_date so they leave any dashboards.
        activities = lead.get("activities", []) or []
        for a in activities:
            a["done"] = True
            if a.get("due_date"):
                a["due_date"] = None
        update["activities"] = activities

    await db.leads.update_one({"id": lead_id}, {"$set": update})

    # Log & notify
    if "stage" in update and update["stage"] != prev_stage:
        await log_activity(user, "lead_stage_changed", "lead", lead_id,
                           previous={"stage": prev_stage}, new={"stage": update["stage"]})
    if "assigned_to_id" in update and update["assigned_to_id"] and update["assigned_to_id"] != prev_assignee:
        await push_notification(
            update["assigned_to_id"], "lead_assigned",
            "A lead was assigned to you",
            f"{lead.get('name','')} ({lead.get('company','')})",
            link_type="lead", link_id=lead_id,
        )
    fresh = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return _serialize(fresh)


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, user=Depends(require_crm_access)):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    # Only creator, assignee, or admin/super_admin can delete
    if user["role"] not in ("super_admin", "admin") and \
       lead.get("created_by_id") != user["id"] and \
       lead.get("assigned_to_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Not allowed to delete this lead")
    await db.leads.delete_one({"id": lead_id})
    await log_activity(user, "lead_deleted", "lead", lead_id, previous={"name": lead.get("name")})
    return {"ok": True}


@router.post("/{lead_id}/activities")
async def add_activity(lead_id: str, payload: LeadActivityCreate,
                       user=Depends(require_crm_access)):
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    activity = LeadActivity(
        kind=payload.kind,
        description=payload.description,
        due_date=payload.due_date,
        done=payload.done,
        created_by_id=user["id"],
        created_by_name=user.get("first_name", ""),
    ).model_dump()
    await db.leads.update_one(
        {"id": lead_id},
        {"$push": {"activities": activity}, "$set": {"updated_at": now_iso()}},
    )
    await log_activity(user, "lead_activity_added", "lead", lead_id, new={"kind": payload.kind})
    return activity


@router.patch("/{lead_id}/activities/{activity_id}")
async def toggle_activity(lead_id: str, activity_id: str,
                          body: dict, user=Depends(require_crm_access)):
    """Small helper: mark activity done/undone or edit description."""
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    activities = lead.get("activities", [])
    found = None
    for a in activities:
        if a.get("id") == activity_id:
            found = a
            break
    if not found:
        raise HTTPException(status_code=404, detail="Activity not found")
    if "done" in body:
        found["done"] = bool(body["done"])
    if "description" in body:
        found["description"] = body["description"]
    if "due_date" in body:
        found["due_date"] = body["due_date"]
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {"activities": activities, "updated_at": now_iso()}},
    )
    return found


@router.post("/{lead_id}/onboard")
async def onboard_lead(lead_id: str, payload: LeadOnboardRequest,
                       user=Depends(require_crm_access)):
    """
    Mark a lead as Onboarded and auto-create a Project linked to it.
    If a project already exists for the lead, returns it (idempotent).
    """
    lead = await db.leads.find_one({"id": lead_id})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    if lead.get("project_id"):
        proj = await db.projects.find_one({"id": lead["project_id"]}, {"_id": 0})
        if proj:
            return {"ok": True, "already_onboarded": True, "project": proj, "lead": _serialize(lead)}

    proj_doc = {
        "id": uuid.uuid4().hex,
        "name": payload.project_name or f"{lead.get('company') or lead.get('name')}".strip(),
        "company_name": payload.company_name or lead.get("company", ""),
        "client_name": lead.get("name", ""),
        "description": payload.description or lead.get("notes", ""),
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        "status": "active",
        "member_ids": payload.member_ids or [user["id"]],
        "lead_id": lead_id,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    await db.projects.insert_one(proj_doc)

    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "stage": "Onboarded",
            "project_id": proj_doc["id"],
            "onboarded_at": now_iso(),
            "updated_at": now_iso(),
        }},
    )
    await log_activity(user, "lead_onboarded", "lead", lead_id,
                       new={"project_id": proj_doc["id"], "project_name": proj_doc["name"]})
    proj_doc.pop("_id", None)
    fresh = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    return {"ok": True, "project": proj_doc, "lead": _serialize(fresh)}


@router.get("/follow-ups/upcoming")
async def follow_ups(days: int = Query(7, ge=1, le=90), user=Depends(require_crm_access)):
    """Leads with follow_up_date within the next N days, assigned to me (or all if admin)."""
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)
    query = {
        "follow_up_date": {"$gte": now.isoformat(), "$lte": end.isoformat()},
        "stage": {"$nin": ["Onboarded", "Lost"]},
    }
    if user["role"] not in ("super_admin", "admin"):
        query["assigned_to_id"] = user["id"]
    docs = await db.leads.find(query, {"_id": 0}).sort("follow_up_date", 1).to_list(500)
    return [_serialize(d) for d in docs]

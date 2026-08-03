"""Quotations & Invoices routes."""
from fastapi import APIRouter, Depends, HTTPException
from db import db
from auth import require_crm_access
from models import (
    QuotationCreate, QuotationUpdate, InvoiceCreate, InvoiceUpdate,
    QUOTATION_STATUSES, INVOICE_STATUSES, LineItem,
)
from utils import now_iso, log_activity, push_notification
from datetime import datetime, timezone
import uuid

router = APIRouter(tags=["billing"])


# ---------- helpers ----------

def _round(v: float) -> float:
    return round(float(v or 0), 2)


def _totals(items):
    """Compute per-line and grand totals. Mutates items list in place."""
    subtotal = 0.0
    gst_amount = 0.0
    for it in items:
        qty = float(it.get("qty") or 0)
        rate = float(it.get("rate") or 0)
        gst_pct = float(it.get("gst_pct") or 0)
        line_total = qty * rate
        line_gst = line_total * gst_pct / 100.0
        it["line_total"] = _round(line_total)
        it["line_gst"] = _round(line_gst)
        subtotal += line_total
        gst_amount += line_gst
    total = subtotal + gst_amount
    return _round(subtotal), _round(gst_amount), _round(total)


async def _next_number(kind: str) -> str:
    """
    Atomic increment on a counters collection. kind = 'quotation'|'invoice'.
    Returns 'RB-Q-2026-0007' / 'RB-INV-2026-0007'.
    """
    year = datetime.now(timezone.utc).year
    key = f"{kind}_{year}"
    res = await db.counters.find_one_and_update(
        {"_id": key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    if res is None:
        # Some drivers require the ReturnDocument enum; fallback re-read.
        res = await db.counters.find_one({"_id": key})
    seq = (res or {}).get("seq", 1)
    prefix = "RB-Q" if kind == "quotation" else "RB-INV"
    return f"{prefix}-{year}-{seq:04d}"


def _client_from_lead(lead: dict) -> dict:
    return {
        "client_name": lead.get("name", ""),
        "client_company": lead.get("company", ""),
        "client_email": lead.get("email", ""),
        "client_phone": lead.get("phone", ""),
        "client_address": "",
    }


def _client_from_project(project: dict) -> dict:
    return {
        "client_name": project.get("client_name", ""),
        "client_company": project.get("company_name", ""),
        "client_email": project.get("client_email", ""),
        "client_phone": project.get("client_phone", ""),
        "client_address": project.get("client_address", ""),
    }


async def _resolve_client_defaults(payload: dict):
    """Fill client_* fields from lead/project if empty."""
    defaults = {}
    if payload.get("lead_id"):
        lead = await db.leads.find_one({"id": payload["lead_id"]}, {"_id": 0})
        if lead:
            defaults = _client_from_lead(lead)
    if payload.get("project_id"):
        proj = await db.projects.find_one({"id": payload["project_id"]}, {"_id": 0})
        if proj:
            # Project overrides lead where present
            pj = _client_from_project(proj)
            for k, v in pj.items():
                if v:
                    defaults[k] = v
    for k, v in defaults.items():
        if not payload.get(k):
            payload[k] = v


async def _notify_team_on_send(kind_label: str, doc: dict, actor: dict):
    """In-app notification to super_admins/admins + assigned lead owner about a sent quotation/invoice."""
    recipient_ids = set()
    admins = await db.users.find(
        {"role": {"$in": ["super_admin", "admin"]}, "status": "active"},
        {"_id": 0, "id": 1},
    ).to_list(200)
    for a in admins:
        recipient_ids.add(a["id"])
    # Also notify the lead's assignee if applicable
    if doc.get("lead_id"):
        lead = await db.leads.find_one({"id": doc["lead_id"]}, {"_id": 0})
        if lead and lead.get("assigned_to_id"):
            recipient_ids.add(lead["assigned_to_id"])
    if doc.get("project_id"):
        proj = await db.projects.find_one({"id": doc["project_id"]}, {"_id": 0})
        for m in (proj or {}).get("member_ids", []) or []:
            recipient_ids.add(m)
    recipient_ids.discard(actor.get("id"))
    for uid_ in recipient_ids:
        await push_notification(
            uid_, f"{kind_label}_sent",
            f"{kind_label.capitalize()} {doc.get('number','')} sent",
            f"For {doc.get('client_company') or doc.get('client_name') or 'client'} — ₹{doc.get('total', 0):,.2f}",
            link_type=kind_label, link_id=doc["id"],
        )


async def _user_can_view(doc: dict, user: dict) -> bool:
    """Admins see everything; sales users see only 'their' quotations/invoices."""
    if user.get("role") in ("super_admin", "admin"):
        return True
    if doc.get("created_by_id") == user["id"]:
        return True
    if doc.get("lead_id"):
        lead = await db.leads.find_one({"id": doc["lead_id"]}, {"_id": 0, "assigned_to_id": 1, "created_by_id": 1})
        if lead and (lead.get("assigned_to_id") == user["id"] or lead.get("created_by_id") == user["id"]):
            return True
    if doc.get("project_id"):
        proj = await db.projects.find_one({"id": doc["project_id"]}, {"_id": 0, "member_ids": 1})
        if proj and user["id"] in (proj.get("member_ids") or []):
            return True
    return False


async def _visibility_query(user: dict) -> dict:
    """Return a mongo query fragment that limits visibility for non-admin users."""
    if user.get("role") in ("super_admin", "admin"):
        return {}
    uid = user["id"]
    # Owned leads (assigned to or created by me)
    lead_ids = [d["id"] for d in await db.leads.find(
        {"$or": [{"assigned_to_id": uid}, {"created_by_id": uid}]},
        {"_id": 0, "id": 1},
    ).to_list(5000)]
    project_ids = [d["id"] for d in await db.projects.find(
        {"member_ids": uid}, {"_id": 0, "id": 1},
    ).to_list(5000)]
    ors = [{"created_by_id": uid}]
    if lead_ids:
        ors.append({"lead_id": {"$in": lead_ids}})
    if project_ids:
        ors.append({"project_id": {"$in": project_ids}})
    return {"$or": ors}


# ================================================================
# Quotations
# ================================================================

quotations = APIRouter(prefix="/quotations")


@quotations.get("")
async def list_quotations(
    status: str = "", lead_id: str = "", project_id: str = "",
    user=Depends(require_crm_access),
):
    q = {}
    if status:
        q["status"] = status
    if lead_id:
        q["lead_id"] = lead_id
    if project_id:
        q["project_id"] = project_id
    vis = await _visibility_query(user)
    if vis:
        q = {"$and": [q, vis]} if q else vis
    docs = await db.quotations.find(q, {"_id": 0}).sort("created_at", -1).to_list(2000)
    return docs


@quotations.get("/statuses")
async def quotation_statuses(user=Depends(require_crm_access)):
    return QUOTATION_STATUSES


@quotations.post("")
async def create_quotation(payload: QuotationCreate, user=Depends(require_crm_access)):
    data = payload.model_dump()
    await _resolve_client_defaults(data)
    subtotal, gst_amount, total = _totals(data["items"])
    doc = {
        "id": uuid.uuid4().hex,
        "number": await _next_number("quotation"),
        "status": "draft",
        "created_by_id": user["id"],
        "created_by_name": user.get("first_name", ""),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "sent_at": None,
        "accepted_at": None,
        "rejected_at": None,
        "subtotal": subtotal,
        "gst_amount": gst_amount,
        "total": total,
        **data,
    }
    await db.quotations.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user, "quotation_created", "quotation", doc["id"],
                       new={"number": doc["number"], "total": doc["total"]})
    return doc


@quotations.get("/{qid}")
async def get_quotation(qid: str, user=Depends(require_crm_access)):
    doc = await db.quotations.find_one({"id": qid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if not await _user_can_view(doc, user):
        raise HTTPException(status_code=403, detail="Not allowed to view this quotation")
    return doc


@quotations.patch("/{qid}")
async def update_quotation(qid: str, payload: QuotationUpdate, user=Depends(require_crm_access)):
    doc = await db.quotations.find_one({"id": qid})
    if not doc:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if not await _user_can_view(doc, user):
        raise HTTPException(status_code=403, detail="Not allowed to edit this quotation")
    update = payload.model_dump(exclude_none=True)
    if "status" in update and update["status"] not in QUOTATION_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {QUOTATION_STATUSES}")
    if "items" in update:
        subtotal, gst_amount, total = _totals(update["items"])
        update["subtotal"] = subtotal
        update["gst_amount"] = gst_amount
        update["total"] = total
    update["updated_at"] = now_iso()
    await db.quotations.update_one({"id": qid}, {"$set": update})
    fresh = await db.quotations.find_one({"id": qid}, {"_id": 0})
    return fresh


@quotations.post("/{qid}/send")
async def send_quotation(qid: str, user=Depends(require_crm_access)):
    doc = await db.quotations.find_one({"id": qid})
    if not doc:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if not doc.get("items"):
        raise HTTPException(status_code=400, detail="Cannot send an empty quotation")
    await db.quotations.update_one(
        {"id": qid},
        {"$set": {"status": "sent", "sent_at": now_iso(), "updated_at": now_iso()}},
    )
    fresh = await db.quotations.find_one({"id": qid}, {"_id": 0})
    await _notify_team_on_send("quotation", fresh, user)
    await log_activity(user, "quotation_sent", "quotation", qid,
                       new={"number": fresh["number"], "total": fresh["total"]})
    return {"ok": True, "quotation": fresh, "email_queued": False,
            "note": "In-app notification only. Resend email lands in Phase 4."}


@quotations.post("/{qid}/mark-status")
async def mark_status(qid: str, body: dict, user=Depends(require_crm_access)):
    status = body.get("status")
    if status not in QUOTATION_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {QUOTATION_STATUSES}")
    stamp_field = {
        "sent": "sent_at",
        "accepted": "accepted_at",
        "rejected": "rejected_at",
    }.get(status)
    update = {"status": status, "updated_at": now_iso()}
    if stamp_field:
        update[stamp_field] = now_iso()
    r = await db.quotations.update_one({"id": qid}, {"$set": update})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Quotation not found")
    fresh = await db.quotations.find_one({"id": qid}, {"_id": 0})
    await log_activity(user, "quotation_status_changed", "quotation", qid, new={"status": status})
    return fresh


@quotations.delete("/{qid}")
async def delete_quotation(qid: str, user=Depends(require_crm_access)):
    doc = await db.quotations.find_one({"id": qid})
    if not doc:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if user.get("role") not in ("super_admin", "admin") and doc.get("created_by_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only the creator or admins can delete")
    await db.quotations.delete_one({"id": qid})
    await log_activity(user, "quotation_deleted", "quotation", qid, previous={"number": doc.get("number")})
    return {"ok": True}


# ================================================================
# Invoices
# ================================================================

invoices = APIRouter(prefix="/invoices")


@invoices.get("")
async def list_invoices(
    status: str = "", lead_id: str = "", project_id: str = "",
    user=Depends(require_crm_access),
):
    q = {}
    if status:
        q["status"] = status
    if lead_id:
        q["lead_id"] = lead_id
    if project_id:
        q["project_id"] = project_id
    vis = await _visibility_query(user)
    if vis:
        q = {"$and": [q, vis]} if q else vis
    docs = await db.invoices.find(q, {"_id": 0}).sort("created_at", -1).to_list(2000)
    # Mark overdue on-the-fly if due_date has passed and status still 'sent'
    now = datetime.now(timezone.utc).isoformat()
    for d in docs:
        if d.get("status") == "sent" and d.get("due_date") and d["due_date"] < now:
            d["_overdue"] = True
    return docs


@invoices.get("/statuses")
async def invoice_statuses(user=Depends(require_crm_access)):
    return INVOICE_STATUSES


@invoices.get("/{iid}")
async def get_invoice(iid: str, user=Depends(require_crm_access)):
    doc = await db.invoices.find_one({"id": iid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not await _user_can_view(doc, user):
        raise HTTPException(status_code=403, detail="Not allowed to view this invoice")
    return doc


@invoices.post("")
async def create_invoice(payload: InvoiceCreate, user=Depends(require_crm_access)):
    data = payload.model_dump()
    await _resolve_client_defaults(data)
    subtotal, gst_amount, total = _totals(data["items"])
    doc = {
        "id": uuid.uuid4().hex,
        "number": await _next_number("invoice"),
        "status": "draft",
        "created_by_id": user["id"],
        "created_by_name": user.get("first_name", ""),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "sent_at": None,
        "paid_at": None,
        "subtotal": subtotal,
        "gst_amount": gst_amount,
        "total": total,
        **data,
    }
    await db.invoices.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user, "invoice_created", "invoice", doc["id"],
                       new={"number": doc["number"], "total": doc["total"]})
    return doc


@invoices.post("/from-quotation/{qid}")
async def invoice_from_quotation(qid: str, user=Depends(require_crm_access)):
    q = await db.quotations.find_one({"id": qid}, {"_id": 0})
    if not q:
        raise HTTPException(status_code=404, detail="Quotation not found")
    # Fresh items copy (new ids)
    items = []
    for it in q.get("items", []):
        items.append({
            "id": uuid.uuid4().hex,
            "description": it.get("description", ""),
            "qty": it.get("qty", 1),
            "rate": it.get("rate", 0),
            "gst_pct": it.get("gst_pct", 18),
            "line_total": it.get("line_total", 0),
            "line_gst": it.get("line_gst", 0),
        })
    payload_dict = {
        "lead_id": q.get("lead_id"),
        "project_id": q.get("project_id"),
        "quotation_id": qid,
        "client_name": q.get("client_name", ""),
        "client_company": q.get("client_company", ""),
        "client_email": q.get("client_email", ""),
        "client_phone": q.get("client_phone", ""),
        "client_address": q.get("client_address", ""),
        "items": items,
        "notes": q.get("notes", ""),
        "terms": q.get("terms", ""),
        "currency": q.get("currency", "INR"),
    }
    subtotal, gst_amount, total = _totals(items)
    doc = {
        "id": uuid.uuid4().hex,
        "number": await _next_number("invoice"),
        "status": "draft",
        "created_by_id": user["id"],
        "created_by_name": user.get("first_name", ""),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "sent_at": None,
        "paid_at": None,
        "subtotal": subtotal,
        "gst_amount": gst_amount,
        "total": total,
        "due_date": None,
        **payload_dict,
    }
    await db.invoices.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user, "invoice_from_quotation", "invoice", doc["id"],
                       new={"number": doc["number"], "quotation_id": qid})
    return doc


@invoices.patch("/{iid}")
async def update_invoice(iid: str, payload: InvoiceUpdate, user=Depends(require_crm_access)):
    doc = await db.invoices.find_one({"id": iid})
    if not doc:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not await _user_can_view(doc, user):
        raise HTTPException(status_code=403, detail="Not allowed to edit this invoice")
    update = payload.model_dump(exclude_none=True)
    if "status" in update and update["status"] not in INVOICE_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {INVOICE_STATUSES}")
    if "items" in update:
        subtotal, gst_amount, total = _totals(update["items"])
        update["subtotal"] = subtotal
        update["gst_amount"] = gst_amount
        update["total"] = total
    update["updated_at"] = now_iso()
    await db.invoices.update_one({"id": iid}, {"$set": update})
    fresh = await db.invoices.find_one({"id": iid}, {"_id": 0})
    return fresh


@invoices.post("/{iid}/send")
async def send_invoice(iid: str, user=Depends(require_crm_access)):
    doc = await db.invoices.find_one({"id": iid})
    if not doc:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not doc.get("items"):
        raise HTTPException(status_code=400, detail="Cannot send an empty invoice")
    await db.invoices.update_one(
        {"id": iid},
        {"$set": {"status": "sent", "sent_at": now_iso(), "updated_at": now_iso()}},
    )
    fresh = await db.invoices.find_one({"id": iid}, {"_id": 0})
    await _notify_team_on_send("invoice", fresh, user)
    await log_activity(user, "invoice_sent", "invoice", iid,
                       new={"number": fresh["number"], "total": fresh["total"]})
    return {"ok": True, "invoice": fresh, "email_queued": False,
            "note": "In-app notification only. Resend email lands in Phase 4."}


@invoices.post("/{iid}/mark-paid")
async def mark_paid(iid: str, user=Depends(require_crm_access)):
    doc = await db.invoices.find_one({"id": iid})
    if not doc:
        raise HTTPException(status_code=404, detail="Invoice not found")
    await db.invoices.update_one(
        {"id": iid},
        {"$set": {"status": "paid", "paid_at": now_iso(), "updated_at": now_iso()}},
    )
    fresh = await db.invoices.find_one({"id": iid}, {"_id": 0})
    await log_activity(user, "invoice_paid", "invoice", iid,
                       new={"number": fresh["number"], "total": fresh["total"]})
    return fresh


@invoices.post("/{iid}/mark-status")
async def mark_invoice_status(iid: str, body: dict, user=Depends(require_crm_access)):
    status = body.get("status")
    if status not in INVOICE_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {INVOICE_STATUSES}")
    update = {"status": status, "updated_at": now_iso()}
    if status == "sent":
        update["sent_at"] = now_iso()
    if status == "paid":
        update["paid_at"] = now_iso()
    r = await db.invoices.update_one({"id": iid}, {"$set": update})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Invoice not found")
    fresh = await db.invoices.find_one({"id": iid}, {"_id": 0})
    await log_activity(user, "invoice_status_changed", "invoice", iid, new={"status": status})
    return fresh


@invoices.delete("/{iid}")
async def delete_invoice(iid: str, user=Depends(require_crm_access)):
    doc = await db.invoices.find_one({"id": iid})
    if not doc:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if user.get("role") not in ("super_admin", "admin") and doc.get("created_by_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only the creator or admins can delete")
    await db.invoices.delete_one({"id": iid})
    await log_activity(user, "invoice_deleted", "invoice", iid, previous={"number": doc.get("number")})
    return {"ok": True}


router.include_router(quotations)
router.include_router(invoices)

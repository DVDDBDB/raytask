"""Company settings + PDF export + Recurring Invoices + Lead Analytics."""
from fastapi import APIRouter, Depends, HTTPException, Response
from db import db
from auth import get_current_user, require_roles, require_crm_access, has_crm_access
from models import (
    CompanySettings, RecurringInvoiceCreate, RecurringInvoiceUpdate, INVOICE_STATUSES,
)
from utils import now_iso, log_activity, push_notification
from datetime import datetime, timezone, timedelta
from io import BytesIO
import uuid
import calendar
import asyncio
import logging

logger = logging.getLogger("raybotix.billing")

router = APIRouter(tags=["billing-extras"])


SETTINGS_KEY = "company"


# =========================================================
# Company Settings
# =========================================================

settings_router = APIRouter(prefix="/settings")


async def _get_company_settings() -> dict:
    doc = await db.company_settings.find_one({"_id": SETTINGS_KEY})
    if not doc:
        # seed a default doc
        default = CompanySettings().model_dump()
        default["_id"] = SETTINGS_KEY
        await db.company_settings.insert_one(default)
        doc = default
    doc.pop("_id", None)
    return doc


@settings_router.get("/company")
async def get_company_settings(user=Depends(get_current_user)):
    """Any authenticated user can read (needed to render PDFs / invoices)."""
    return await _get_company_settings()


@settings_router.put("/company")
async def update_company_settings(
    payload: CompanySettings,
    user=Depends(require_roles("super_admin", "admin")),
):
    data = payload.model_dump()
    await db.company_settings.update_one(
        {"_id": SETTINGS_KEY},
        {"$set": data},
        upsert=True,
    )
    await log_activity(user, "company_settings_updated", "settings", SETTINGS_KEY, new=data)
    return {**data, "_id": None}


# =========================================================
# PDF export
# =========================================================

pdf_router = APIRouter()


def _fmt_inr(n: float) -> str:
    try:
        n = float(n or 0)
    except Exception:
        return "0.00"
    # Indian grouping (12,34,567.89)
    neg = n < 0
    n_abs = abs(n)
    ip, fp = f"{n_abs:.2f}".split(".")
    if len(ip) <= 3:
        grouped = ip
    else:
        head, tail = ip[:-3], ip[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        grouped = ",".join(groups) + "," + tail
    return ("-" if neg else "") + grouped + "." + fp


def _amount_to_words(amount: float) -> str:
    # Simple INR words converter (up to 99 crore).
    try:
        rupees = int(amount)
    except Exception:
        return ""
    if rupees == 0:
        return "Zero Rupees Only"
    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
             "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
             "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def two(n):
        if n < 20:
            return units[n]
        return tens[n // 10] + ("" if n % 10 == 0 else " " + units[n % 10])

    def three(n):
        h = n // 100
        r = n % 100
        s = ""
        if h:
            s += units[h] + " Hundred"
            if r:
                s += " and "
        if r:
            s += two(r)
        return s.strip()

    parts = []
    crore = rupees // 10000000
    if crore:
        parts.append(three(crore) + " Crore")
        rupees %= 10000000
    lakh = rupees // 100000
    if lakh:
        parts.append(three(lakh) + " Lakh")
        rupees %= 100000
    thou = rupees // 1000
    if thou:
        parts.append(three(thou) + " Thousand")
        rupees %= 1000
    rest = three(rupees)
    if rest:
        parts.append(rest)
    return " ".join(parts).strip() + " Rupees Only"


def _render_billing_pdf(doc: dict, settings: dict, kind: str) -> bytes:
    """Render a quotation or invoice PDF. kind = 'invoice' | 'quotation'."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak,
    )
    from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

    buf = BytesIO()
    pdf = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"{kind.capitalize()} {doc.get('number','')}",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="H2b", parent=styles["Heading2"],
                              textColor=colors.HexColor("#DC2626"), spaceAfter=2))
    styles.add(ParagraphStyle(name="Right", parent=styles["Normal"], alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name="Small2", parent=styles["Normal"], fontSize=9, leading=12))
    story = []

    # Header
    company_lines = [
        f"<b>{settings.get('company_name', 'Raybotix Digital')}</b>",
    ]
    if settings.get("tagline"):
        company_lines.append(settings["tagline"])
    addr_parts = [settings.get("address", ""), settings.get("city", ""), settings.get("state", ""), settings.get("pincode", "")]
    addr_line = ", ".join([a for a in addr_parts if a])
    if addr_line:
        company_lines.append(addr_line)
    contact_bits = []
    if settings.get("phone"): contact_bits.append("☎ " + settings["phone"])
    if settings.get("email"): contact_bits.append("✉ " + settings["email"])
    if settings.get("website"): contact_bits.append(settings["website"])
    if contact_bits:
        company_lines.append(" · ".join(contact_bits))
    if settings.get("gst_number"):
        company_lines.append(f"GSTIN: <b>{settings['gst_number']}</b>")
    if settings.get("pan_number"):
        company_lines.append(f"PAN: {settings['pan_number']}")

    left = Paragraph("<br/>".join(company_lines), styles["Small2"])

    # Title + number
    title = "TAX INVOICE" if kind == "invoice" else "QUOTATION"
    right = Paragraph(
        f"<para align='right'><font size=18 color='#DC2626'><b>{title}</b></font><br/>"
        f"<b>{doc.get('number','')}</b><br/>"
        f"Date: {(doc.get('created_at') or '')[:10]}<br/>"
        f"{'Due:' if kind == 'invoice' else 'Valid till:'} "
        f"{((doc.get('due_date') if kind == 'invoice' else doc.get('valid_till')) or '—')[:10]}"
        f"</para>",
        styles["Normal"],
    )
    header_tbl = Table([[left, right]], colWidths=[110 * mm, 70 * mm])
    header_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(header_tbl)
    story.append(Spacer(1, 6 * mm))

    # Bill To
    bill_to = [
        f"<b>{doc.get('client_company') or doc.get('client_name','')}</b>",
    ]
    if doc.get("client_company") and doc.get("client_name"):
        bill_to.append(doc["client_name"])
    if doc.get("client_address"): bill_to.append(doc["client_address"])
    if doc.get("client_phone"): bill_to.append("☎ " + doc["client_phone"])
    if doc.get("client_email"): bill_to.append("✉ " + doc["client_email"])

    bill_tbl = Table(
        [[Paragraph("<b>Bill To</b>", styles["Small"]),
          Paragraph(f"<b>Status</b>: {doc.get('status','draft').upper()}", styles["Small"])],
         [Paragraph("<br/>".join(bill_to), styles["Small2"]), ""]],
        colWidths=[130 * mm, 50 * mm],
    )
    bill_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(bill_tbl)
    story.append(Spacer(1, 6 * mm))

    # Items
    data = [["#", "Description", "Qty", "Rate ₹", "GST %", "Line ₹"]]
    for i, it in enumerate(doc.get("items", []) or [], start=1):
        qty = float(it.get("qty", 0) or 0)
        rate = float(it.get("rate", 0) or 0)
        gst_pct = float(it.get("gst_pct", 0) or 0)
        line = qty * rate
        data.append([
            str(i),
            Paragraph(it.get("description", "") or "", styles["Small2"]),
            f"{qty:g}",
            _fmt_inr(rate),
            f"{gst_pct:g}%",
            _fmt_inr(line),
        ])

    items_tbl = Table(data, colWidths=[10 * mm, 82 * mm, 15 * mm, 25 * mm, 15 * mm, 33 * mm], repeatRows=1)
    items_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DC2626")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(items_tbl)
    story.append(Spacer(1, 3 * mm))

    # Totals block (right aligned)
    totals = [
        ["Subtotal", "₹ " + _fmt_inr(doc.get("subtotal", 0))],
        ["GST", "₹ " + _fmt_inr(doc.get("gst_amount", 0))],
        ["Grand Total", "₹ " + _fmt_inr(doc.get("total", 0))],
    ]
    tot_tbl = Table(totals, colWidths=[45 * mm, 40 * mm], hAlign="RIGHT")
    tot_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("TEXTCOLOR", (0, 2), (-1, 2), colors.HexColor("#DC2626")),
        ("LINEABOVE", (0, 2), (-1, 2), 1, colors.HexColor("#DC2626")),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tot_tbl)
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        f"<i>Amount in words: {_amount_to_words(doc.get('total', 0))}</i>",
        styles["Small2"],
    ))
    story.append(Spacer(1, 6 * mm))

    # Notes + Terms + Bank
    if doc.get("notes"):
        story.append(Paragraph("<b>Notes</b>", styles["Small"]))
        story.append(Paragraph(doc["notes"].replace("\n", "<br/>"), styles["Small2"]))
        story.append(Spacer(1, 3 * mm))
    if doc.get("terms"):
        story.append(Paragraph("<b>Terms</b>", styles["Small"]))
        story.append(Paragraph(doc["terms"].replace("\n", "<br/>"), styles["Small2"]))
        story.append(Spacer(1, 3 * mm))

    # Bank details (invoices only)
    if kind == "invoice" and (settings.get("bank_name") or settings.get("bank_account_number")):
        bank_lines = ["<b>Bank Details</b>"]
        if settings.get("bank_account_name"): bank_lines.append(f"A/c Name: {settings['bank_account_name']}")
        if settings.get("bank_account_number"): bank_lines.append(f"A/c No.: {settings['bank_account_number']}")
        if settings.get("bank_ifsc"): bank_lines.append(f"IFSC: {settings['bank_ifsc']}")
        if settings.get("bank_name"): bank_lines.append(f"Bank: {settings['bank_name']}")
        if settings.get("bank_branch"): bank_lines.append(f"Branch: {settings['bank_branch']}")
        if settings.get("bank_upi"): bank_lines.append(f"UPI: {settings['bank_upi']}")
        story.append(Paragraph("<br/>".join(bank_lines), styles["Small2"]))
        story.append(Spacer(1, 3 * mm))

    footer_text = settings.get("invoice_footer" if kind == "invoice" else "quotation_footer") \
        or "Thank you for your business."
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        f"<para align='center'><font color='#6B7280'>{footer_text}</font></para>",
        styles["Small2"],
    ))

    pdf.build(story)
    return buf.getvalue()


async def _pdf_response(collection_name: str, doc_id: str, kind: str, user: dict):
    coll = getattr(db, collection_name)
    doc = await coll.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail=f"{kind.capitalize()} not found")
    # Import here to avoid circular
    from routes_billing import _user_can_view
    if not await _user_can_view(doc, user):
        raise HTTPException(status_code=403, detail=f"Not allowed to view this {kind}")
    settings = await _get_company_settings()
    pdf_bytes = _render_billing_pdf(doc, settings, kind)
    filename = f"{doc.get('number', kind)}.pdf".replace(" ", "-")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@pdf_router.get("/quotations/{qid}/pdf")
async def quotation_pdf(qid: str, user=Depends(require_crm_access)):
    return await _pdf_response("quotations", qid, "quotation", user)


@pdf_router.get("/invoices/{iid}/pdf")
async def invoice_pdf(iid: str, user=Depends(require_crm_access)):
    return await _pdf_response("invoices", iid, "invoice", user)


# =========================================================
# Recurring Invoices
# =========================================================

recurring_router = APIRouter(prefix="/recurring-invoices")


def _next_run(day_of_month: int, from_date: datetime | None = None) -> datetime:
    now = from_date or datetime.now(timezone.utc)
    day_of_month = max(1, min(28, int(day_of_month or 1)))
    # Start from today; if the day has already passed this month, roll to next month.
    year, month = now.year, now.month
    candidate = now.replace(year=year, month=month, day=day_of_month,
                            hour=6, minute=0, second=0, microsecond=0)
    if candidate <= now:
        # Next month
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
        candidate = candidate.replace(year=year, month=month)
    return candidate


@recurring_router.get("")
async def list_recurring(user=Depends(require_crm_access)):
    from routes_billing import _visibility_query
    q = await _visibility_query(user)
    docs = await db.recurring_invoices.find(q or {}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return docs


@recurring_router.post("")
async def create_recurring(payload: RecurringInvoiceCreate, user=Depends(require_crm_access)):
    data = payload.model_dump()
    doc = {
        "id": uuid.uuid4().hex,
        "created_by_id": user["id"],
        "created_by_name": user.get("first_name", ""),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "last_run_at": None,
        **data,
    }
    if not doc.get("next_run_date"):
        doc["next_run_date"] = _next_run(doc.get("day_of_month", 1)).isoformat()
    await db.recurring_invoices.insert_one(doc)
    doc.pop("_id", None)
    await log_activity(user, "recurring_invoice_created", "recurring_invoice", doc["id"],
                       new={"client": doc.get("client_company") or doc.get("client_name"),
                            "day_of_month": doc.get("day_of_month")})
    return doc


@recurring_router.get("/{rid}")
async def get_recurring(rid: str, user=Depends(require_crm_access)):
    from routes_billing import _user_can_view
    doc = await db.recurring_invoices.find_one({"id": rid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if not await _user_can_view(doc, user):
        raise HTTPException(status_code=403, detail="Not allowed")
    return doc


@recurring_router.patch("/{rid}")
async def update_recurring(rid: str, payload: RecurringInvoiceUpdate, user=Depends(require_crm_access)):
    from routes_billing import _user_can_view
    doc = await db.recurring_invoices.find_one({"id": rid})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if not await _user_can_view(doc, user):
        raise HTTPException(status_code=403, detail="Not allowed to edit")
    update = payload.model_dump(exclude_none=True)
    if "day_of_month" in update:
        update["next_run_date"] = _next_run(update["day_of_month"]).isoformat()
    update["updated_at"] = now_iso()
    await db.recurring_invoices.update_one({"id": rid}, {"$set": update})
    fresh = await db.recurring_invoices.find_one({"id": rid}, {"_id": 0})
    return fresh


@recurring_router.delete("/{rid}")
async def delete_recurring(rid: str, user=Depends(require_crm_access)):
    doc = await db.recurring_invoices.find_one({"id": rid})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if user.get("role") not in ("super_admin", "admin") and doc.get("created_by_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Only creator or admins can delete")
    await db.recurring_invoices.delete_one({"id": rid})
    return {"ok": True}


@recurring_router.post("/{rid}/run-now")
async def run_now(rid: str, user=Depends(require_crm_access)):
    """Manually generate the next invoice for this template. Also advances next_run_date."""
    doc = await db.recurring_invoices.find_one({"id": rid}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    from routes_billing import _user_can_view
    if not await _user_can_view(doc, user):
        raise HTTPException(status_code=403, detail="Not allowed")
    invoice = await _spawn_invoice_from_recurring(doc, actor_id=user["id"])
    return {"ok": True, "invoice": invoice}


# ---------------- scheduler helpers ----------------

async def _spawn_invoice_from_recurring(template: dict, actor_id: str) -> dict:
    """Create a Draft Invoice from a recurring template, notify team, advance next_run_date."""
    from routes_billing import _next_number, _totals
    items = []
    for it in template.get("items", []) or []:
        items.append({
            "id": uuid.uuid4().hex,
            "description": it.get("description", ""),
            "qty": it.get("qty", 1),
            "rate": it.get("rate", 0),
            "gst_pct": it.get("gst_pct", 18),
            "line_total": 0,
            "line_gst": 0,
        })
    subtotal, gst_amount, total = _totals(items)
    number = await _next_number("invoice")
    doc = {
        "id": uuid.uuid4().hex,
        "number": number,
        "status": "draft",
        "created_by_id": actor_id,
        "created_by_name": "Auto (Recurring)",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "sent_at": None,
        "paid_at": None,
        "subtotal": subtotal,
        "gst_amount": gst_amount,
        "total": total,
        "lead_id": template.get("lead_id"),
        "project_id": template.get("project_id"),
        "quotation_id": None,
        "recurring_invoice_id": template["id"],
        "client_name": template.get("client_name", ""),
        "client_company": template.get("client_company", ""),
        "client_email": template.get("client_email", ""),
        "client_phone": template.get("client_phone", ""),
        "client_address": template.get("client_address", ""),
        "items": items,
        "notes": template.get("notes", ""),
        "terms": template.get("terms", ""),
        "currency": template.get("currency", "INR"),
        "due_date": None,
    }
    await db.invoices.insert_one(doc)
    doc.pop("_id", None)
    # Advance the template
    next_run = _next_run(template.get("day_of_month", 1),
                         from_date=datetime.now(timezone.utc)).isoformat()
    await db.recurring_invoices.update_one(
        {"id": template["id"]},
        {"$set": {"last_run_at": now_iso(), "next_run_date": next_run}},
    )
    # Notify admins + project members + template creator
    recipient_ids = set()
    admins = await db.users.find(
        {"role": {"$in": ["super_admin", "admin"]}, "status": "active"},
        {"_id": 0, "id": 1},
    ).to_list(200)
    for a in admins:
        recipient_ids.add(a["id"])
    if template.get("created_by_id"):
        recipient_ids.add(template["created_by_id"])
    if template.get("project_id"):
        proj = await db.projects.find_one({"id": template["project_id"]}, {"_id": 0, "member_ids": 1})
        for m in (proj or {}).get("member_ids") or []:
            recipient_ids.add(m)
    for uid_ in recipient_ids:
        await push_notification(
            uid_, "recurring_invoice_generated",
            f"Draft invoice {number} auto-created",
            f"For {doc.get('client_company') or doc.get('client_name') or 'client'} — ₹{total:,.2f}",
            link_type="invoice", link_id=doc["id"],
        )
    logger.info("Recurring invoice %s generated from template %s", number, template["id"])
    return doc


_scheduler_task = None


async def _tick():
    now_iso_str = datetime.now(timezone.utc).isoformat()
    due = await db.recurring_invoices.find(
        {"active": True, "next_run_date": {"$lte": now_iso_str}},
        {"_id": 0},
    ).to_list(500)
    for t in due:
        try:
            actor = t.get("created_by_id") or (await db.users.find_one(
                {"role": "super_admin"}, {"_id": 0, "id": 1}) or {}).get("id", "system")
            await _spawn_invoice_from_recurring(t, actor)
        except Exception as e:
            logger.exception("Recurring tick failed for %s: %s", t.get("id"), e)


async def _loop(interval_seconds: int = 60):
    while True:
        try:
            await _tick()
        except Exception as e:
            logger.exception("Recurring loop error: %s", e)
        await asyncio.sleep(interval_seconds)


def start_recurring_scheduler(loop_object):
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        return
    _scheduler_task = loop_object.create_task(_loop())


# =========================================================
# Lead Analytics
# =========================================================

lead_analytics_router = APIRouter()


@lead_analytics_router.get("/analytics/leads")
async def lead_analytics(user=Depends(require_crm_access)):
    """Per-owner leads contacted/converted + total sales generated + pipeline value.

    - Admins see all owners.
    - Sales users see only their own row.
    """
    query = {}
    if user.get("role") not in ("super_admin", "admin"):
        query = {"$or": [{"assigned_to_id": user["id"]}, {"created_by_id": user["id"]}]}
    leads = await db.leads.find(query, {"_id": 0}).to_list(20000)

    users_map = {u["id"]: u for u in await db.users.find(
        {}, {"_id": 0, "password_hash": 0}).to_list(1000)}

    # Aggregate per owner
    per_owner = {}
    for l in leads:
        owner_id = l.get("assigned_to_id") or l.get("created_by_id") or "unassigned"
        row = per_owner.setdefault(owner_id, {
            "owner_id": owner_id,
            "owner_name": (users_map.get(owner_id) or {}).get("first_name", "Unassigned"),
            "designation": (users_map.get(owner_id) or {}).get("designation", ""),
            "contacted": 0,
            "converted": 0,
            "lost": 0,
            "in_pipeline": 0,
            "pipeline_value": 0.0,
            "onboarded_value": 0.0,
            "hot": 0, "cold": 0, "warm": 0,
        })
        # Anything past "New" counts as contacted.
        if l.get("stage") in ("Contacted", "Qualified", "Proposal", "Negotiation", "Onboarded"):
            row["contacted"] += 1
        if l.get("stage") == "Onboarded":
            row["converted"] += 1
            row["onboarded_value"] += float(l.get("value_estimate") or 0)
        elif l.get("stage") == "Lost":
            row["lost"] += 1
        else:
            row["in_pipeline"] += 1
            row["pipeline_value"] += float(l.get("value_estimate") or 0)
        temp = l.get("temperature") or "warm"
        row[temp] = row.get(temp, 0) + 1

    # Sales from paid invoices (link to lead's owner via lead_id → assigned_to_id)
    paid = await db.invoices.find(
        {"status": "paid"}, {"_id": 0, "total": 1, "lead_id": 1, "project_id": 1, "created_by_id": 1},
    ).to_list(20000)
    for inv in paid:
        owner_id = None
        if inv.get("lead_id"):
            l = next((x for x in leads if x["id"] == inv["lead_id"]), None)
            if l:
                owner_id = l.get("assigned_to_id") or l.get("created_by_id")
        if not owner_id and inv.get("project_id"):
            proj = await db.projects.find_one({"id": inv["project_id"]}, {"_id": 0})
            # Attribute to the project's linked lead's owner if any, else invoice creator
            if proj and proj.get("lead_id"):
                l = await db.leads.find_one({"id": proj["lead_id"]},
                                            {"_id": 0, "assigned_to_id": 1, "created_by_id": 1})
                if l:
                    owner_id = l.get("assigned_to_id") or l.get("created_by_id")
        if not owner_id:
            owner_id = inv.get("created_by_id") or "unassigned"
        # Skip attributing to owners the caller can't see (non-admins).
        if user.get("role") not in ("super_admin", "admin") and owner_id != user["id"]:
            continue
        row = per_owner.setdefault(owner_id, {
            "owner_id": owner_id,
            "owner_name": (users_map.get(owner_id) or {}).get("first_name", "Unknown"),
            "designation": (users_map.get(owner_id) or {}).get("designation", ""),
            "contacted": 0, "converted": 0, "lost": 0, "in_pipeline": 0,
            "pipeline_value": 0.0, "onboarded_value": 0.0,
            "hot": 0, "cold": 0, "warm": 0,
        })
        row["onboarded_value"] += float(inv.get("total") or 0)

    owners = list(per_owner.values())
    for o in owners:
        o["pipeline_value"] = round(o["pipeline_value"], 2)
        o["onboarded_value"] = round(o["onboarded_value"], 2)
        o["conversion_rate"] = (
            round(100 * o["converted"] / o["contacted"], 1)
            if o["contacted"] else 0.0
        )
    owners.sort(key=lambda r: r["onboarded_value"], reverse=True)

    totals = {
        "total_leads": sum(o["contacted"] + (1 if False else 0) for o in owners),
        "total_contacted": sum(o["contacted"] for o in owners),
        "total_converted": sum(o["converted"] for o in owners),
        "total_lost": sum(o["lost"] for o in owners),
        "pipeline_value": round(sum(o["pipeline_value"] for o in owners), 2),
        "sales_generated": round(sum(o["onboarded_value"] for o in owners), 2),
    }
    return {"owners": owners, "totals": totals}


# =========================================================
# Compose
# =========================================================

router.include_router(settings_router)
router.include_router(pdf_router)
router.include_router(recurring_router)
router.include_router(lead_analytics_router)

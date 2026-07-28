"""User (staff) management routes."""
from fastapi import APIRouter, Depends, HTTPException
from models import ApproveRequest, UserUpdateAdmin, PasswordChange
from auth import get_current_user, require_roles, hash_password, can_see_costs
from db import db
from utils import now_iso, log_activity, push_notification

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
async def list_users(status: str = "", user=Depends(get_current_user)):
    q = {}
    if status:
        q["status"] = status
    projection = {"_id": 0, "password_hash": 0}
    # Non super_admin cannot see salary
    if not can_see_costs(user):
        projection["monthly_salary"] = 0
    users = await db.users.find(q, projection).sort("created_at", -1).to_list(500)
    # Also add active_tasks_count for each user (for assignment dropdown)
    counts = await db.tasks.aggregate([
        {"$match": {"assignee_id": {"$ne": None},
                    "status": {"$in": ["Assigned", "In Progress", "Paused", "Not Started"]}}},
        {"$group": {"_id": "$assignee_id", "n": {"$sum": 1}}},
    ]).to_list(1000)
    count_map = {c["_id"]: c["n"] for c in counts}
    for u in users:
        u["active_tasks_count"] = count_map.get(u["id"], 0)
    return users


@router.get("/{user_id}")
async def get_user(user_id: str, user=Depends(get_current_user)):
    projection = {"_id": 0, "password_hash": 0}
    if not can_see_costs(user) and user_id != user["id"]:
        projection["monthly_salary"] = 0
    u = await db.users.find_one({"id": user_id}, projection)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u


@router.post("/{user_id}/approve")
async def approve_user(user_id: str, payload: ApproveRequest,
                       user=Depends(require_roles("super_admin"))):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one(
        {"id": user_id},
        {"$set": {
            "status": "active",
            "role": payload.role,
            "designation": payload.designation,
            "updated_at": now_iso(),
        }},
    )
    await log_activity(user, "user_approved", "user", user_id,
                       previous=target.get("status"), new="active")
    await push_notification(user_id, "signup_approved",
                            "Access approved",
                            f"Welcome to Raybotix Digital. Role: {payload.role}.")
    return {"ok": True}


@router.post("/{user_id}/reject")
async def reject_user(user_id: str, user=Depends(require_roles("super_admin"))):
    await db.users.update_one({"id": user_id}, {"$set": {"status": "rejected", "updated_at": now_iso()}})
    await log_activity(user, "user_rejected", "user", user_id)
    await push_notification(user_id, "signup_rejected", "Signup rejected",
                            "Your access request was rejected.")
    return {"ok": True}


@router.patch("/{user_id}")
async def update_user(user_id: str, payload: UserUpdateAdmin,
                      user=Depends(require_roles("super_admin", "admin"))):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    # Only super_admin can modify salary/role
    if user["role"] != "super_admin":
        update.pop("monthly_salary", None)
        update.pop("role", None)
    update["updated_at"] = now_iso()
    await db.users.update_one({"id": user_id}, {"$set": update})
    await log_activity(user, "user_updated", "user", user_id,
                       previous={k: target.get(k) for k in update if k in target},
                       new=update)
    return {"ok": True}


@router.post("/{user_id}/reset-password")
async def reset_password(user_id: str, payload: PasswordChange,
                         user=Depends(require_roles("super_admin"))):
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"password_hash": hash_password(payload.new_password), "updated_at": now_iso()}},
    )
    await log_activity(user, "password_reset", "user", user_id)
    return {"ok": True}


@router.delete("/{user_id}")
async def deactivate_user(user_id: str, user=Depends(require_roles("super_admin"))):
    await db.users.update_one({"id": user_id}, {"$set": {"status": "deactivated", "updated_at": now_iso()}})
    await log_activity(user, "user_deactivated", "user", user_id)
    await push_notification(user_id, "account_deactivated", "Account deactivated",
                            "Your account has been deactivated.")
    return {"ok": True}

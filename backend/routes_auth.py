"""Authentication and profile routes."""
from fastapi import APIRouter, HTTPException, Depends
from models import UserCreate, LoginRequest, PasswordChange, ProfileUpdate
from auth import (
    hash_password, verify_password, create_token, get_current_user,
)
from db import db
from utils import now_iso, log_activity
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup")
async def signup(payload: UserCreate):
    existing = await db.users.find_one({"email": payload.email.lower()})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = uuid.uuid4().hex
    now = now_iso()
    doc = {
        "id": user_id,
        "email": payload.email.lower(),
        "first_name": payload.first_name,
        "last_name": payload.last_name,
        "designation": payload.designation,
        "role": "team_member",
        "status": "pending",
        "avatar_url": "",
        "monthly_salary": 0.0,
        "working_hours_per_day": 8.0,
        "working_days_per_month": 25,
        "theme": "system",
        "permissions": [],
        "password_hash": hash_password(payload.password),
        "last_login": None,
        "created_at": now,
        "updated_at": now,
    }
    await db.users.insert_one(doc)
    # Notify all super admins
    admins = await db.users.find({"role": "super_admin", "status": "active"}, {"id": 1}).to_list(50)
    for a in admins:
        await db.notifications.insert_one({
            "id": uuid.uuid4().hex,
            "user_id": a["id"],
            "kind": "signup_pending",
            "title": "New signup pending approval",
            "body": f"{payload.first_name} ({payload.email}) is requesting access.",
            "link_type": "staff",
            "link_id": user_id,
            "read": False,
            "created_at": now,
        })
    return {"ok": True, "message": "Signup received. Await Super Admin approval."}


@router.post("/login")
async def login(payload: LoginRequest):
    user = await db.users.find_one({"email": payload.email.lower()})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("status") != "active":
        raise HTTPException(
            status_code=403,
            detail=f"Account is {user.get('status', 'pending')}. Please contact your Super Admin.",
        )
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login": now_iso()}})
    token = create_token(user["id"])
    user.pop("_id", None)
    user.pop("password_hash", None)
    return {"token": token, "user": user}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user


@router.post("/change-password")
async def change_password(payload: PasswordChange, user=Depends(get_current_user)):
    full = await db.users.find_one({"id": user["id"]})
    if not payload.current_password or not verify_password(payload.current_password, full["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password incorrect")
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_password(payload.new_password), "updated_at": now_iso()}},
    )
    return {"ok": True}


@router.patch("/profile")
async def update_profile(payload: ProfileUpdate, user=Depends(get_current_user)):
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    update["updated_at"] = now_iso()
    await db.users.update_one({"id": user["id"]}, {"$set": update})
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password_hash": 0})
    return fresh

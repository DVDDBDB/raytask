"""Settings routes."""
from fastapi import APIRouter, Depends
from models import CompanySettings
from auth import get_current_user, require_roles
from db import db
from utils import now_iso

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings(user=Depends(get_current_user)):
    s = await db.settings.find_one({"id": "company"}, {"_id": 0})
    if not s:
        defaults = CompanySettings().model_dump()
        defaults["id"] = "company"
        await db.settings.insert_one(defaults)
        return {k: v for k, v in defaults.items() if k != "_id"}
    return s


@router.patch("")
async def update_settings(payload: dict, user=Depends(require_roles("super_admin"))):
    update = {k: v for k, v in payload.items() if k != "id"}
    update["updated_at"] = now_iso()
    await db.settings.update_one({"id": "company"}, {"$set": update}, upsert=True)
    return {"ok": True}

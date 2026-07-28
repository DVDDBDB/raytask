"""File upload/download + reference storage in Mongo."""
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response, Header, Query
from auth import get_current_user, decode_token
from db import db
from storage import put_object, get_object, build_path
from utils import now_iso

router = APIRouter(prefix="/files", tags=["files"])

MAX_IMAGE = 5 * 1024 * 1024   # 5 MB
MAX_FILE = 25 * 1024 * 1024   # 25 MB

IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}


@router.post("/upload")
async def upload(file: UploadFile = File(...), user=Depends(get_current_user)):
    data = await file.read()
    ctype = file.content_type or "application/octet-stream"
    is_image = ctype in IMAGE_TYPES
    limit = MAX_IMAGE if is_image else MAX_FILE
    if len(data) > limit:
        raise HTTPException(status_code=400, detail=f"File too large ({len(data)} bytes, max {limit})")
    path = build_path(user["id"], file.filename or "file")
    result = put_object(path, data, ctype)
    doc = {
        "id": uuid.uuid4().hex,
        "storage_path": result["path"],
        "filename": file.filename or "file",
        "content_type": ctype,
        "size": result.get("size", len(data)),
        "owner_id": user["id"],
        "is_deleted": False,
        "created_at": now_iso(),
    }
    await db.files.insert_one(doc)
    doc.pop("_id", None)
    doc["url"] = f"/api/files/{doc['id']}"
    return doc


async def _resolve_user_from_token(token_value: str):
    if not token_value:
        return None
    payload = decode_token(token_value)
    if not payload:
        return None
    return await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})


@router.get("/{file_id}")
async def download(
    file_id: str,
    authorization: str = Header(None),
    auth: str = Query(None),
):
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:]
    elif auth:
        token = auth
    user = await _resolve_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    rec = await db.files.find_one({"id": file_id, "is_deleted": False}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    data, ctype = get_object(rec["storage_path"])
    headers = {
        "Content-Disposition": f'inline; filename="{rec.get("filename", "file")}"',
        "Cache-Control": "private, max-age=3600",
    }
    return Response(content=data, media_type=rec.get("content_type", ctype), headers=headers)

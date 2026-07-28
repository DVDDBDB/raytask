"""Emergent Object Storage helper."""
import os
import uuid
import logging
import requests

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = "raybotix-digital"

logger = logging.getLogger("raybotix.storage")

_storage_key = None


def _emergent_key() -> str:
    key = os.environ.get("EMERGENT_LLM_KEY")
    if not key:
        raise RuntimeError("EMERGENT_LLM_KEY missing from backend/.env")
    return key


def init_storage():
    global _storage_key
    if _storage_key:
        return _storage_key
    r = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": _emergent_key()}, timeout=30)
    r.raise_for_status()
    _storage_key = r.json()["storage_key"]
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    r = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120,
    )
    if r.status_code == 403:
        # refresh key
        globals()["_storage_key"] = None
        key = init_storage()
        r = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": content_type},
            data=data, timeout=120,
        )
    r.raise_for_status()
    return r.json()


def get_object(path: str):
    key = init_storage()
    r = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60,
    )
    if r.status_code == 403:
        globals()["_storage_key"] = None
        key = init_storage()
        r = requests.get(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key}, timeout=60,
        )
    r.raise_for_status()
    return r.content, r.headers.get("Content-Type", "application/octet-stream")


def build_path(user_id: str, filename: str) -> str:
    ext = "bin"
    if "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()
        # sanitize extension
        ext = "".join(c for c in ext if c.isalnum())[:8] or "bin"
    return f"{APP_NAME}/uploads/{user_id}/{uuid.uuid4().hex}.{ext}"

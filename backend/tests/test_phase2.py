"""Phase 2 backend tests: attachments, WebSocket, Excel exports, recurring tasks."""
import os
import sys
import io
import json
import asyncio
import pytest
import requests
import websockets
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/app/backend")
# Load backend .env so the scheduler test can import db.py (which needs MONGO_URL)
try:
    from dotenv import load_dotenv
    load_dotenv("/app/backend/.env")
except Exception:
    pass

def _read_frontend_env():
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("REACT_APP_BACKEND_URL missing")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env()
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"
WS_BASE = BASE_URL.replace("https://", "wss://").replace("http://", "ws://")


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def tokens():
    return {
        "super": _login("superadmin@raybotix.com", "Admin@123"),
        "manager": _login("neha@raybotix.com", "Password@123"),
        "priya": _login("priya@raybotix.com", "Password@123"),
        "rahul": _login("rahul@raybotix.com", "Password@123"),
        "amit": _login("amit@raybotix.com", "Password@123"),
    }


def _hdr(t):
    return {"Authorization": f"Bearer {t['token']}"}


# =========================================================================
# ATTACHMENTS
# =========================================================================
class TestAttachments:
    def test_upload_returns_metadata(self, tokens):
        # tiny PNG (1x1)
        png = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 200)
        files = {"file": ("test.png", png, "image/png")}
        r = requests.post(f"{API}/files/upload", files=files, headers=_hdr(tokens["priya"]), timeout=30)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ["id", "storage_path", "filename", "content_type", "size", "url"]:
            assert k in d, f"missing {k}"
        assert d["content_type"] == "image/png"
        assert d["filename"] == "test.png"
        assert d["url"] == f"/api/files/{d['id']}"
        pytest.file_id = d["id"]
        pytest.file_size = d["size"]
        pytest.file_meta = {"id": d["id"], "filename": d["filename"], "content_type": d["content_type"], "size": d["size"]}

    def test_download_with_bearer(self, tokens):
        r = requests.get(f"{API}/files/{pytest.file_id}", headers=_hdr(tokens["priya"]), timeout=30)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/png")
        assert "Content-Disposition" in r.headers or "content-disposition" in r.headers
        assert len(r.content) > 0

    def test_download_with_query_auth(self, tokens):
        tok = tokens["priya"]["token"]
        r = requests.get(f"{API}/files/{pytest.file_id}?auth={tok}", timeout=30)
        assert r.status_code == 200
        assert len(r.content) > 0

    def test_download_no_token_401(self):
        r = requests.get(f"{API}/files/{pytest.file_id}", timeout=30)
        assert r.status_code == 401

    def test_download_not_found_404(self, tokens):
        r = requests.get(f"{API}/files/nonexistent-id-xyz", headers=_hdr(tokens["priya"]), timeout=30)
        assert r.status_code == 404


# =========================================================================
# TASKS WITH ATTACHMENTS
# =========================================================================
class TestTaskAttachments:
    def test_create_task_with_attachments(self, tokens):
        payload = {
            "title": "TEST_attach task",
            "description": "with file",
            "assignee_id": _me(tokens["priya"])["id"],
            "priority": "Medium",
            "attachments": [pytest.file_meta],
        }
        r = requests.post(f"{API}/tasks", json=payload, headers=_hdr(tokens["manager"]), timeout=30)
        assert r.status_code in (200, 201), r.text
        t = r.json()
        assert len(t.get("attachments", [])) == 1
        assert t["attachments"][0]["id"] == pytest.file_meta["id"]
        pytest.task_id = t["id"]

    def test_get_task_has_attachments(self, tokens):
        r = requests.get(f"{API}/tasks/{pytest.task_id}", headers=_hdr(tokens["priya"]), timeout=30)
        assert r.status_code == 200
        assert len(r.json()["attachments"]) == 1

    def test_assignee_patch_attachments(self, tokens):
        # Upload another file
        files = {"file": ("second.png", b"\x89PNG\r\n\x1a\n" + b"\x01" * 100, "image/png")}
        up = requests.post(f"{API}/files/upload", files=files, headers=_hdr(tokens["priya"]), timeout=30).json()
        new_att = [{"id": up["id"], "filename": up["filename"], "content_type": up["content_type"], "size": up["size"]}]
        r = requests.patch(f"{API}/tasks/{pytest.task_id}", json={"attachments": new_att}, headers=_hdr(tokens["priya"]), timeout=30)
        assert r.status_code == 200, r.text
        # PATCH returns {"ok": True}; verify via GET
        g = requests.get(f"{API}/tasks/{pytest.task_id}", headers=_hdr(tokens["priya"]), timeout=30).json()
        assert len(g["attachments"]) == 1
        assert g["attachments"][0]["id"] == up["id"]

    def test_random_member_cannot_patch(self, tokens):
        r = requests.patch(f"{API}/tasks/{pytest.task_id}", json={"attachments": []}, headers=_hdr(tokens["amit"]), timeout=30)
        assert r.status_code == 403, f"expected 403, got {r.status_code} body={r.text[:200]}"


# =========================================================================
# EXCEL EXPORTS
# =========================================================================
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class TestExports:
    @pytest.mark.parametrize("path", ["tasks.xlsx", "costs.xlsx", "productivity.xlsx"])
    def test_super_admin_can_download(self, tokens, path):
        r = requests.get(f"{API}/exports/{path}", headers=_hdr(tokens["super"]), timeout=60)
        assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:200]}"
        assert r.headers["content-type"] == XLSX_MIME
        assert len(r.content) > 2048, f"{path} too small: {len(r.content)} bytes"
        # xlsx = ZIP magic
        assert r.content[:2] == b"PK"

    def test_manager_can_tasks_and_productivity(self, tokens):
        for p in ["tasks.xlsx", "productivity.xlsx"]:
            r = requests.get(f"{API}/exports/{p}", headers=_hdr(tokens["manager"]), timeout=60)
            assert r.status_code == 200, f"{p} manager: {r.status_code}"

    def test_manager_forbidden_costs(self, tokens):
        r = requests.get(f"{API}/exports/costs.xlsx", headers=_hdr(tokens["manager"]), timeout=30)
        assert r.status_code == 403

    def test_team_member_forbidden_all(self, tokens):
        for p in ["tasks.xlsx", "costs.xlsx", "productivity.xlsx"]:
            r = requests.get(f"{API}/exports/{p}", headers=_hdr(tokens["priya"]), timeout=30)
            assert r.status_code == 403, f"{p} priya expected 403 got {r.status_code}"


# =========================================================================
# WEBSOCKET
# =========================================================================
def _me(tok):
    r = requests.get(f"{API}/auth/me", headers=_hdr(tok), timeout=30)
    return r.json()


async def _ensure_conversation(sender_tok, other_id):
    # send a bootstrap message to auto-create conv
    r = requests.post(f"{API}/messages",
                      json={"recipient_ids": [other_id], "body": "hi"},
                      headers=_hdr(sender_tok), timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["conversation_id"]


class TestWebSocket:
    def test_invalid_token_closes_4401(self):
        # NOTE: routes_ws.py calls ws.close(4401) before ws.accept(), which under
        # ASGI/Starlette manifests as an HTTP 403 during the WebSocket handshake
        # (the client never sees the 4401 close frame). Accept either behaviour
        # as "connection rejected".
        async def run():
            uri = f"{WS_BASE}/api/ws?token=invalid.jwt.here"
            try:
                async with websockets.connect(uri) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=3)
                    return "opened"
            except websockets.exceptions.ConnectionClosed as e:
                return ("closed", e.code)
            except websockets.exceptions.InvalidStatus as e:
                return ("http", e.response.status_code)
        result = asyncio.run(run())
        # Accept HTTP 403/401 handshake rejection OR close code 4401
        assert (isinstance(result, tuple) and (
            (result[0] == "http" and result[1] in (401, 403))
            or (result[0] == "closed" and result[1] == 4401)
        )), f"expected rejection, got {result}"

    def test_no_token_closes(self):
        async def run():
            uri = f"{WS_BASE}/api/ws"
            try:
                async with websockets.connect(uri) as ws:
                    await asyncio.wait_for(ws.recv(), timeout=3)
                    return "opened"
            except websockets.exceptions.ConnectionClosed as e:
                return ("closed", e.code)
            except websockets.exceptions.InvalidStatus as e:
                return ("http", e.response.status_code)
        result = asyncio.run(run())
        assert isinstance(result, tuple) and result[0] in ("http", "closed"), f"expected rejection, got {result}"

    def test_ready_frame_and_broadcast(self, tokens):
        priya_id = _me(tokens["priya"])["id"]
        rahul_id = _me(tokens["rahul"])["id"]

        async def run():
            # First ensure a conversation exists
            conv_id = await _ensure_conversation(tokens["priya"], rahul_id)

            uri_priya = f"{WS_BASE}/api/ws?token={tokens['priya']['token']}"
            uri_rahul = f"{WS_BASE}/api/ws?token={tokens['rahul']['token']}"

            async with websockets.connect(uri_priya) as ws_p, websockets.connect(uri_rahul) as ws_r:
                # Ready frames
                ready_p = json.loads(await asyncio.wait_for(ws_p.recv(), timeout=5))
                ready_r = json.loads(await asyncio.wait_for(ws_r.recv(), timeout=5))
                assert ready_p["type"] == "ready"
                assert ready_r["type"] == "ready"
                assert ready_p["user_id"] == priya_id
                assert ready_r["user_id"] == rahul_id

                # Priya sends a message via HTTP
                body_txt = f"phase2 test {datetime.now(timezone.utc).isoformat()}"
                resp = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: requests.post(f"{API}/messages",
                                          json={"conversation_id": conv_id, "body": body_txt},
                                          headers=_hdr(tokens["priya"]), timeout=30)
                )
                assert resp.status_code == 200, resp.text

                # Rahul should get the broadcast
                r_msg = json.loads(await asyncio.wait_for(ws_r.recv(), timeout=5))
                assert r_msg["type"] == "message"
                assert r_msg["conversation_id"] == conv_id
                assert r_msg["message"]["body"] == body_txt

                # Priya's own WS also receives (self-broadcast for multi-tab sync)
                p_msg = json.loads(await asyncio.wait_for(ws_p.recv(), timeout=5))
                assert p_msg["type"] == "message"
                assert p_msg["message"]["body"] == body_txt

        asyncio.run(run())


# =========================================================================
# RECURRING TASKS
# =========================================================================
class TestRecurring:
    def test_create_recurring_task_populates_next_run_at(self, tokens):
        priya_id = _me(tokens["priya"])["id"]
        payload = {
            "title": "TEST_recurring weekly",
            "description": "template",
            "assignee_id": priya_id,
            "priority": "Medium",
            "recurrence": {"enabled": True, "frequency": "weekly"},
        }
        r = requests.post(f"{API}/tasks", json=payload, headers=_hdr(tokens["manager"]), timeout=30)
        assert r.status_code in (200, 201), r.text
        t = r.json()
        assert t.get("recurrence") is not None
        assert t["recurrence"]["enabled"] is True
        assert t["recurrence"].get("next_run_at"), "next_run_at should be auto-populated"
        pytest.template_id = t["id"]

    def test_get_task_returns_recurrence(self, tokens):
        r = requests.get(f"{API}/tasks/{pytest.template_id}", headers=_hdr(tokens["manager"]), timeout=30)
        assert r.status_code == 200
        assert r.json()["recurrence"]["enabled"] is True

    def test_scheduler_tick_spawns_child(self, tokens):
        # Backdate next_run_at via mongo directly, then run _tick.
        async def run():
            from db import db
            from recurring import _tick
            past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
            await db.tasks.update_one(
                {"id": pytest.template_id},
                {"$set": {"recurrence.next_run_at": past}},
            )
            processed = await _tick()
            return processed
        asyncio.run(run())

        # Poll for a spawned child
        found = None
        for _ in range(10):
            r = requests.get(f"{API}/tasks?parent_task_id={pytest.template_id}",
                             headers=_hdr(tokens["manager"]), timeout=30)
            # If filter unsupported, fall back to full list
            if r.status_code == 200:
                items = r.json()
                # some APIs return list wrapped
                if isinstance(items, dict):
                    items = items.get("items") or items.get("tasks") or []
                for it in items:
                    if it.get("spawned_from_recurring") == pytest.template_id and it["id"] != pytest.template_id:
                        found = it
                        break
            if found:
                break
        # fallback: full task list filter client-side
        if not found:
            r = requests.get(f"{API}/tasks", headers=_hdr(tokens["manager"]), timeout=30)
            items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
            for it in items:
                if it.get("spawned_from_recurring") == pytest.template_id and it["id"] != pytest.template_id:
                    found = it; break
        assert found, "Spawned child task not found"
        assert found["parent_task_id"] == pytest.template_id
        assert found["status"] == "Assigned"
        assert found["spawned_from_recurring"] == pytest.template_id
        assert len(found.get("workflow", [])) == 1

        # Template's next_run_at should now be in the future
        r2 = requests.get(f"{API}/tasks/{pytest.template_id}", headers=_hdr(tokens["manager"]), timeout=30)
        tpl = r2.json()
        assert tpl["recurrence"]["enabled"] is True
        nxt = tpl["recurrence"]["next_run_at"]
        nxt_dt = datetime.fromisoformat(nxt.replace("Z", "+00:00"))
        assert nxt_dt > datetime.now(timezone.utc), f"next_run_at not advanced: {nxt}"

    def test_disable_recurrence_via_patch(self, tokens):
        r = requests.patch(f"{API}/tasks/{pytest.template_id}",
                           json={"recurrence": {"enabled": False, "frequency": "weekly"}},
                           headers=_hdr(tokens["manager"]), timeout=30)
        assert r.status_code == 200, r.text
        g = requests.get(f"{API}/tasks/{pytest.template_id}", headers=_hdr(tokens["manager"]), timeout=30).json()
        assert g["recurrence"]["enabled"] is False

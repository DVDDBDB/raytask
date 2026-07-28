"""Raybotix Digital – comprehensive backend API tests.

Covers auth, users approval, projects, tasks lifecycle (timer/handoff/reopen/
review), messages, notifications, activity, settings, analytics, permissions.
"""
import os
import time
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------- Setup ----------
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[2] / "frontend" / ".env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"

CREDS = {
    "super": ("superadmin@raybotix.com", "Admin@123"),
    "manager": ("neha@raybotix.com", "Password@123"),
    "priya": ("priya@raybotix.com", "Password@123"),
    "rahul": ("rahul@raybotix.com", "Password@123"),
    "amit": ("amit@raybotix.com", "Password@123"),
    "karan": ("karan@raybotix.com", "Password@123"),
}


def login(email, password):
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    return data["token"], data["user"]


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def tokens():
    out = {}
    for k, (e, p) in CREDS.items():
        tok, u = login(e, p)
        out[k] = {"token": tok, "user": u, "email": e}
    return out


@pytest.fixture(scope="session")
def users_map(tokens):
    r = requests.get(f"{BASE_URL}/users", headers=hdr(tokens["super"]["token"]))
    assert r.status_code == 200
    return {u["email"]: u for u in r.json()}


# ---------- AUTH ----------
class TestAuth:
    def test_login_success(self):
        r = requests.post(f"{BASE_URL}/auth/login", json={"email": CREDS["super"][0], "password": CREDS["super"][1]})
        assert r.status_code == 200
        data = r.json()
        assert "token" in data and "user" in data
        assert data["user"]["email"] == CREDS["super"][0]
        assert data["user"]["role"] == "super_admin"
        assert "password_hash" not in data["user"]

    def test_login_wrong_password(self):
        r = requests.post(f"{BASE_URL}/auth/login", json={"email": CREDS["super"][0], "password": "wrong"})
        assert r.status_code == 401

    def test_me_with_token(self, tokens):
        r = requests.get(f"{BASE_URL}/auth/me", headers=hdr(tokens["super"]["token"]))
        assert r.status_code == 200
        assert r.json()["email"] == CREDS["super"][0]

    def test_me_without_token(self):
        r = requests.get(f"{BASE_URL}/auth/me")
        assert r.status_code == 401


# ---------- SIGNUP APPROVAL ----------
class TestSignupApproval:
    def test_signup_pending_cannot_login_then_approve(self, tokens):
        email = f"test_signup_{uuid.uuid4().hex[:8]}@raybotix.com"
        payload = {"email": email, "password": "Test@1234", "first_name": "Test", "last_name": "User",
                   "designation": "Other"}
        r = requests.post(f"{BASE_URL}/auth/signup", json=payload)
        assert r.status_code == 200
        # cannot login yet
        r2 = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": "Test@1234"})
        assert r2.status_code == 403

        # find user id as super
        users = requests.get(f"{BASE_URL}/users", headers=hdr(tokens["super"]["token"])).json()
        u = next((x for x in users if x["email"] == email), None)
        assert u and u["status"] == "pending"

        # approve
        r3 = requests.post(
            f"{BASE_URL}/users/{u['id']}/approve",
            headers=hdr(tokens["super"]["token"]),
            json={"role": "team_member", "designation": "Content Writer"},
        )
        assert r3.status_code == 200

        # now login works
        r4 = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": "Test@1234"})
        assert r4.status_code == 200

        # reject flow – create another user and reject
        email2 = f"test_signup_{uuid.uuid4().hex[:8]}@raybotix.com"
        requests.post(f"{BASE_URL}/auth/signup", json={**payload, "email": email2})
        users = requests.get(f"{BASE_URL}/users", headers=hdr(tokens["super"]["token"])).json()
        u2 = next(x for x in users if x["email"] == email2)
        r5 = requests.post(f"{BASE_URL}/users/{u2['id']}/reject", headers=hdr(tokens["super"]["token"]))
        assert r5.status_code == 200
        u2_after = requests.get(f"{BASE_URL}/users/{u2['id']}", headers=hdr(tokens["super"]["token"])).json()
        assert u2_after["status"] == "rejected"


# ---------- USERS LIST ----------
class TestUsers:
    def test_list_users_super_has_salary(self, tokens):
        r = requests.get(f"{BASE_URL}/users", headers=hdr(tokens["super"]["token"]))
        assert r.status_code == 200
        users = r.json()
        assert len(users) >= 6
        for u in users:
            assert "active_tasks_count" in u
        # Priya has monthly_salary > 0
        priya = next(u for u in users if u["email"] == CREDS["priya"][0])
        assert priya["monthly_salary"] > 0

    def test_list_users_non_admin_no_salary(self, tokens):
        r = requests.get(f"{BASE_URL}/users", headers=hdr(tokens["priya"]["token"]))
        assert r.status_code == 200
        users = r.json()
        for u in users:
            # salary either missing or 0
            assert u.get("monthly_salary", 0) in (0, 0.0, None) or "monthly_salary" not in u


# ---------- PROJECTS ----------
class TestProjects:
    def test_list_projects_seed(self, tokens):
        r = requests.get(f"{BASE_URL}/projects", headers=hdr(tokens["super"]["token"]))
        assert r.status_code == 200
        projects = r.json()
        assert len(projects) >= 3
        for p in projects:
            assert "total_tasks" in p and "completed_tasks" in p
            assert "monthly_cost" in p and "total_cost" in p

    def test_list_projects_team_no_cost(self, tokens):
        r = requests.get(f"{BASE_URL}/projects", headers=hdr(tokens["priya"]["token"]))
        assert r.status_code == 200
        for p in r.json():
            assert "monthly_cost" not in p and "total_cost" not in p

    def test_create_project_super(self, tokens):
        payload = {"name": f"TEST_Project_{uuid.uuid4().hex[:6]}", "company_name": "TestCo"}
        r = requests.post(f"{BASE_URL}/projects", headers=hdr(tokens["super"]["token"]), json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == payload["name"]
        assert "id" in data

    def test_manager_can_create_project(self, tokens):
        payload = {"name": f"TEST_MgrProj_{uuid.uuid4().hex[:6]}"}
        r = requests.post(f"{BASE_URL}/projects", headers=hdr(tokens["manager"]["token"]), json=payload)
        assert r.status_code == 200


# ---------- TASKS ----------
class TestTasks:
    def test_list_seed_tasks(self, tokens):
        r = requests.get(f"{BASE_URL}/tasks", headers=hdr(tokens["super"]["token"]))
        assert r.status_code == 200
        tasks = r.json()
        assert len(tasks) >= 6
        # Sorted urgent first
        priorities = [t["priority"] for t in tasks]
        assert priorities[0] == "Urgent"

    def test_filter_by_priority(self, tokens):
        r = requests.get(f"{BASE_URL}/tasks?priority=Urgent", headers=hdr(tokens["super"]["token"]))
        assert r.status_code == 200
        for t in r.json():
            assert t["priority"] == "Urgent"

    def test_create_task_future_becomes_scheduled(self, tokens, users_map):
        future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        payload = {
            "title": f"TEST_future_{uuid.uuid4().hex[:6]}",
            "assignee_id": users_map[CREDS["priya"][0]]["id"],
            "status": "Assigned",
            "priority": "Low",
            "scheduled_start_date": future,
        }
        r = requests.post(f"{BASE_URL}/tasks", headers=hdr(tokens["super"]["token"]), json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "Scheduled"


# ---------- TIMER LIFECYCLE ----------
@pytest.fixture(scope="session")
def priya_task_ids(tokens, users_map):
    """Return two task IDs assigned to Priya so we can test single-active-timer + full lifecycle.
    Creates fresh tasks to keep tests idempotent across re-runs."""
    priya_id = users_map[CREDS["priya"][0]]["id"]
    ids = []
    for i in range(2):
        r = requests.post(
            f"{BASE_URL}/tasks", headers=hdr(tokens["super"]["token"]),
            json={"title": f"TEST_timer_{i}_{uuid.uuid4().hex[:6]}",
                  "assignee_id": priya_id, "priority": "Medium"},
        )
        assert r.status_code == 200
        ids.append(r.json()["id"])
    return ids


class TestTimerLifecycle:
    def test_full_timer_flow_and_single_active(self, tokens, priya_task_ids):
        tokP = tokens["priya"]["token"]
        t1, t2 = priya_task_ids
        # start t1
        r = requests.post(f"{BASE_URL}/tasks/{t1}/start", headers=hdr(tokP))
        assert r.status_code == 200
        # verify status
        r = requests.get(f"{BASE_URL}/tasks/{t1}", headers=hdr(tokP))
        assert r.json()["status"] == "In Progress"
        assert r.json()["active_session"] is not None

        # trying to start t2 => 400
        r = requests.post(f"{BASE_URL}/tasks/{t2}/start", headers=hdr(tokP))
        assert r.status_code == 400
        assert "active" in r.text.lower() or "pause" in r.text.lower()

        # pause t1
        time.sleep(1.2)
        r = requests.post(f"{BASE_URL}/tasks/{t1}/pause", headers=hdr(tokP))
        assert r.status_code == 200
        r = requests.get(f"{BASE_URL}/tasks/{t1}", headers=hdr(tokP))
        assert r.json()["status"] == "Paused"

        # resume
        r = requests.post(f"{BASE_URL}/tasks/{t1}/resume", headers=hdr(tokP))
        assert r.status_code == 200
        r = requests.get(f"{BASE_URL}/tasks/{t1}", headers=hdr(tokP))
        assert r.json()["status"] == "In Progress"

        # complete
        time.sleep(1.2)
        r = requests.post(f"{BASE_URL}/tasks/{t1}/complete", headers=hdr(tokP))
        assert r.status_code == 200
        r = requests.get(f"{BASE_URL}/tasks/{t1}", headers=hdr(tokP))
        data = r.json()
        assert data["status"] == "Completed"
        assert data["completed_at"] is not None
        # sessions exist and total > 0
        assert data["total_team_seconds"] > 0
        assert len(data["timer_sessions"]) >= 1


# ---------- HANDOFF ----------
class TestHandoff:
    def test_handoff_continue_same(self, tokens, users_map):
        # Create a fresh task assigned to Priya, then handoff to Rahul on same
        priya_id = users_map[CREDS["priya"][0]]["id"]
        rahul_id = users_map[CREDS["rahul"][0]]["id"]
        cr = requests.post(
            f"{BASE_URL}/tasks", headers=hdr(tokens["super"]["token"]),
            json={"title": f"TEST_handoff_same_{uuid.uuid4().hex[:6]}",
                  "assignee_id": priya_id, "priority": "Medium"},
        )
        assert cr.status_code == 200
        tid = cr.json()["id"]

        r = requests.post(
            f"{BASE_URL}/tasks/{tid}/handoff", headers=hdr(tokens["priya"]["token"]),
            json={"next_assignee_id": rahul_id, "remarks": "Ready for edit",
                  "create_next_task": False},
        )
        assert r.status_code == 200, r.text
        detail = requests.get(f"{BASE_URL}/tasks/{tid}", headers=hdr(tokens["super"]["token"])).json()
        assert detail["assignee_id"] == rahul_id
        assert detail["status"] == "Assigned"
        assert len(detail["workflow"]) >= 2
        assert len(detail["reassignment_history"]) >= 1

    def test_handoff_create_next(self, tokens, users_map):
        priya_id = users_map[CREDS["priya"][0]]["id"]
        rahul_id = users_map[CREDS["rahul"][0]]["id"]
        cr = requests.post(
            f"{BASE_URL}/tasks", headers=hdr(tokens["super"]["token"]),
            json={"title": f"TEST_handoff_next_{uuid.uuid4().hex[:6]}",
                  "assignee_id": priya_id, "priority": "Medium"},
        )
        parent_id = cr.json()["id"]

        due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        next_task = {"title": "TEST_child_task", "priority": "Medium",
                     "estimated_duration_minutes": 60, "due_date": due}
        r = requests.post(
            f"{BASE_URL}/tasks/{parent_id}/handoff",
            headers=hdr(tokens["priya"]["token"]),
            json={"next_assignee_id": rahul_id, "remarks": "editing",
                  "create_next_task": True, "next_task": next_task},
        )
        assert r.status_code == 200, r.text
        child_id = r.json()["next_task_id"]
        # parent should be completed
        parent = requests.get(f"{BASE_URL}/tasks/{parent_id}", headers=hdr(tokens["super"]["token"])).json()
        assert parent["status"] == "Completed"
        # child links to parent
        child = requests.get(f"{BASE_URL}/tasks/{child_id}", headers=hdr(tokens["super"]["token"])).json()
        assert child["parent_task_id"] == parent_id
        assert child["assignee_id"] == rahul_id
        # parent.children includes child
        assert any(c["id"] == child_id for c in parent["children"])


# ---------- REOPEN / REVIEW ----------
class TestReopenReview:
    def test_reopen_completed_task(self, tokens, users_map):
        priya_id = users_map[CREDS["priya"][0]]["id"]
        # create + complete
        cr = requests.post(
            f"{BASE_URL}/tasks", headers=hdr(tokens["super"]["token"]),
            json={"title": f"TEST_reopen_{uuid.uuid4().hex[:6]}",
                  "assignee_id": priya_id, "priority": "Low"},
        )
        tid = cr.json()["id"]
        requests.post(f"{BASE_URL}/tasks/{tid}/start", headers=hdr(tokens["priya"]["token"]))
        requests.post(f"{BASE_URL}/tasks/{tid}/complete", headers=hdr(tokens["priya"]["token"]))
        before = requests.get(f"{BASE_URL}/tasks/{tid}", headers=hdr(tokens["super"]["token"])).json()
        wf_before = len(before["workflow"])
        due = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        r = requests.post(
            f"{BASE_URL}/tasks/{tid}/reopen", headers=hdr(tokens["super"]["token"]),
            json={"assignee_id": priya_id, "reason": "needs redo",
                  "due_date": due, "priority": "Medium", "instructions": ""},
        )
        assert r.status_code == 200, r.text
        after = requests.get(f"{BASE_URL}/tasks/{tid}", headers=hdr(tokens["super"]["token"])).json()
        assert after["status"] == "Reopened"
        assert len(after["workflow"]) == wf_before + 1

    def test_review_approve(self, tokens, users_map):
        # Create a task in Waiting for Review state
        priya_id = users_map[CREDS["priya"][0]]["id"]
        cr = requests.post(f"{BASE_URL}/tasks", headers=hdr(tokens["super"]["token"]),
                           json={"title": f"TEST_review_{uuid.uuid4().hex[:6]}",
                                 "assignee_id": priya_id, "priority": "Low",
                                 "status": "Waiting for Review"})
        assert cr.status_code == 200
        tid = cr.json()["id"]
        r = requests.post(f"{BASE_URL}/tasks/{tid}/review", headers=hdr(tokens["super"]["token"]),
                          json={"action": "approve", "comment": "Looks good"})
        assert r.status_code == 200
        detail = requests.get(f"{BASE_URL}/tasks/{tid}", headers=hdr(tokens["super"]["token"])).json()
        assert detail["review_status"] == "Approved"
        assert any(c.get("kind") == "review" and c["body"] == "Looks good" for c in detail["comments"])


# ---------- PROJECT COST ----------
class TestProjectCost:
    def test_cost_after_timer(self, tokens, users_map):
        priya_id = users_map[CREDS["priya"][0]]["id"]
        # find a project & task for Priya
        tasks = requests.get(f"{BASE_URL}/tasks?assignee_id={priya_id}", headers=hdr(tokens["super"]["token"])).json()
        target = next((t for t in tasks if t.get("project_id") and t["status"] in ("Assigned", "Paused")), None)
        if not target:
            # create one
            projs = requests.get(f"{BASE_URL}/projects", headers=hdr(tokens["super"]["token"])).json()
            cr = requests.post(f"{BASE_URL}/tasks", headers=hdr(tokens["super"]["token"]),
                               json={"title": f"TEST_cost_{uuid.uuid4().hex[:6]}",
                                     "assignee_id": priya_id,
                                     "project_id": projs[0]["id"], "priority": "Low"})
            target = cr.json()
        pid = target["project_id"]
        tid = target["id"]
        tokP = tokens["priya"]["token"]
        requests.post(f"{BASE_URL}/tasks/{tid}/start", headers=hdr(tokP))
        time.sleep(3)
        requests.post(f"{BASE_URL}/tasks/{tid}/complete", headers=hdr(tokP))
        proj = requests.get(f"{BASE_URL}/projects/{pid}", headers=hdr(tokens["super"]["token"])).json()
        assert proj["monthly_cost"] > 0
        assert proj["total_cost"] > 0
        costs = requests.get(f"{BASE_URL}/analytics/costs", headers=hdr(tokens["super"]["token"])).json()
        assert any(p["project_id"] == pid for p in costs["projects"])


# ---------- ANALYTICS ----------
class TestAnalytics:
    def test_dashboard_super(self, tokens):
        r = requests.get(f"{BASE_URL}/analytics/dashboard", headers=hdr(tokens["super"]["token"]))
        assert r.status_code == 200
        data = r.json()
        for k in ("active_users", "active_timers", "monthly_cost"):
            assert k in data

    def test_dashboard_team_no_cost(self, tokens):
        r = requests.get(f"{BASE_URL}/analytics/dashboard", headers=hdr(tokens["priya"]["token"]))
        assert r.status_code == 200
        assert "monthly_cost" not in r.json()

    def test_productivity(self, tokens):
        r = requests.get(f"{BASE_URL}/analytics/productivity", headers=hdr(tokens["super"]["token"]))
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list)
        if arr:
            for item in arr:
                assert "hourly_cost" in item and "monthly_cost" in item

    def test_employee_analytics(self, tokens, users_map):
        priya_id = users_map[CREDS["priya"][0]]["id"]
        r = requests.get(f"{BASE_URL}/analytics/employee/{priya_id}", headers=hdr(tokens["super"]["token"]))
        assert r.status_code == 200
        data = r.json()
        assert "daily" in data and isinstance(data["daily"], list)
        assert "completed" in data and "reopened" in data and "overdue" in data


# ---------- MESSAGES ----------
class TestMessages:
    def test_conversation_and_send(self, tokens, users_map):
        rahul_id = users_map[CREDS["rahul"][0]]["id"]
        tokP = tokens["priya"]["token"]
        # create conversation
        r = requests.post(f"{BASE_URL}/messages/conversations", headers=hdr(tokP),
                          json={"participant_ids": [rahul_id]})
        assert r.status_code == 200
        conv_id = r.json()["id"]
        # duplicate 1-1 returns same
        r2 = requests.post(f"{BASE_URL}/messages/conversations", headers=hdr(tokP),
                           json={"participant_ids": [rahul_id]})
        assert r2.json()["id"] == conv_id

        # send message
        m = requests.post(f"{BASE_URL}/messages", headers=hdr(tokP),
                          json={"conversation_id": conv_id, "body": "hello TEST"})
        assert m.status_code == 200

        # rahul reads messages
        gr = requests.get(f"{BASE_URL}/messages/{conv_id}", headers=hdr(tokens["rahul"]["token"]))
        assert gr.status_code == 200
        msgs = gr.json()
        assert any(mm["body"] == "hello TEST" for mm in msgs)

        # rahul has notification kind=new_message
        n = requests.get(f"{BASE_URL}/notifications", headers=hdr(tokens["rahul"]["token"])).json()
        assert any(i["kind"] == "new_message" for i in n["items"])


# ---------- NOTIFICATIONS ----------
class TestNotifications:
    def test_list_and_read(self, tokens):
        tokR = tokens["rahul"]["token"]
        r = requests.get(f"{BASE_URL}/notifications", headers=hdr(tokR))
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and "unread" in data
        if data["items"]:
            nid = data["items"][0]["id"]
            r2 = requests.post(f"{BASE_URL}/notifications/{nid}/read", headers=hdr(tokR))
            assert r2.status_code == 200
        r3 = requests.post(f"{BASE_URL}/notifications/read-all", headers=hdr(tokR))
        assert r3.status_code == 200
        after = requests.get(f"{BASE_URL}/notifications", headers=hdr(tokR)).json()
        assert after["unread"] == 0


# ---------- ACTIVITY ----------
class TestActivity:
    def test_activity_admin_ok(self, tokens):
        r = requests.get(f"{BASE_URL}/activity", headers=hdr(tokens["super"]["token"]))
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) > 0

    def test_activity_team_forbidden(self, tokens):
        r = requests.get(f"{BASE_URL}/activity", headers=hdr(tokens["priya"]["token"]))
        assert r.status_code == 403


# ---------- SETTINGS ----------
class TestSettings:
    def test_get_settings(self, tokens):
        r = requests.get(f"{BASE_URL}/settings", headers=hdr(tokens["priya"]["token"]))
        assert r.status_code == 200
        s = r.json()
        assert s["working_days_per_month"] == 25
        assert "designations" in s and isinstance(s["designations"], list)

    def test_patch_settings_forbidden_for_team(self, tokens):
        r = requests.patch(f"{BASE_URL}/settings", headers=hdr(tokens["priya"]["token"]),
                           json={"company_name": "X"})
        assert r.status_code == 403

    def test_patch_settings_super_ok(self, tokens):
        r = requests.patch(f"{BASE_URL}/settings", headers=hdr(tokens["super"]["token"]),
                           json={"contact": "TEST-contact"})
        assert r.status_code == 200


# ---------- PERMISSIONS ----------
class TestPermissions:
    def test_team_cannot_approve(self, tokens, users_map):
        any_uid = next(iter(users_map.values()))["id"]
        r = requests.post(f"{BASE_URL}/users/{any_uid}/approve",
                          headers=hdr(tokens["priya"]["token"]),
                          json={"role": "team_member", "designation": "Other"})
        assert r.status_code == 403

    def test_team_cannot_costs(self, tokens):
        r = requests.get(f"{BASE_URL}/analytics/costs", headers=hdr(tokens["priya"]["token"]))
        assert r.status_code == 403

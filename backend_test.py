#!/usr/bin/env python3
"""
Backend test for "Failed to create task" bug fix.
Tests that POST /api/tasks correctly handles naive datetime-local inputs
and timezone-aware ISO dates without raising TypeError.
"""
import requests
import sys
from datetime import datetime, timezone

# Backend URL from frontend/.env
BASE_URL = "https://ray-task-hub.preview.emergentagent.com/api"

# Test credentials
SUPER_ADMIN_EMAIL = "superadmin@raybotix.com"
SUPER_ADMIN_PASSWORD = "Admin@123"

# Global variables for test data
jwt_token = None
project_id = None
assignee_id = None
created_task_ids = []


def log(msg):
    print(f"[TEST] {msg}")


def login():
    """Test Case 1: Login as super admin and obtain JWT."""
    global jwt_token
    log("Test 1: Login as super admin")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": SUPER_ADMIN_EMAIL,
        "password": SUPER_ADMIN_PASSWORD
    })
    if resp.status_code != 200:
        log(f"❌ FAIL: Login returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    data = resp.json()
    jwt_token = data.get("token")
    if not jwt_token:
        log("❌ FAIL: No token in response")
        return False
    log(f"✅ PASS: Login successful, JWT obtained")
    return True


def get_project():
    """Test Case 2: GET /api/projects and pick a project id."""
    global project_id
    log("Test 2: GET /api/projects")
    headers = {"Authorization": f"Bearer {jwt_token}"}
    resp = requests.get(f"{BASE_URL}/projects", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: GET /api/projects returned {resp.status_code}")
        return False
    projects = resp.json()
    if not projects:
        log("❌ FAIL: No projects found")
        return False
    # Pick first project
    project_id = projects[0]["id"]
    project_name = projects[0].get("name", "Unknown")
    log(f"✅ PASS: Found project '{project_name}' (id: {project_id})")
    return True


def get_user():
    """Test Case 3: GET /api/users and pick an active user id."""
    global assignee_id
    log("Test 3: GET /api/users")
    headers = {"Authorization": f"Bearer {jwt_token}"}
    resp = requests.get(f"{BASE_URL}/users", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: GET /api/users returned {resp.status_code}")
        return False
    users = resp.json()
    active_users = [u for u in users if u.get("status") == "active"]
    if not active_users:
        log("❌ FAIL: No active users found")
        return False
    # Pick first active user
    assignee_id = active_users[0]["id"]
    user_name = active_users[0].get("first_name", "Unknown")
    log(f"✅ PASS: Found active user '{user_name}' (id: {assignee_id})")
    return True


def create_task_basic():
    """Test Case 4: POST /api/tasks with basic fields, NO dates."""
    log("Test 4: POST /api/tasks with basic fields (no dates)")
    headers = {"Authorization": f"Bearer {jwt_token}"}
    payload = {
        "title": "AutoTest — basic task without dates",
        "description": "Testing basic task creation",
        "project_id": project_id,
        "assignee_id": assignee_id,
        "priority": "Medium",
        "status": "Assigned",
        "estimated_duration_minutes": 60,
        "tags": [],
        "instructions": "",
        "reference_links": [],
        "attachments": []
    }
    resp = requests.post(f"{BASE_URL}/tasks", headers=headers, json=payload)
    if resp.status_code != 200:
        log(f"❌ FAIL: POST /api/tasks returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    data = resp.json()
    task_id = data.get("id")
    task_status = data.get("status")
    if not task_id:
        log("❌ FAIL: No 'id' in response")
        return False
    if task_status != "Assigned":
        log(f"❌ FAIL: Expected status 'Assigned', got '{task_status}'")
        return False
    created_task_ids.append(task_id)
    log(f"✅ PASS: Task created (id: {task_id}, status: {task_status})")
    return True


def create_task_future_naive():
    """Test Case 5: POST /api/tasks with FUTURE naive datetime-local dates."""
    log("Test 5: POST /api/tasks with FUTURE naive datetime-local dates")
    headers = {"Authorization": f"Bearer {jwt_token}"}
    payload = {
        "title": "AutoTest — future naive dates",
        "description": "Testing with future scheduled_start_date and due_date",
        "project_id": project_id,
        "assignee_id": assignee_id,
        "priority": "Medium",
        "status": "Assigned",
        "estimated_duration_minutes": 60,
        "scheduled_start_date": "2026-12-01T10:00",
        "due_date": "2026-12-05T18:00",
        "tags": [],
        "instructions": "",
        "reference_links": [],
        "attachments": []
    }
    resp = requests.post(f"{BASE_URL}/tasks", headers=headers, json=payload)
    if resp.status_code != 200:
        log(f"❌ FAIL: POST /api/tasks returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    data = resp.json()
    task_id = data.get("id")
    task_status = data.get("status")
    if not task_id:
        log("❌ FAIL: No 'id' in response")
        return False
    # Should be auto-promoted to "Scheduled" because start is in the future
    if task_status != "Scheduled":
        log(f"❌ FAIL: Expected status 'Scheduled', got '{task_status}'")
        return False
    created_task_ids.append(task_id)
    log(f"✅ PASS: Task created (id: {task_id}, status: {task_status})")
    return True


def create_task_past_naive():
    """Test Case 6: POST /api/tasks with PAST scheduled_start_date."""
    log("Test 6: POST /api/tasks with PAST scheduled_start_date")
    headers = {"Authorization": f"Bearer {jwt_token}"}
    payload = {
        "title": "AutoTest — past naive date",
        "description": "Testing with past scheduled_start_date",
        "project_id": project_id,
        "assignee_id": assignee_id,
        "priority": "Medium",
        "status": "Assigned",
        "estimated_duration_minutes": 60,
        "scheduled_start_date": "2020-01-01T09:00",
        "due_date": "2020-01-05T18:00",
        "tags": [],
        "instructions": "",
        "reference_links": [],
        "attachments": []
    }
    resp = requests.post(f"{BASE_URL}/tasks", headers=headers, json=payload)
    if resp.status_code != 200:
        log(f"❌ FAIL: POST /api/tasks returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    data = resp.json()
    task_id = data.get("id")
    task_status = data.get("status")
    if not task_id:
        log("❌ FAIL: No 'id' in response")
        return False
    # Should remain "Assigned" because start is in the past
    if task_status != "Assigned":
        log(f"❌ FAIL: Expected status 'Assigned', got '{task_status}'")
        return False
    created_task_ids.append(task_id)
    log(f"✅ PASS: Task created (id: {task_id}, status: {task_status})")
    return True


def create_task_timezone_aware():
    """Test Case 7: POST /api/tasks with timezone-aware ISO date."""
    log("Test 7: POST /api/tasks with timezone-aware ISO date")
    headers = {"Authorization": f"Bearer {jwt_token}"}
    payload = {
        "title": "AutoTest — timezone-aware date",
        "description": "Testing with timezone-aware ISO date",
        "project_id": project_id,
        "assignee_id": assignee_id,
        "priority": "Medium",
        "status": "Assigned",
        "estimated_duration_minutes": 60,
        "scheduled_start_date": "2026-12-01T10:00:00Z",
        "due_date": "2026-12-05T18:00:00Z",
        "tags": [],
        "instructions": "",
        "reference_links": [],
        "attachments": []
    }
    resp = requests.post(f"{BASE_URL}/tasks", headers=headers, json=payload)
    if resp.status_code != 200:
        log(f"❌ FAIL: POST /api/tasks returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    data = resp.json()
    task_id = data.get("id")
    if not task_id:
        log("❌ FAIL: No 'id' in response")
        return False
    created_task_ids.append(task_id)
    log(f"✅ PASS: Task created (id: {task_id})")
    return True


def list_tasks():
    """Test Case 8: GET /api/tasks?scope=all and verify newly-created tasks appear."""
    log("Test 8: GET /api/tasks?scope=all")
    headers = {"Authorization": f"Bearer {jwt_token}"}
    resp = requests.get(f"{BASE_URL}/tasks?scope=all", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: GET /api/tasks returned {resp.status_code}")
        return False
    tasks = resp.json()
    task_ids_in_list = [t["id"] for t in tasks]
    missing = [tid for tid in created_task_ids if tid not in task_ids_in_list]
    if missing:
        log(f"❌ FAIL: Created task IDs not found in list: {missing}")
        return False
    log(f"✅ PASS: All {len(created_task_ids)} created tasks appear in list")
    return True


def test_analytics_dashboard():
    """Test Case 9: GET /api/analytics/dashboard (regression test)."""
    log("Test 9: GET /api/analytics/dashboard (regression)")
    headers = {"Authorization": f"Bearer {jwt_token}"}
    resp = requests.get(f"{BASE_URL}/analytics/dashboard", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: GET /api/analytics/dashboard returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    data = resp.json()
    log(f"✅ PASS: Analytics dashboard returned 200 (total tasks: {data.get('total', 0)})")
    return True


def test_timer_start_pause():
    """Test Case 10: Start and pause timer on an assigned task (regression test)."""
    log("Test 10: Start and pause timer on assigned task (regression)")
    # Find an assigned task from our created tasks
    headers = {"Authorization": f"Bearer {jwt_token}"}
    assigned_task_id = None
    assignee_email = None
    
    for tid in created_task_ids:
        resp = requests.get(f"{BASE_URL}/tasks/{tid}", headers=headers)
        if resp.status_code == 200:
            task = resp.json()
            if task.get("status") == "Assigned" and task.get("assignee"):
                assigned_task_id = tid
                # Get assignee email from users list
                resp_users = requests.get(f"{BASE_URL}/users", headers=headers)
                if resp_users.status_code == 200:
                    users = resp_users.json()
                    for u in users:
                        if u["id"] == task["assignee"]["id"]:
                            assignee_email = u.get("email")
                            break
                break
    
    if not assigned_task_id or not assignee_email:
        log("⚠️  SKIP: No assigned task found for timer test")
        return True
    
    # Login as assignee (use default password for team members)
    log(f"  Logging in as assignee ({assignee_email})")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": assignee_email,
        "password": "Password@123"
    })
    if resp.status_code != 200:
        log(f"⚠️  SKIP: Could not login as assignee")
        return True
    
    assignee_token = resp.json().get("token")
    assignee_headers = {"Authorization": f"Bearer {assignee_token}"}
    
    # Start timer
    log(f"  Starting timer on task {assigned_task_id}")
    resp = requests.post(f"{BASE_URL}/tasks/{assigned_task_id}/start", headers=assignee_headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: POST /api/tasks/{assigned_task_id}/start returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    
    # Pause timer
    log(f"  Pausing timer on task {assigned_task_id}")
    resp = requests.post(f"{BASE_URL}/tasks/{assigned_task_id}/pause", headers=assignee_headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: POST /api/tasks/{assigned_task_id}/pause returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    
    log(f"✅ PASS: Timer start and pause both returned 200")
    return True


def main():
    log("=" * 70)
    log("Backend Test: 'Failed to create task' Bug Fix Verification")
    log("=" * 70)
    
    tests = [
        ("Login", login),
        ("Get Projects", get_project),
        ("Get Users", get_user),
        ("Create Task (basic, no dates)", create_task_basic),
        ("Create Task (future naive dates)", create_task_future_naive),
        ("Create Task (past naive date)", create_task_past_naive),
        ("Create Task (timezone-aware date)", create_task_timezone_aware),
        ("List Tasks", list_tasks),
        ("Analytics Dashboard", test_analytics_dashboard),
        ("Timer Start/Pause", test_timer_start_pause),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            log(f"❌ EXCEPTION in {name}: {e}")
            failed += 1
    
    log("=" * 70)
    log(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    log("=" * 70)
    
    if failed > 0:
        sys.exit(1)
    else:
        log("🎉 All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()

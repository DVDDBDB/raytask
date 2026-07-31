#!/usr/bin/env python3
"""
Backend test for Cost Analytics redesign.
Tests GET /api/analytics/costs with various range parameters, filters,
and GET /api/exports/costs.xlsx.
"""
import requests
import sys
from datetime import datetime

# Backend URL from frontend/.env
BASE_URL = "https://ray-task-hub.preview.emergentagent.com/api"

# Test credentials
SUPER_ADMIN_EMAIL = "superadmin@raybotix.com"
SUPER_ADMIN_PASSWORD = "Admin@123"
TEAM_MEMBER_EMAIL = "priya@raybotix.com"
TEAM_MEMBER_PASSWORD = "Password@123"

# Global variables
admin_token = None
team_token = None
test_project_id = None
test_user_id = None


def log(msg):
    print(f"[TEST] {msg}")


def test_1_login_admin():
    """Test Case 1: Login as super admin."""
    global admin_token
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
    admin_token = data.get("token")
    if not admin_token:
        log("❌ FAIL: No token in response")
        return False
    log(f"✅ PASS: Login successful")
    return True


def test_2_range_today():
    """Test Case 2: range=today → 200; range_label == "Today"; start & end present; total is a number ≥ 0."""
    log("Test 2: GET /api/analytics/costs?range=today")
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = requests.get(f"{BASE_URL}/analytics/costs?range=today", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: Returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    data = resp.json()
    
    # Check range_label
    if data.get("range_label") != "Today":
        log(f"❌ FAIL: Expected range_label='Today', got '{data.get('range_label')}'")
        return False
    
    # Check start and end are present
    if not data.get("start") or not data.get("end"):
        log(f"❌ FAIL: Missing start or end fields")
        return False
    
    # Check total is a number >= 0
    total = data.get("total")
    if not isinstance(total, (int, float)) or total < 0:
        log(f"❌ FAIL: total should be a number >= 0, got {total}")
        return False
    
    log(f"✅ PASS: range_label='Today', start={data['start'][:10]}, end={data['end'][:10]}, total={total}")
    return True


def test_3_range_week():
    """Test Case 3: range=week → 200; range_label == "This week"."""
    log("Test 3: GET /api/analytics/costs?range=week")
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = requests.get(f"{BASE_URL}/analytics/costs?range=week", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: Returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    data = resp.json()
    
    if data.get("range_label") != "This week":
        log(f"❌ FAIL: Expected range_label='This week', got '{data.get('range_label')}'")
        return False
    
    log(f"✅ PASS: range_label='This week', start={data.get('start', '')[:10]}")
    return True


def test_4_range_month():
    """Test Case 4: range=month → 200; range_label contains current month name; start ends with "-01T00:00:00+00:00"."""
    log("Test 4: GET /api/analytics/costs?range=month")
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = requests.get(f"{BASE_URL}/analytics/costs?range=month", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: Returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    data = resp.json()
    
    # Check range_label contains a month name (e.g., "July 2026")
    range_label = data.get("range_label", "")
    current_month = datetime.now().strftime("%B")  # e.g., "July"
    if current_month not in range_label:
        log(f"❌ FAIL: Expected range_label to contain '{current_month}', got '{range_label}'")
        return False
    
    # Check start ends with "-01T00:00:00+00:00"
    start = data.get("start", "")
    if not start.endswith("-01T00:00:00+00:00"):
        log(f"❌ FAIL: Expected start to end with '-01T00:00:00+00:00', got '{start}'")
        return False
    
    log(f"✅ PASS: range_label='{range_label}', start={start[:10]}")
    return True


def test_5_range_quarter():
    """Test Case 5: range=quarter → 200; range_label starts with "Q"."""
    log("Test 5: GET /api/analytics/costs?range=quarter")
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = requests.get(f"{BASE_URL}/analytics/costs?range=quarter", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: Returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    data = resp.json()
    
    range_label = data.get("range_label", "")
    if not range_label.startswith("Q"):
        log(f"❌ FAIL: Expected range_label to start with 'Q', got '{range_label}'")
        return False
    
    log(f"✅ PASS: range_label='{range_label}'")
    return True


def test_6_range_year():
    """Test Case 6: range=year → 200; range_label like "Year 2026"; start ends with "-01-01T00:00:00+00:00"."""
    log("Test 6: GET /api/analytics/costs?range=year")
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = requests.get(f"{BASE_URL}/analytics/costs?range=year", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: Returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    data = resp.json()
    
    range_label = data.get("range_label", "")
    current_year = str(datetime.now().year)
    if not range_label.startswith("Year") or current_year not in range_label:
        log(f"❌ FAIL: Expected range_label like 'Year {current_year}', got '{range_label}'")
        return False
    
    start = data.get("start", "")
    if not start.endswith("-01-01T00:00:00+00:00"):
        log(f"❌ FAIL: Expected start to end with '-01-01T00:00:00+00:00', got '{start}'")
        return False
    
    log(f"✅ PASS: range_label='{range_label}', start={start[:10]}")
    return True


def test_7_range_custom():
    """Test Case 7: range=custom&start=2026-07-01&end=2026-07-31 → 200; range_label "2026-07-01 → 2026-07-31"; end ISO ends with "T23:59:59+00:00"."""
    log("Test 7: GET /api/analytics/costs?range=custom&start=2026-07-01&end=2026-07-31")
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = requests.get(f"{BASE_URL}/analytics/costs?range=custom&start=2026-07-01&end=2026-07-31", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: Returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    data = resp.json()
    
    range_label = data.get("range_label", "")
    if range_label != "2026-07-01 → 2026-07-31":
        log(f"❌ FAIL: Expected range_label='2026-07-01 → 2026-07-31', got '{range_label}'")
        return False
    
    end = data.get("end", "")
    if not end.endswith("T23:59:59+00:00"):
        log(f"❌ FAIL: Expected end to end with 'T23:59:59+00:00', got '{end}'")
        return False
    
    log(f"✅ PASS: range_label='{range_label}', end={end}")
    return True


def test_8_project_filter():
    """Test Case 8: Pick any project from GET /api/projects → call /analytics/costs?range=month&project_id=<id>. Verify filtering."""
    global test_project_id
    log("Test 8: GET /api/analytics/costs with project_id filter")
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Get projects
    resp = requests.get(f"{BASE_URL}/projects", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: GET /api/projects returned {resp.status_code}")
        return False
    projects = resp.json()
    if not projects:
        log("⚠️  SKIP: No projects found")
        return True
    
    test_project_id = projects[0]["id"]
    project_name = projects[0].get("name", "Unknown")
    
    # Get unfiltered total
    resp_unfiltered = requests.get(f"{BASE_URL}/analytics/costs?range=month", headers=headers)
    if resp_unfiltered.status_code != 200:
        log(f"❌ FAIL: Unfiltered request returned {resp_unfiltered.status_code}")
        return False
    unfiltered_total = resp_unfiltered.json().get("total", 0)
    
    # Get filtered by project
    resp = requests.get(f"{BASE_URL}/analytics/costs?range=month&project_id={test_project_id}", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: Returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    data = resp.json()
    
    # Verify all tasks belong to this project
    tasks = data.get("tasks", [])
    for task in tasks:
        if task.get("project_id") != test_project_id:
            log(f"❌ FAIL: Task {task.get('task_id')} has project_id={task.get('project_id')}, expected {test_project_id}")
            return False
    
    # Verify projects list contains only this project (if any)
    projects_list = data.get("projects", [])
    for proj in projects_list:
        if proj.get("project_id") != test_project_id:
            log(f"❌ FAIL: Projects list contains project_id={proj.get('project_id')}, expected only {test_project_id}")
            return False
    
    # Verify total <= unfiltered total
    filtered_total = data.get("total", 0)
    if filtered_total > unfiltered_total:
        log(f"❌ FAIL: Filtered total ({filtered_total}) > unfiltered total ({unfiltered_total})")
        return False
    
    log(f"✅ PASS: Project filter works (project='{project_name}', filtered_total={filtered_total} <= unfiltered={unfiltered_total})")
    return True


def test_9_user_filter():
    """Test Case 9: Pick any user from GET /api/users → call /analytics/costs?range=month&user_id=<id>. Verify filtering."""
    global test_user_id
    log("Test 9: GET /api/analytics/costs with user_id filter")
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Get users
    resp = requests.get(f"{BASE_URL}/users", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: GET /api/users returned {resp.status_code}")
        return False
    users = resp.json()
    active_users = [u for u in users if u.get("status") == "active"]
    if not active_users:
        log("⚠️  SKIP: No active users found")
        return True
    
    test_user_id = active_users[0]["id"]
    user_name = active_users[0].get("first_name", "Unknown")
    
    # Get unfiltered total
    resp_unfiltered = requests.get(f"{BASE_URL}/analytics/costs?range=month", headers=headers)
    if resp_unfiltered.status_code != 200:
        log(f"❌ FAIL: Unfiltered request returned {resp_unfiltered.status_code}")
        return False
    unfiltered_total = resp_unfiltered.json().get("total", 0)
    
    # Get filtered by user
    resp = requests.get(f"{BASE_URL}/analytics/costs?range=month&user_id={test_user_id}", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: Returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    data = resp.json()
    
    # Verify employees list contains at most this user
    employees = data.get("employees", [])
    for emp in employees:
        if emp.get("user_id") != test_user_id:
            log(f"❌ FAIL: Employees list contains user_id={emp.get('user_id')}, expected only {test_user_id}")
            return False
    
    # Verify total <= unfiltered total
    filtered_total = data.get("total", 0)
    if filtered_total > unfiltered_total:
        log(f"❌ FAIL: Filtered total ({filtered_total}) > unfiltered total ({unfiltered_total})")
        return False
    
    log(f"✅ PASS: User filter works (user='{user_name}', filtered_total={filtered_total} <= unfiltered={unfiltered_total})")
    return True


def test_10_response_shape():
    """Test Case 10: Verify response shape for /analytics/costs?range=month."""
    log("Test 10: Verify response shape")
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = requests.get(f"{BASE_URL}/analytics/costs?range=month", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: Returned {resp.status_code}")
        return False
    data = resp.json()
    
    # Check employees fields
    employees = data.get("employees", [])
    if employees:
        emp = employees[0]
        required_emp_fields = ["user_id", "first_name", "designation", "hourly", "cost", "seconds", "hours", "monthly_cost", "monthly_hours"]
        for field in required_emp_fields:
            if field not in emp:
                log(f"❌ FAIL: Employee missing field '{field}'")
                return False
    
    # Check tasks fields
    tasks = data.get("tasks", [])
    if tasks:
        task = tasks[0]
        required_task_fields = ["task_id", "title", "project_name", "assignee_name", "cost", "hours"]
        for field in required_task_fields:
            if field not in task:
                log(f"❌ FAIL: Task missing field '{field}'")
                return False
    
    # Check projects fields
    projects = data.get("projects", [])
    if projects:
        proj = projects[0]
        required_proj_fields = ["project_id", "name", "company_name", "cost", "seconds", "hours"]
        for field in required_proj_fields:
            if field not in proj:
                log(f"❌ FAIL: Project missing field '{field}'")
                return False
    
    log(f"✅ PASS: Response shape verified (employees: {len(employees)}, tasks: {len(tasks)}, projects: {len(projects)})")
    return True


def test_11_rbac():
    """Test Case 11: RBAC: login as priya@raybotix.com → GET /api/analytics/costs must return 403."""
    global team_token
    log("Test 11: RBAC test with team member")
    
    # Login as team member
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": TEAM_MEMBER_EMAIL,
        "password": TEAM_MEMBER_PASSWORD
    })
    if resp.status_code != 200:
        log(f"❌ FAIL: Team member login returned {resp.status_code}")
        return False
    team_token = resp.json().get("token")
    
    # Try to access costs endpoint
    headers = {"Authorization": f"Bearer {team_token}"}
    resp = requests.get(f"{BASE_URL}/analytics/costs", headers=headers)
    if resp.status_code != 403:
        log(f"❌ FAIL: Expected 403, got {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    
    log(f"✅ PASS: Team member correctly denied access (403)")
    return True


def test_12_excel_export():
    """Test Case 12: GET /api/exports/costs.xlsx?range=month → 200; Content-Type must be xlsx; body length > 100 bytes."""
    log("Test 12: GET /api/exports/costs.xlsx")
    headers = {"Authorization": f"Bearer {admin_token}"}
    resp = requests.get(f"{BASE_URL}/exports/costs.xlsx?range=month", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: Returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    
    # Check Content-Type
    content_type = resp.headers.get("Content-Type", "")
    expected_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if content_type != expected_type:
        log(f"❌ FAIL: Expected Content-Type='{expected_type}', got '{content_type}'")
        return False
    
    # Check body length
    body_length = len(resp.content)
    if body_length <= 100:
        log(f"❌ FAIL: Body length {body_length} <= 100 bytes")
        return False
    
    log(f"✅ PASS: Excel export works (Content-Type correct, body length={body_length} bytes)")
    return True


def test_13_regression():
    """Test Case 13: Regression: GET /api/analytics/dashboard → 200. GET /api/analytics/productivity → 200. GET /api/tasks?scope=all → 200."""
    log("Test 13: Regression tests")
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Test dashboard
    resp = requests.get(f"{BASE_URL}/analytics/dashboard", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: GET /api/analytics/dashboard returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    
    # Test productivity
    resp = requests.get(f"{BASE_URL}/analytics/productivity", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: GET /api/analytics/productivity returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    
    # Test tasks
    resp = requests.get(f"{BASE_URL}/tasks?scope=all", headers=headers)
    if resp.status_code != 200:
        log(f"❌ FAIL: GET /api/tasks?scope=all returned {resp.status_code}")
        log(f"Response: {resp.text}")
        return False
    
    log(f"✅ PASS: All regression tests passed (dashboard, productivity, tasks)")
    return True


def main():
    log("=" * 80)
    log("Backend Test: Cost Analytics Redesign Verification")
    log("=" * 80)
    
    tests = [
        ("Login as super admin", test_1_login_admin),
        ("range=today", test_2_range_today),
        ("range=week", test_3_range_week),
        ("range=month", test_4_range_month),
        ("range=quarter", test_5_range_quarter),
        ("range=year", test_6_range_year),
        ("range=custom with dates", test_7_range_custom),
        ("project_id filter", test_8_project_filter),
        ("user_id filter", test_9_user_filter),
        ("Response shape verification", test_10_response_shape),
        ("RBAC (team member 403)", test_11_rbac),
        ("Excel export", test_12_excel_export),
        ("Regression tests", test_13_regression),
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
            import traceback
            traceback.print_exc()
            failed += 1
    
    log("=" * 80)
    log(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    log("=" * 80)
    
    if failed > 0:
        sys.exit(1)
    else:
        log("🎉 All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()

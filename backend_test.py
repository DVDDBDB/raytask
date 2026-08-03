"""
Backend test for Phase 1: Timer auto-stop at 18:00 IST + /tasks/resumable endpoint
"""
import requests
import os
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import uuid

# Read environment variables
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "raybotix_digital")
BASE_URL = "https://ray-task-hub.preview.emergentagent.com/api"

# Test credentials
SUPER_ADMIN_EMAIL = "superadmin@raybotix.com"
SUPER_ADMIN_PASSWORD = "Admin@123"
TEAM_MEMBER_EMAIL = "priya@raybotix.com"
TEAM_MEMBER_PASSWORD = "Password@123"

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

# Global variables
super_admin_token = None
super_admin_id = None
team_member_token = None
team_member_id = None
test_task_id = None
test_project_id = None


def login(email, password):
    """Login and return token and user_id"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": password
    })
    if response.status_code == 200:
        data = response.json()
        return data.get("token"), data.get("user", {}).get("id")
    else:
        print(f"❌ Login failed for {email}: {response.status_code} {response.text}")
        return None, None


async def setup_db():
    """Setup database connection and get user IDs"""
    global super_admin_id, team_member_id, test_project_id
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Get super admin ID
    super_admin = await db.users.find_one({"email": SUPER_ADMIN_EMAIL}, {"_id": 0, "id": 1})
    if super_admin:
        super_admin_id = super_admin["id"]
    
    # Get team member ID
    team_member = await db.users.find_one({"email": TEAM_MEMBER_EMAIL}, {"_id": 0, "id": 1})
    if team_member:
        team_member_id = team_member["id"]
    
    # Get a project ID for creating tasks
    project = await db.projects.find_one({}, {"_id": 0, "id": 1})
    if project:
        test_project_id = project["id"]
    
    return db, client


async def cleanup_auto_paused_sessions(db, user_id):
    """Remove all auto-paused sessions for a user"""
    result = await db.timer_sessions.delete_many({
        "user_id": user_id,
        "auto_paused": True
    })
    print(f"🧹 Cleaned up {result.deleted_count} auto-paused sessions for user {user_id}")


async def cleanup_all_open_sessions(db, user_id):
    """Close all open sessions for a user"""
    result = await db.timer_sessions.update_many(
        {"user_id": user_id, "ended_at": None},
        {"$set": {"ended_at": datetime.now(timezone.utc).isoformat(), "duration_seconds": 0}}
    )
    print(f"🧹 Closed {result.modified_count} open sessions for user {user_id}")


async def inject_yesterday_session(db, user_id, task_id):
    """Inject a synthetic yesterday auto-paused session"""
    now_ist = datetime.now(timezone.utc).astimezone(IST)
    yday_18_ist = datetime(now_ist.year, now_ist.month, now_ist.day, 18, 0, tzinfo=IST) - timedelta(days=1)
    yday_09_ist = yday_18_ist.replace(hour=9)
    ended_utc = yday_18_ist.astimezone(timezone.utc).isoformat()
    started_utc = yday_09_ist.astimezone(timezone.utc).isoformat()
    
    session_id = uuid.uuid4().hex
    session_doc = {
        "id": session_id,
        "task_id": task_id,
        "user_id": user_id,
        "user_first_name": "Test",
        "user_designation": "Developer",
        "started_at": started_utc,
        "ended_at": ended_utc,
        "duration_seconds": 32400,  # 9 hours
        "auto_paused": True,
        "auto_paused_at": ended_utc,
        "paused": False,
    }
    await db.timer_sessions.insert_one(session_doc)
    
    # Update task to have auto_paused_at and status="Paused"
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {
            "auto_paused_at": ended_utc,
            "status": "Paused"
        }}
    )
    
    print(f"✅ Injected yesterday auto-paused session for task {task_id}")
    return session_id


async def inject_two_days_ago_session(db, user_id, task_id):
    """Inject a synthetic two-days-ago auto-paused session"""
    now_ist = datetime.now(timezone.utc).astimezone(IST)
    two_days_ago_18_ist = datetime(now_ist.year, now_ist.month, now_ist.day, 18, 0, tzinfo=IST) - timedelta(days=2)
    two_days_ago_09_ist = two_days_ago_18_ist.replace(hour=9)
    ended_utc = two_days_ago_18_ist.astimezone(timezone.utc).isoformat()
    started_utc = two_days_ago_09_ist.astimezone(timezone.utc).isoformat()
    
    session_id = uuid.uuid4().hex
    session_doc = {
        "id": session_id,
        "task_id": task_id,
        "user_id": user_id,
        "user_first_name": "Test",
        "user_designation": "Developer",
        "started_at": started_utc,
        "ended_at": ended_utc,
        "duration_seconds": 32400,
        "auto_paused": True,
        "auto_paused_at": ended_utc,
        "paused": False,
    }
    await db.timer_sessions.insert_one(session_doc)
    print(f"✅ Injected two-days-ago auto-paused session for task {task_id}")
    return session_id


async def inject_today_open_session(db, user_id, task_id):
    """Inject a fresh OPEN session for today 09:00 IST"""
    now_ist = datetime.now(timezone.utc).astimezone(IST)
    today_09_ist = datetime(now_ist.year, now_ist.month, now_ist.day, 9, 0, tzinfo=IST)
    started_utc = today_09_ist.astimezone(timezone.utc).isoformat()
    
    session_id = uuid.uuid4().hex
    session_doc = {
        "id": session_id,
        "task_id": task_id,
        "user_id": user_id,
        "user_first_name": "Test",
        "user_designation": "Developer",
        "started_at": started_utc,
        "ended_at": None,
        "duration_seconds": 0,
        "auto_paused": False,
        "paused": False,
    }
    await db.timer_sessions.insert_one(session_doc)
    
    # Update task to In Progress
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {"status": "In Progress"}}
    )
    
    print(f"✅ Injected today open session for task {task_id}")
    return session_id


def create_task(token, title, assignee_id):
    """Create a task and return task_id"""
    response = requests.post(
        f"{BASE_URL}/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": title,
            "description": "Test task for auto-pause",
            "project_id": test_project_id,
            "assignee_id": assignee_id,
            "priority": "Medium",
            "status": "Assigned",
            "estimated_minutes": 60
        }
    )
    if response.status_code == 200:
        task = response.json()
        print(f"✅ Created task: {task['id']} - {title}")
        return task["id"]
    else:
        print(f"❌ Failed to create task: {response.status_code} {response.text}")
        return None


def test_resumable_endpoint(token, test_name, expected_status=200):
    """Test GET /api/tasks/resumable"""
    response = requests.get(
        f"{BASE_URL}/tasks/resumable",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"Status: {response.status_code}")
    if response.status_code == expected_status:
        if response.status_code == 200:
            data = response.json()
            print(f"Response: {len(data)} tasks")
            for task in data:
                print(f"  - Task ID: {task.get('id')}")
                print(f"    Title: {task.get('title')}")
                print(f"    Project: {task.get('project_name')}")
                print(f"    Priority: {task.get('priority')}")
                print(f"    Status: {task.get('status')}")
                print(f"    Auto-paused at: {task.get('auto_paused_at')}")
                print(f"    Yesterday seconds: {task.get('yesterday_seconds')}")
            return True, data
        else:
            print(f"Response: {response.text}")
            return True, None
    else:
        print(f"❌ Expected {expected_status}, got {response.status_code}")
        print(f"Response: {response.text}")
        return False, None


def test_resume_task(token, task_id):
    """Test POST /api/tasks/{id}/resume"""
    response = requests.post(
        f"{BASE_URL}/tasks/{task_id}/resume",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"\nResuming task {task_id}: {response.status_code}")
    if response.status_code == 200:
        print("✅ Task resumed successfully")
        return True
    else:
        print(f"❌ Failed to resume: {response.text}")
        return False


def test_pause_task(token, task_id):
    """Test POST /api/tasks/{id}/pause"""
    response = requests.post(
        f"{BASE_URL}/tasks/{task_id}/pause",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"\nPausing task {task_id}: {response.status_code}")
    if response.status_code == 200:
        print("✅ Task paused successfully")
        return True
    else:
        print(f"❌ Failed to pause: {response.text}")
        return False


def test_complete_task(token, task_id):
    """Test POST /api/tasks/{id}/complete"""
    response = requests.post(
        f"{BASE_URL}/tasks/{task_id}/complete",
        headers={"Authorization": f"Bearer {token}"}
    )
    print(f"\nCompleting task {task_id}: {response.status_code}")
    if response.status_code == 200:
        print("✅ Task completed successfully")
        return True
    else:
        print(f"❌ Failed to complete: {response.text}")
        return False


def get_task(token, task_id):
    """Get task details"""
    response = requests.get(
        f"{BASE_URL}/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to get task: {response.status_code} {response.text}")
        return None


def test_regression_endpoints(token):
    """Test regression endpoints"""
    print(f"\n{'='*80}")
    print("REGRESSION TESTS")
    
    endpoints = [
        "/analytics/dashboard",
        "/analytics/costs?range=month",
        "/tasks?scope=all"
    ]
    
    all_passed = True
    for endpoint in endpoints:
        response = requests.get(
            f"{BASE_URL}{endpoint}",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code == 200:
            print(f"✅ GET {endpoint} - 200")
        else:
            print(f"❌ GET {endpoint} - {response.status_code}")
            all_passed = False
    
    return all_passed


async def test_autostop_tick(db):
    """Test autostop._tick() function directly"""
    print(f"\n{'='*80}")
    print("TEST: Autostop unit test - _tick() function")
    
    # Set environment variables before importing autostop
    os.environ['MONGO_URL'] = MONGO_URL
    os.environ['DB_NAME'] = DB_NAME
    
    # Import autostop module
    import sys
    sys.path.insert(0, '/app/backend')
    import autostop
    
    # Check current IST time
    now_ist = datetime.now(timezone.utc).astimezone(IST)
    print(f"Current IST time: {now_ist.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Create a test task for this
    task_id = uuid.uuid4().hex
    task_doc = {
        "id": task_id,
        "title": "Autostop tick test task",
        "description": "Test",
        "project_id": test_project_id,
        "assignee_id": super_admin_id,
        "creator_id": super_admin_id,
        "priority": "Medium",
        "status": "In Progress",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "workflow": [],
        "reassignment_history": [],
    }
    await db.tasks.insert_one(task_doc)
    
    # Inject today open session starting at 09:00 IST
    session_id = await inject_today_open_session(db, super_admin_id, task_id)
    
    # Call _tick()
    print("Calling autostop._tick()...")
    paused_count = await autostop._tick()
    print(f"Auto-paused {paused_count} sessions")
    
    # Check if session was updated
    session = await db.timer_sessions.find_one({"id": session_id}, {"_id": 0})
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    
    result = False
    if now_ist.hour >= 18:
        # After 18:00 IST, session should be auto-paused
        if session.get("ended_at") and session.get("auto_paused"):
            print("✅ Session was auto-paused (after 18:00 IST)")
            print(f"   ended_at: {session.get('ended_at')}")
            print(f"   duration_seconds: {session.get('duration_seconds')}")
            print(f"   auto_paused: {session.get('auto_paused')}")
            print(f"   Task status: {task.get('status')}")
            print(f"   Task auto_paused_at: {task.get('auto_paused_at')}")
            result = True
        else:
            print("❌ Session was NOT auto-paused (expected after 18:00 IST)")
            result = False
    else:
        # Before 18:00 IST, session should NOT be auto-paused
        if not session.get("ended_at"):
            print("✅ Session was NOT auto-paused (before 18:00 IST - correct)")
            print(f"   Current IST hour: {now_ist.hour}")
            result = True
        else:
            print("❌ Session was auto-paused (unexpected before 18:00 IST)")
            result = False
    
    # Clean up: close the open session if it's still open
    if not session.get("ended_at"):
        await db.timer_sessions.update_one(
            {"id": session_id},
            {"$set": {"ended_at": datetime.now(timezone.utc).isoformat(), "duration_seconds": 100}}
        )
        print("🧹 Cleaned up open session from autostop test")
    
    return result


async def main():
    """Main test runner"""
    global super_admin_token, team_member_token, test_task_id
    
    print("="*80)
    print("PHASE 1 BACKEND TESTS: Timer auto-stop at 18:00 IST + /tasks/resumable")
    print("="*80)
    
    # Setup database
    db, client = await setup_db()
    
    # Login
    print("\n1. Logging in...")
    super_admin_token, _ = login(SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD)
    team_member_token, _ = login(TEAM_MEMBER_EMAIL, TEAM_MEMBER_PASSWORD)
    
    if not super_admin_token:
        print("❌ Failed to login as super admin")
        return
    
    print(f"✅ Logged in as super admin")
    print(f"✅ Super admin ID: {super_admin_id}")
    
    # Test 2: GET /api/tasks/resumable BEFORE injection
    await cleanup_auto_paused_sessions(db, super_admin_id)
    await cleanup_all_open_sessions(db, super_admin_id)
    success, data = test_resumable_endpoint(super_admin_token, "Test 2: GET /resumable BEFORE injection (should be empty)")
    if success and len(data) == 0:
        print("✅ Test 2 PASSED")
    else:
        print("❌ Test 2 FAILED")
    
    # Create a test task
    test_task_id = create_task(super_admin_token, "Auto-pause test task", super_admin_id)
    if not test_task_id:
        print("❌ Failed to create test task")
        return
    
    # Test 3: Inject synthetic yesterday auto-paused session
    print(f"\n{'='*80}")
    print("TEST 3: Inject yesterday auto-paused session")
    session_id = await inject_yesterday_session(db, super_admin_id, test_task_id)
    
    # Test 4: GET /api/tasks/resumable AFTER injection
    success, data = test_resumable_endpoint(super_admin_token, "Test 4: GET /resumable AFTER injection")
    if success and len(data) > 0:
        task = data[0]
        required_keys = ["id", "title", "project_name", "priority", "status", "auto_paused_at", "yesterday_seconds"]
        has_all_keys = all(key in task for key in required_keys)
        if has_all_keys and task.get("yesterday_seconds", 0) > 0:
            print("✅ Test 4 PASSED - Response includes task with all required keys")
        else:
            print("❌ Test 4 FAILED - Missing keys or yesterday_seconds <= 0")
    else:
        print("❌ Test 4 FAILED")
    
    # Test 5: POST /api/tasks/{id}/resume
    print(f"\n{'='*80}")
    print("TEST 5: Resume task")
    if test_resume_task(super_admin_token, test_task_id):
        # Check that task no longer appears in resumable
        success, data = test_resumable_endpoint(super_admin_token, "Test 5b: GET /resumable after resume (should be empty)")
        if success and len(data) == 0:
            print("✅ Test 5 PASSED - Task no longer in resumable list")
            
            # Check that auto_paused_at is removed
            task = get_task(super_admin_token, test_task_id)
            if task and "auto_paused_at" not in task:
                print("✅ Test 5c PASSED - auto_paused_at removed from task")
            else:
                print("❌ Test 5c FAILED - auto_paused_at still present")
        else:
            print("❌ Test 5 FAILED")
    else:
        print("❌ Test 5 FAILED")
    
    # Test 6: POST /api/tasks/{id}/pause
    print(f"\n{'='*80}")
    print("TEST 6: Pause task (auto_paused_at should NOT reappear)")
    if test_pause_task(super_admin_token, test_task_id):
        task = get_task(super_admin_token, test_task_id)
        if task:
            if task.get("status") == "Paused" and "auto_paused_at" not in task:
                print("✅ Test 6 PASSED - Task paused, auto_paused_at NOT present")
            else:
                print(f"❌ Test 6 FAILED - status={task.get('status')}, auto_paused_at present: {'auto_paused_at' in task}")
        else:
            print("❌ Test 6 FAILED - Could not get task")
    else:
        print("❌ Test 6 FAILED")
    
    # Test 7: Inject two-days-ago session
    print(f"\n{'='*80}")
    print("TEST 7: Inject two-days-ago auto-paused session")
    test_task_id_2 = create_task(super_admin_token, "Two days ago test task", super_admin_id)
    if test_task_id_2:
        await inject_two_days_ago_session(db, super_admin_id, test_task_id_2)
        success, data = test_resumable_endpoint(super_admin_token, "Test 7: GET /resumable (should NOT include two-days-ago)")
        # Should not include the two-days-ago task
        task_ids = [t["id"] for t in data]
        if test_task_id_2 not in task_ids:
            print("✅ Test 7 PASSED - Two-days-ago task NOT in resumable list")
        else:
            print("❌ Test 7 FAILED - Two-days-ago task in resumable list")
    else:
        print("❌ Test 7 FAILED - Could not create task")
    
    # Test 8: Complete an auto-paused task
    print(f"\n{'='*80}")
    print("TEST 8: Complete an auto-paused task")
    test_task_id_3 = create_task(super_admin_token, "Complete test task", super_admin_id)
    if test_task_id_3:
        await inject_yesterday_session(db, super_admin_id, test_task_id_3)
        # Resume first
        test_resume_task(super_admin_token, test_task_id_3)
        # Complete
        if test_complete_task(super_admin_token, test_task_id_3):
            success, data = test_resumable_endpoint(super_admin_token, "Test 8: GET /resumable (should NOT include completed)")
            task_ids = [t["id"] for t in data]
            if test_task_id_3 not in task_ids:
                print("✅ Test 8 PASSED - Completed task NOT in resumable list")
            else:
                print("❌ Test 8 FAILED - Completed task in resumable list")
        else:
            print("❌ Test 8 FAILED - Could not complete task")
    else:
        print("❌ Test 8 FAILED - Could not create task")
    
    # Test 9: RBAC - team member
    print(f"\n{'='*80}")
    print("TEST 9: RBAC - Team member (Priya)")
    if team_member_token:
        # Clean up any auto-paused sessions for Priya
        await cleanup_auto_paused_sessions(db, team_member_id)
        success, data = test_resumable_endpoint(team_member_token, "Test 9: GET /resumable as team member")
        if success and len(data) == 0:
            print("✅ Test 9 PASSED - Team member gets empty list (no auto-paused sessions)")
        else:
            print("❌ Test 9 FAILED")
    else:
        print("⚠️  Test 9 SKIPPED - Could not login as team member")
    
    # Test 10: Autostop unit test
    await test_autostop_tick(db)
    
    # Test 11: Regression - existing timer endpoints
    print(f"\n{'='*80}")
    print("TEST 11: Regression - Timer endpoints")
    test_task_id_4 = create_task(super_admin_token, "Regression test task", super_admin_id)
    if test_task_id_4:
        # Test start
        response = requests.post(
            f"{BASE_URL}/tasks/{test_task_id_4}/start",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        if response.status_code == 200:
            print("✅ POST /start - 200")
        else:
            print(f"❌ POST /start - {response.status_code}: {response.text}")
        
        # Test pause
        response = requests.post(
            f"{BASE_URL}/tasks/{test_task_id_4}/pause",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        if response.status_code == 200:
            print("✅ POST /pause - 200")
        else:
            print(f"❌ POST /pause - {response.status_code}: {response.text}")
        
        # Test resume
        response = requests.post(
            f"{BASE_URL}/tasks/{test_task_id_4}/resume",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        if response.status_code == 200:
            print("✅ POST /resume - 200")
        else:
            print(f"❌ POST /resume - {response.status_code}: {response.text}")
        
        # Test complete
        response = requests.post(
            f"{BASE_URL}/tasks/{test_task_id_4}/complete",
            headers={"Authorization": f"Bearer {super_admin_token}"}
        )
        if response.status_code == 200:
            print("✅ POST /complete - 200")
        else:
            print(f"❌ POST /complete - {response.status_code}: {response.text}")
        
        # Test 403 for non-assignee (create a new task for this)
        test_task_id_5 = create_task(super_admin_token, "Non-assignee test task", super_admin_id)
        if team_member_token and test_task_id_5:
            response = requests.post(
                f"{BASE_URL}/tasks/{test_task_id_5}/start",
                headers={"Authorization": f"Bearer {team_member_token}"}
            )
            if response.status_code == 403:
                print("✅ POST /start as non-assignee - 403")
            else:
                print(f"❌ POST /start as non-assignee - {response.status_code} (expected 403)")
    else:
        print("❌ Test 11 FAILED - Could not create task")
    
    # Test 12: Regression - analytics endpoints
    test_regression_endpoints(super_admin_token)
    
    # Cleanup
    print(f"\n{'='*80}")
    print("CLEANUP")
    await cleanup_auto_paused_sessions(db, super_admin_id)
    await cleanup_auto_paused_sessions(db, team_member_id)
    
    client.close()
    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())

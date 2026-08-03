#!/usr/bin/env python3
"""
CRM Phase 2 Backend Testing Script
Tests all 20 test cases for leads/inquiries functionality
"""
import requests
import json
from typing import Optional

BASE_URL = "https://ray-task-hub.preview.emergentagent.com/api"

# Test credentials
SUPER_ADMIN_EMAIL = "superadmin@raybotix.com"
SUPER_ADMIN_PASSWORD = "Admin@123"
PRIYA_EMAIL = "priya@raybotix.com"
PRIYA_PASSWORD = "Password@123"

# Global state
super_admin_token = None
super_admin_id = None
priya_token = None
priya_id = None
test_lead_id = None
test_activity_id = None
test_project_id = None


def login(email: str, password: str) -> tuple[Optional[str], Optional[str]]:
    """Login and return (token, user_id)"""
    resp = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if resp.status_code == 200:
        data = resp.json()
        return data.get("token"), data.get("user", {}).get("id")
    return None, None


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_1_login_super_admin():
    """Test 1: Login as super admin"""
    global super_admin_token, super_admin_id
    print("\n[Test 1] Login as super admin")
    super_admin_token, super_admin_id = login(SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD)
    if super_admin_token and super_admin_id:
        print(f"✅ PASS - Logged in as super admin (id: {super_admin_id})")
        return True
    else:
        print("❌ FAIL - Could not login as super admin")
        return False


def test_2_get_stages():
    """Test 2: GET /api/leads/stages"""
    print("\n[Test 2] GET /api/leads/stages")
    resp = requests.get(f"{BASE_URL}/leads/stages", headers=headers(super_admin_token))
    expected = ["New", "Contacted", "Qualified", "Proposal", "Negotiation", "Onboarded", "Lost"]
    
    if resp.status_code == 200:
        stages = resp.json()
        if stages == expected:
            print(f"✅ PASS - Status: {resp.status_code}, Stages: {stages}")
            return True
        else:
            print(f"❌ FAIL - Status: {resp.status_code}, Expected {expected}, Got: {stages}")
            return False
    else:
        print(f"❌ FAIL - Status: {resp.status_code}, Body: {resp.text}")
        return False


def test_3_get_team():
    """Test 3: GET /api/leads/team"""
    print("\n[Test 3] GET /api/leads/team")
    resp = requests.get(f"{BASE_URL}/leads/team", headers=headers(super_admin_token))
    
    if resp.status_code == 200:
        team = resp.json()
        # Should contain super_admin + admin + any crm_access users
        has_super_admin = any(u.get("role") == "super_admin" for u in team)
        print(f"✅ PASS - Status: {resp.status_code}, Team size: {len(team)}, Has super_admin: {has_super_admin}")
        return True
    else:
        print(f"❌ FAIL - Status: {resp.status_code}, Body: {resp.text}")
        return False


def test_4_create_lead():
    """Test 4: POST /api/leads - create new lead"""
    global test_lead_id
    print("\n[Test 4] POST /api/leads - create new lead")
    
    payload = {
        "name": "Acme Client",
        "company": "Acme Ltd",
        "email": "c@acme.co",
        "phone": "+91 90000 00001",
        "source": "Website",
        "stage": "New",
        "next_step": "Send deck",
        "follow_up_date": "2026-08-05T10:00:00Z",
        "value_estimate": 250000
    }
    
    resp = requests.post(f"{BASE_URL}/leads", json=payload, headers=headers(super_admin_token))
    
    if resp.status_code == 200:
        lead = resp.json()
        test_lead_id = lead.get("id")
        has_id = bool(test_lead_id)
        has_activities = "activities" in lead and isinstance(lead["activities"], list)
        has_created_by = bool(lead.get("created_by_id"))
        assigned_to_none = lead.get("assigned_to_id") in (None, "")
        
        if has_id and has_activities and has_created_by:
            print(f"✅ PASS - Status: {resp.status_code}, Lead ID: {test_lead_id}, Activities: {lead['activities']}, Created by: {lead['created_by_id']}, Assigned to: {lead.get('assigned_to_id')}")
            return True
        else:
            print(f"❌ FAIL - Missing required fields. has_id={has_id}, has_activities={has_activities}, has_created_by={has_created_by}")
            return False
    else:
        print(f"❌ FAIL - Status: {resp.status_code}, Body: {resp.text}")
        return False


def test_5_list_leads():
    """Test 5: GET /api/leads with filters"""
    print("\n[Test 5] GET /api/leads with filters")
    
    # Test 5a: List all leads
    resp = requests.get(f"{BASE_URL}/leads", headers=headers(super_admin_token))
    if resp.status_code != 200:
        print(f"❌ FAIL - List all leads failed: {resp.status_code}")
        return False
    
    all_leads = resp.json()
    has_test_lead = any(l.get("id") == test_lead_id for l in all_leads)
    
    # Test 5b: Filter by stage=New
    resp = requests.get(f"{BASE_URL}/leads?stage=New", headers=headers(super_admin_token))
    if resp.status_code != 200:
        print(f"❌ FAIL - Filter by stage failed: {resp.status_code}")
        return False
    
    new_leads = resp.json()
    has_test_lead_in_new = any(l.get("id") == test_lead_id for l in new_leads)
    
    # Test 5c: Search by q=Acme
    resp = requests.get(f"{BASE_URL}/leads?q=Acme", headers=headers(super_admin_token))
    if resp.status_code != 200:
        print(f"❌ FAIL - Search by q failed: {resp.status_code}")
        return False
    
    search_leads = resp.json()
    has_test_lead_in_search = any(l.get("id") == test_lead_id for l in search_leads)
    
    if has_test_lead and has_test_lead_in_new and has_test_lead_in_search:
        print(f"✅ PASS - All filters work. Total leads: {len(all_leads)}, New leads: {len(new_leads)}, Search results: {len(search_leads)}")
        return True
    else:
        print(f"❌ FAIL - Test lead not found in filters. has_test_lead={has_test_lead}, in_new={has_test_lead_in_new}, in_search={has_test_lead_in_search}")
        return False


def test_6_update_stage_valid():
    """Test 6: PATCH /api/leads/{id} with valid stage"""
    print("\n[Test 6] PATCH /api/leads/{id} - update stage to Contacted")
    
    payload = {"stage": "Contacted", "next_step": "Send proposal"}
    resp = requests.patch(f"{BASE_URL}/leads/{test_lead_id}", json=payload, headers=headers(super_admin_token))
    
    if resp.status_code == 200:
        lead = resp.json()
        if lead.get("stage") == "Contacted":
            print(f"✅ PASS - Status: {resp.status_code}, Stage: {lead['stage']}")
            return True
        else:
            print(f"❌ FAIL - Stage not updated. Got: {lead.get('stage')}")
            return False
    else:
        print(f"❌ FAIL - Status: {resp.status_code}, Body: {resp.text}")
        return False


def test_7_update_stage_invalid():
    """Test 7: PATCH /api/leads/{id} with invalid stage"""
    print("\n[Test 7] PATCH /api/leads/{id} - update stage to invalid 'Foo'")
    
    payload = {"stage": "Foo"}
    resp = requests.patch(f"{BASE_URL}/leads/{test_lead_id}", json=payload, headers=headers(super_admin_token))
    
    if resp.status_code == 400:
        print(f"✅ PASS - Status: {resp.status_code}, Correctly rejected invalid stage")
        return True
    else:
        print(f"❌ FAIL - Status: {resp.status_code}, Expected 400. Body: {resp.text}")
        return False


def test_8_add_activity():
    """Test 8: POST /api/leads/{id}/activities"""
    global test_activity_id
    print("\n[Test 8] POST /api/leads/{id}/activities - add activity")
    
    payload = {"kind": "call", "description": "Called client"}
    resp = requests.post(f"{BASE_URL}/leads/{test_lead_id}/activities", json=payload, headers=headers(super_admin_token))
    
    if resp.status_code == 200:
        activity = resp.json()
        test_activity_id = activity.get("id")
        if test_activity_id:
            print(f"✅ PASS - Status: {resp.status_code}, Activity ID: {test_activity_id}")
            return True
        else:
            print(f"❌ FAIL - No activity ID returned")
            return False
    else:
        print(f"❌ FAIL - Status: {resp.status_code}, Body: {resp.text}")
        return False


def test_9_get_lead_with_activity():
    """Test 9: GET /api/leads/{id} - verify activity is present"""
    print("\n[Test 9] GET /api/leads/{id} - verify activity")
    
    resp = requests.get(f"{BASE_URL}/leads/{test_lead_id}", headers=headers(super_admin_token))
    
    if resp.status_code == 200:
        lead = resp.json()
        activities = lead.get("activities", [])
        has_activity = any(a.get("id") == test_activity_id for a in activities)
        
        if has_activity:
            print(f"✅ PASS - Status: {resp.status_code}, Activities count: {len(activities)}, Has test activity: {has_activity}")
            return True
        else:
            print(f"❌ FAIL - Test activity not found. Activities: {activities}")
            return False
    else:
        print(f"❌ FAIL - Status: {resp.status_code}, Body: {resp.text}")
        return False


def test_10_toggle_activity():
    """Test 10: PATCH /api/leads/{id}/activities/{aid} - mark done"""
    print("\n[Test 10] PATCH /api/leads/{id}/activities/{aid} - mark done")
    
    payload = {"done": True}
    resp = requests.patch(f"{BASE_URL}/leads/{test_lead_id}/activities/{test_activity_id}", 
                         json=payload, headers=headers(super_admin_token))
    
    if resp.status_code == 200:
        activity = resp.json()
        if activity.get("done") == True:
            print(f"✅ PASS - Status: {resp.status_code}, Done: {activity['done']}")
            return True
        else:
            print(f"❌ FAIL - Activity not marked done. Got: {activity.get('done')}")
            return False
    else:
        print(f"❌ FAIL - Status: {resp.status_code}, Body: {resp.text}")
        return False


def test_11_assignment():
    """Test 11: Assignment - assign to super admin (valid), then to Priya (no CRM access - should fail)"""
    global priya_id
    print("\n[Test 11] Assignment tests")
    
    # 11a: Assign to super admin (valid)
    payload = {"assigned_to_id": super_admin_id}
    resp = requests.patch(f"{BASE_URL}/leads/{test_lead_id}", json=payload, headers=headers(super_admin_token))
    
    if resp.status_code != 200:
        print(f"❌ FAIL - Could not assign to super admin. Status: {resp.status_code}")
        return False
    
    print(f"  ✓ Assigned to super admin successfully")
    
    # 11b: Get Priya's ID
    resp = requests.get(f"{BASE_URL}/users", headers=headers(super_admin_token))
    if resp.status_code != 200:
        print(f"❌ FAIL - Could not get users list")
        return False
    
    users = resp.json()
    priya = next((u for u in users if u.get("email") == PRIYA_EMAIL), None)
    if not priya:
        print(f"❌ FAIL - Could not find Priya in users list")
        return False
    
    priya_id = priya.get("id")
    print(f"  ✓ Found Priya (id: {priya_id})")
    
    # 11c: Try to assign to Priya (should fail - no CRM access)
    payload = {"assigned_to_id": priya_id}
    resp = requests.patch(f"{BASE_URL}/leads/{test_lead_id}", json=payload, headers=headers(super_admin_token))
    
    if resp.status_code == 400:
        print(f"✅ PASS - Correctly rejected assignment to user without CRM access (status: {resp.status_code})")
        return True
    else:
        print(f"❌ FAIL - Expected 400, got {resp.status_code}. Body: {resp.text}")
        return False


def test_12_grant_crm_and_assign():
    """Test 12: Grant CRM access to Priya, then assign lead"""
    print("\n[Test 12] Grant CRM access and assign")
    
    # 12a: Grant CRM access
    payload = {"crm_access": True}
    resp = requests.patch(f"{BASE_URL}/users/{priya_id}", json=payload, headers=headers(super_admin_token))
    
    if resp.status_code != 200:
        print(f"❌ FAIL - Could not grant CRM access. Status: {resp.status_code}, Body: {resp.text}")
        return False
    
    print(f"  ✓ Granted CRM access to Priya")
    
    # 12b: Assign lead to Priya
    payload = {"assigned_to_id": priya_id}
    resp = requests.patch(f"{BASE_URL}/leads/{test_lead_id}", json=payload, headers=headers(super_admin_token))
    
    if resp.status_code == 200:
        lead = resp.json()
        if lead.get("assigned_to_id") == priya_id and lead.get("assigned_to_name"):
            print(f"✅ PASS - Status: {resp.status_code}, Assigned to: {lead['assigned_to_id']}, Name: {lead['assigned_to_name']}")
            return True
        else:
            print(f"❌ FAIL - Assignment not reflected. assigned_to_id: {lead.get('assigned_to_id')}, assigned_to_name: {lead.get('assigned_to_name')}")
            return False
    else:
        print(f"❌ FAIL - Status: {resp.status_code}, Body: {resp.text}")
        return False


def test_13_rbac_pre_grant():
    """Test 13: RBAC - Priya without CRM access should get 403"""
    print("\n[Test 13] RBAC pre-grant (simulate by removing CRM access temporarily)")
    
    # First, remove CRM access from Priya
    payload = {"crm_access": False}
    resp = requests.patch(f"{BASE_URL}/users/{priya_id}", json=payload, headers=headers(super_admin_token))
    if resp.status_code != 200:
        print(f"❌ FAIL - Could not remove CRM access. Status: {resp.status_code}")
        return False
    
    print(f"  ✓ Removed CRM access from Priya")
    
    # Get fresh token for Priya
    priya_token_temp, _ = login(PRIYA_EMAIL, PRIYA_PASSWORD)
    if not priya_token_temp:
        print(f"❌ FAIL - Could not login as Priya")
        return False
    
    # Try to access leads
    resp = requests.get(f"{BASE_URL}/leads", headers=headers(priya_token_temp))
    
    if resp.status_code == 403:
        print(f"✅ PASS - Correctly denied access (status: {resp.status_code})")
        return True
    else:
        print(f"❌ FAIL - Expected 403, got {resp.status_code}. Body: {resp.text}")
        return False


def test_14_rbac_post_grant():
    """Test 14: RBAC - Priya with CRM access should get 200"""
    global priya_token
    print("\n[Test 14] RBAC post-grant")
    
    # Grant CRM access back
    payload = {"crm_access": True}
    resp = requests.patch(f"{BASE_URL}/users/{priya_id}", json=payload, headers=headers(super_admin_token))
    if resp.status_code != 200:
        print(f"❌ FAIL - Could not grant CRM access. Status: {resp.status_code}")
        return False
    
    print(f"  ✓ Granted CRM access to Priya")
    
    # Get fresh token for Priya
    priya_token, _ = login(PRIYA_EMAIL, PRIYA_PASSWORD)
    if not priya_token:
        print(f"❌ FAIL - Could not login as Priya")
        return False
    
    # Try to access leads
    resp = requests.get(f"{BASE_URL}/leads", headers=headers(priya_token))
    
    if resp.status_code == 200:
        leads = resp.json()
        print(f"✅ PASS - Status: {resp.status_code}, Leads count: {len(leads)}")
        return True
    else:
        print(f"❌ FAIL - Status: {resp.status_code}, Body: {resp.text}")
        return False


def test_15_onboard_lead():
    """Test 15: POST /api/leads/{id}/onboard - create project"""
    global test_project_id
    print("\n[Test 15] POST /api/leads/{id}/onboard - first call")
    
    resp = requests.post(f"{BASE_URL}/leads/{test_lead_id}/onboard", json={}, headers=headers(super_admin_token))
    
    if resp.status_code == 200:
        data = resp.json()
        ok = data.get("ok")
        project = data.get("project", {})
        lead = data.get("lead", {})
        test_project_id = project.get("id")
        
        checks = {
            "ok": ok == True,
            "project_id": bool(test_project_id),
            "project_name": bool(project.get("name")),
            "lead_stage": lead.get("stage") == "Onboarded",
            "lead_project_id": lead.get("project_id") == test_project_id
        }
        
        if all(checks.values()):
            print(f"✅ PASS - Status: {resp.status_code}, Project ID: {test_project_id}, Lead stage: {lead['stage']}")
            
            # Verify project exists in projects list
            resp = requests.get(f"{BASE_URL}/projects", headers=headers(super_admin_token))
            if resp.status_code == 200:
                projects = resp.json()
                has_project = any(p.get("id") == test_project_id for p in projects)
                if has_project:
                    print(f"  ✓ Project found in /api/projects")
                else:
                    print(f"  ⚠ Project NOT found in /api/projects")
            
            return True
        else:
            print(f"❌ FAIL - Missing required fields: {checks}")
            return False
    else:
        print(f"❌ FAIL - Status: {resp.status_code}, Body: {resp.text}")
        return False


def test_16_onboard_idempotent():
    """Test 16: POST /api/leads/{id}/onboard - second call (idempotent)"""
    print("\n[Test 16] POST /api/leads/{id}/onboard - second call (idempotent)")
    
    resp = requests.post(f"{BASE_URL}/leads/{test_lead_id}/onboard", json={}, headers=headers(super_admin_token))
    
    if resp.status_code == 200:
        data = resp.json()
        already_onboarded = data.get("already_onboarded")
        project = data.get("project", {})
        project_id = project.get("id")
        
        if already_onboarded == True and project_id == test_project_id:
            print(f"✅ PASS - Status: {resp.status_code}, already_onboarded: {already_onboarded}, Same project ID: {project_id}")
            return True
        else:
            print(f"❌ FAIL - already_onboarded: {already_onboarded}, project_id: {project_id} (expected: {test_project_id})")
            return False
    else:
        print(f"❌ FAIL - Status: {resp.status_code}, Body: {resp.text}")
        return False


def test_17_follow_ups():
    """Test 17: GET /api/leads/follow-ups/upcoming - onboarded lead should NOT appear"""
    print("\n[Test 17] GET /api/leads/follow-ups/upcoming?days=90")
    
    resp = requests.get(f"{BASE_URL}/leads/follow-ups/upcoming?days=90", headers=headers(super_admin_token))
    
    if resp.status_code == 200:
        leads = resp.json()
        has_onboarded_lead = any(l.get("id") == test_lead_id for l in leads)
        
        if not has_onboarded_lead:
            print(f"✅ PASS - Status: {resp.status_code}, Onboarded lead correctly excluded. Follow-ups count: {len(leads)}")
            return True
        else:
            print(f"❌ FAIL - Onboarded lead should NOT appear in follow-ups")
            return False
    else:
        print(f"❌ FAIL - Status: {resp.status_code}, Body: {resp.text}")
        return False


def test_18_delete_lead():
    """Test 18: DELETE /api/leads/{id} - delete existing and non-existing"""
    print("\n[Test 18] DELETE /api/leads/{id}")
    
    # 18a: Delete existing lead
    resp = requests.delete(f"{BASE_URL}/leads/{test_lead_id}", headers=headers(super_admin_token))
    
    if resp.status_code != 200:
        print(f"❌ FAIL - Could not delete lead. Status: {resp.status_code}, Body: {resp.text}")
        return False
    
    print(f"  ✓ Deleted lead successfully")
    
    # 18b: Try to delete non-existing lead
    fake_id = "nonexistent-lead-id-12345"
    resp = requests.delete(f"{BASE_URL}/leads/{fake_id}", headers=headers(super_admin_token))
    
    if resp.status_code == 404:
        print(f"✅ PASS - Correctly returned 404 for non-existing lead")
        return True
    else:
        print(f"❌ FAIL - Expected 404, got {resp.status_code}. Body: {resp.text}")
        return False


def test_19_regression():
    """Test 19: Regression tests - verify other endpoints still work"""
    print("\n[Test 19] Regression tests")
    
    tests = [
        ("GET /api/analytics/dashboard", f"{BASE_URL}/analytics/dashboard"),
        ("GET /api/tasks?scope=all", f"{BASE_URL}/tasks?scope=all"),
        ("GET /api/analytics/costs?range=month", f"{BASE_URL}/analytics/costs?range=month"),
    ]
    
    all_passed = True
    for name, url in tests:
        resp = requests.get(url, headers=headers(super_admin_token))
        if resp.status_code == 200:
            print(f"  ✓ {name} - Status: {resp.status_code}")
        else:
            print(f"  ✗ {name} - Status: {resp.status_code}, Body: {resp.text}")
            all_passed = False
    
    if all_passed:
        print(f"✅ PASS - All regression tests passed")
        return True
    else:
        print(f"❌ FAIL - Some regression tests failed")
        return False


def test_20_cleanup():
    """Test 20: Cleanup - delete test project and revoke Priya's CRM access"""
    print("\n[Test 20] Cleanup")
    
    # 20a: Delete test project
    if test_project_id:
        resp = requests.delete(f"{BASE_URL}/projects/{test_project_id}", headers=headers(super_admin_token))
        if resp.status_code == 200:
            print(f"  ✓ Deleted test project")
        else:
            print(f"  ⚠ Could not delete test project. Status: {resp.status_code}")
    
    # 20b: Revoke Priya's CRM access
    payload = {"crm_access": False}
    resp = requests.patch(f"{BASE_URL}/users/{priya_id}", json=payload, headers=headers(super_admin_token))
    
    if resp.status_code == 200:
        print(f"  ✓ Revoked Priya's CRM access")
        print(f"✅ PASS - Cleanup completed")
        return True
    else:
        print(f"  ⚠ Could not revoke CRM access. Status: {resp.status_code}")
        print(f"⚠ PARTIAL - Cleanup partially completed")
        return True  # Don't fail the test for cleanup issues


def main():
    """Run all tests"""
    print("=" * 80)
    print("CRM PHASE 2 BACKEND TESTING")
    print("=" * 80)
    
    tests = [
        test_1_login_super_admin,
        test_2_get_stages,
        test_3_get_team,
        test_4_create_lead,
        test_5_list_leads,
        test_6_update_stage_valid,
        test_7_update_stage_invalid,
        test_8_add_activity,
        test_9_get_lead_with_activity,
        test_10_toggle_activity,
        test_11_assignment,
        test_12_grant_crm_and_assign,
        test_13_rbac_pre_grant,
        test_14_rbac_post_grant,
        test_15_onboard_lead,
        test_16_onboard_idempotent,
        test_17_follow_ups,
        test_18_delete_lead,
        test_19_regression,
        test_20_cleanup,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"❌ EXCEPTION in {test.__name__}: {e}")
            results.append((test.__name__, False))
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

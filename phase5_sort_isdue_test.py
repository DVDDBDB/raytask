#!/usr/bin/env python3
"""
Phase 5 Re-verification: Sort parameter and is_due field ONLY.
Tests the two previously-failed features that have now been restored.
"""
import requests
import json
from datetime import datetime, timezone
import sys

# Configuration
BASE_URL = "https://ray-task-hub.preview.emergentagent.com/api"
SUPER_ADMIN_EMAIL = "superadmin@raybotix.com"
SUPER_ADMIN_PASSWORD = "Admin@123"

# Test state
admin_token = None
test_leads = []

def log(msg, level="INFO"):
    """Log test messages."""
    print(f"[{level}] {msg}")

def login(email, password):
    """Login and return token."""
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token")
            log(f"✅ Login successful: {email}")
            return token
        else:
            log(f"❌ Login failed for {email}: {resp.status_code} {resp.text}", "ERROR")
            return None
    except Exception as e:
        log(f"❌ Login exception for {email}: {e}", "ERROR")
        return None

def test_sort_parameter():
    """
    A) Sort parameter tests
    1. Create three leads: L-Low, L-Urgent, L-Medium
    2. GET /api/leads?sort=priority → verify order is Urgent, Medium, Low
    3. GET /api/leads?sort=follow_up → verify leads with follow_up_date come first
    4. GET /api/leads?sort=updated → verify sorted by updated_at descending
    """
    log("\n" + "="*60)
    log("A) SORT PARAMETER TESTS")
    log("="*60)
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Test 1: Create three leads with different priorities
    log("\n--- Test 1: Create three leads (L-Low, L-Urgent, L-Medium) ---")
    
    leads_to_create = [
        {"name": "L-Low", "stage": "New", "priority": "Low", "company": "Low Priority Corp"},
        {"name": "L-Urgent", "stage": "New", "priority": "Urgent", "company": "Urgent Corp"},
        {"name": "L-Medium", "stage": "New", "priority": "Medium", "company": "Medium Corp"},
    ]
    
    created_leads = {}
    for lead_data in leads_to_create:
        resp = requests.post(f"{BASE_URL}/leads", json=lead_data, headers=headers, timeout=10)
        if resp.status_code == 200:
            lead = resp.json()
            test_leads.append(lead["id"])
            created_leads[lead_data["name"]] = lead
            log(f"✅ Created {lead_data['name']} (id={lead['id'][:8]}, priority={lead.get('priority')})")
        else:
            log(f"❌ FAILED to create {lead_data['name']}: {resp.status_code} {resp.text}", "ERROR")
            return False
    
    # Test 2: GET /api/leads?sort=priority → verify order
    log("\n--- Test 2: GET /api/leads?sort=priority ---")
    resp = requests.get(f"{BASE_URL}/leads?sort=priority", headers=headers, timeout=10)
    if resp.status_code != 200:
        log(f"❌ FAILED: GET /api/leads?sort=priority returned {resp.status_code}: {resp.text}", "ERROR")
        return False
    
    leads = resp.json()
    log(f"✅ GET /api/leads?sort=priority returned {len(leads)} leads")
    
    # Find our three test leads in the response
    our_leads = [l for l in leads if l["id"] in [created_leads["L-Low"]["id"], created_leads["L-Urgent"]["id"], created_leads["L-Medium"]["id"]]]
    if len(our_leads) != 3:
        log(f"❌ FAILED: Expected to find 3 test leads, found {len(our_leads)}", "ERROR")
        return False
    
    # Verify order: Urgent should come before Medium, Medium before Low
    priorities = [l["priority"] for l in our_leads]
    log(f"   Order of our test leads: {priorities}")
    
    urgent_idx = next((i for i, l in enumerate(our_leads) if l["name"] == "L-Urgent"), None)
    medium_idx = next((i for i, l in enumerate(our_leads) if l["name"] == "L-Medium"), None)
    low_idx = next((i for i, l in enumerate(our_leads) if l["name"] == "L-Low"), None)
    
    if urgent_idx is not None and medium_idx is not None and low_idx is not None:
        if urgent_idx < medium_idx < low_idx:
            log(f"✅ PASS: Sort order correct (Urgent at {urgent_idx}, Medium at {medium_idx}, Low at {low_idx})")
        else:
            log(f"❌ FAIL: Sort order incorrect (Urgent at {urgent_idx}, Medium at {medium_idx}, Low at {low_idx})", "ERROR")
            log(f"   Expected: Urgent < Medium < Low", "ERROR")
            return False
    else:
        log(f"❌ FAIL: Could not find all three leads in response", "ERROR")
        return False
    
    # Test 3: GET /api/leads?sort=follow_up
    log("\n--- Test 3: GET /api/leads?sort=follow_up ---")
    
    # First, add follow_up_date to L-Urgent
    resp = requests.patch(
        f"{BASE_URL}/leads/{created_leads['L-Urgent']['id']}", 
        json={"follow_up_date": "2026-08-15T10:00:00Z"},
        headers=headers, 
        timeout=10
    )
    if resp.status_code != 200:
        log(f"❌ FAILED to add follow_up_date to L-Urgent: {resp.status_code}", "ERROR")
        return False
    log(f"✅ Added follow_up_date to L-Urgent")
    
    resp = requests.get(f"{BASE_URL}/leads?sort=follow_up", headers=headers, timeout=10)
    if resp.status_code != 200:
        log(f"❌ FAILED: GET /api/leads?sort=follow_up returned {resp.status_code}: {resp.text}", "ERROR")
        return False
    
    leads = resp.json()
    log(f"✅ GET /api/leads?sort=follow_up returned {len(leads)} leads")
    
    # Verify that leads with follow_up_date come before those without
    # Find L-Urgent (has follow_up_date) and L-Low (no follow_up_date)
    urgent_idx = next((i for i, l in enumerate(leads) if l["id"] == created_leads["L-Urgent"]["id"]), None)
    low_idx = next((i for i, l in enumerate(leads) if l["id"] == created_leads["L-Low"]["id"]), None)
    
    if urgent_idx is not None and low_idx is not None:
        if urgent_idx < low_idx:
            log(f"✅ PASS: L-Urgent (with follow_up) at index {urgent_idx}, L-Low (without) at index {low_idx}")
        else:
            log(f"❌ FAIL: L-Urgent at {urgent_idx}, L-Low at {low_idx} (expected Urgent < Low)", "ERROR")
            return False
    else:
        log(f"❌ FAIL: Could not find leads in response", "ERROR")
        return False
    
    # Test 4: GET /api/leads?sort=updated
    log("\n--- Test 4: GET /api/leads?sort=updated ---")
    
    # Update L-Low to make it the most recently updated
    resp = requests.patch(
        f"{BASE_URL}/leads/{created_leads['L-Low']['id']}", 
        json={"notes": "Updated just now"},
        headers=headers, 
        timeout=10
    )
    if resp.status_code != 200:
        log(f"❌ FAILED to update L-Low: {resp.status_code}", "ERROR")
        return False
    log(f"✅ Updated L-Low (should now be most recent)")
    
    resp = requests.get(f"{BASE_URL}/leads?sort=updated", headers=headers, timeout=10)
    if resp.status_code != 200:
        log(f"❌ FAILED: GET /api/leads?sort=updated returned {resp.status_code}: {resp.text}", "ERROR")
        return False
    
    leads = resp.json()
    log(f"✅ GET /api/leads?sort=updated returned {len(leads)} leads")
    
    # L-Low should be first (most recently updated)
    if len(leads) > 0:
        first_lead = leads[0]
        if first_lead["id"] == created_leads["L-Low"]["id"]:
            log(f"✅ PASS: L-Low is first (most recently updated)")
        else:
            log(f"⚠️  L-Low not first, but this could be due to other recent updates. Checking if sorted descending...")
            # Verify descending order by checking updated_at timestamps
            updated_ats = [l.get("updated_at", "") for l in leads[:5]]
            is_descending = all(updated_ats[i] >= updated_ats[i+1] for i in range(len(updated_ats)-1))
            if is_descending:
                log(f"✅ PASS: Leads are sorted by updated_at descending")
            else:
                log(f"❌ FAIL: Leads not sorted by updated_at descending", "ERROR")
                log(f"   First 5 updated_at values: {updated_ats}", "ERROR")
                return False
    else:
        log(f"❌ FAIL: No leads returned", "ERROR")
        return False
    
    return True

def test_is_due_field():
    """
    B) is_due field tests
    5. Create lead L-Past with follow_up_date="2020-01-01T09:00:00Z"
    6. GET /api/leads → verify L-Past has is_due=true
    7. PATCH L-Past to stage="Lost" → verify is_due=false
    8. Create lead L-Future with follow_up_date="2099-01-01T00:00:00Z" → verify is_due=false
    """
    log("\n" + "="*60)
    log("B) IS_DUE FIELD TESTS")
    log("="*60)
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # Test 5: Create lead L-Past with past follow_up_date
    log("\n--- Test 5: Create lead L-Past with follow_up_date in the past ---")
    
    past_lead_data = {
        "name": "L-Past",
        "stage": "New",
        "company": "Past Corp",
        "follow_up_date": "2020-01-01T09:00:00Z"
    }
    
    resp = requests.post(f"{BASE_URL}/leads", json=past_lead_data, headers=headers, timeout=10)
    if resp.status_code != 200:
        log(f"❌ FAILED to create L-Past: {resp.status_code} {resp.text}", "ERROR")
        return False
    
    l_past = resp.json()
    test_leads.append(l_past["id"])
    log(f"✅ Created L-Past (id={l_past['id'][:8]}, follow_up_date={l_past.get('follow_up_date')})")
    
    # Test 6: GET /api/leads → verify L-Past has is_due=true
    log("\n--- Test 6: GET /api/leads → verify L-Past has is_due=true ---")
    
    resp = requests.get(f"{BASE_URL}/leads", headers=headers, timeout=10)
    if resp.status_code != 200:
        log(f"❌ FAILED: GET /api/leads returned {resp.status_code}: {resp.text}", "ERROR")
        return False
    
    leads = resp.json()
    l_past_in_list = next((l for l in leads if l["id"] == l_past["id"]), None)
    
    if not l_past_in_list:
        log(f"❌ FAIL: L-Past not found in leads list", "ERROR")
        return False
    
    if "is_due" not in l_past_in_list:
        log(f"❌ FAIL: is_due field NOT PRESENT in L-Past response", "ERROR")
        log(f"   Lead keys: {list(l_past_in_list.keys())}", "ERROR")
        return False
    
    if l_past_in_list["is_due"] == True:
        log(f"✅ PASS: L-Past has is_due=true (follow_up_date in past)")
    else:
        log(f"❌ FAIL: L-Past has is_due={l_past_in_list['is_due']}, expected true", "ERROR")
        return False
    
    # Test 7: PATCH L-Past to stage="Lost" → verify is_due=false
    log("\n--- Test 7: PATCH L-Past to stage='Lost' → verify is_due=false ---")
    
    resp = requests.patch(
        f"{BASE_URL}/leads/{l_past['id']}", 
        json={"stage": "Lost"},
        headers=headers, 
        timeout=10
    )
    if resp.status_code != 200:
        log(f"❌ FAILED to update L-Past to Lost: {resp.status_code} {resp.text}", "ERROR")
        return False
    
    log(f"✅ Updated L-Past to stage=Lost")
    
    # GET with include_lost=true to see Lost leads
    resp = requests.get(f"{BASE_URL}/leads?include_lost=true", headers=headers, timeout=10)
    if resp.status_code != 200:
        log(f"❌ FAILED: GET /api/leads?include_lost=true returned {resp.status_code}", "ERROR")
        return False
    
    leads = resp.json()
    l_past_lost = next((l for l in leads if l["id"] == l_past["id"]), None)
    
    if not l_past_lost:
        log(f"❌ FAIL: L-Past not found after marking as Lost", "ERROR")
        return False
    
    if l_past_lost.get("stage") != "Lost":
        log(f"❌ FAIL: L-Past stage is {l_past_lost.get('stage')}, expected Lost", "ERROR")
        return False
    
    if l_past_lost.get("is_due") == False:
        log(f"✅ PASS: L-Past (Lost stage) has is_due=false")
    else:
        log(f"❌ FAIL: L-Past (Lost) has is_due={l_past_lost.get('is_due')}, expected false", "ERROR")
        return False
    
    # Test 8: Create lead L-Future with future follow_up_date → verify is_due=false
    log("\n--- Test 8: Create lead L-Future with follow_up_date in future → verify is_due=false ---")
    
    future_lead_data = {
        "name": "L-Future",
        "stage": "New",
        "company": "Future Corp",
        "follow_up_date": "2099-01-01T00:00:00Z"
    }
    
    resp = requests.post(f"{BASE_URL}/leads", json=future_lead_data, headers=headers, timeout=10)
    if resp.status_code != 200:
        log(f"❌ FAILED to create L-Future: {resp.status_code} {resp.text}", "ERROR")
        return False
    
    l_future = resp.json()
    test_leads.append(l_future["id"])
    log(f"✅ Created L-Future (id={l_future['id'][:8]}, follow_up_date={l_future.get('follow_up_date')})")
    
    resp = requests.get(f"{BASE_URL}/leads", headers=headers, timeout=10)
    if resp.status_code != 200:
        log(f"❌ FAILED: GET /api/leads returned {resp.status_code}", "ERROR")
        return False
    
    leads = resp.json()
    l_future_in_list = next((l for l in leads if l["id"] == l_future["id"]), None)
    
    if not l_future_in_list:
        log(f"❌ FAIL: L-Future not found in leads list", "ERROR")
        return False
    
    if l_future_in_list.get("is_due") == False:
        log(f"✅ PASS: L-Future has is_due=false (follow_up_date in future)")
    else:
        log(f"❌ FAIL: L-Future has is_due={l_future_in_list.get('is_due')}, expected false", "ERROR")
        return False
    
    return True

def cleanup():
    """Delete all test leads."""
    log("\n" + "="*60)
    log("CLEANUP")
    log("="*60)
    
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    for lead_id in test_leads:
        resp = requests.delete(f"{BASE_URL}/leads/{lead_id}", headers=headers, timeout=10)
        if resp.status_code in [200, 404]:
            log(f"✅ Deleted lead {lead_id[:8]}")
        else:
            log(f"⚠️  Could not delete lead {lead_id[:8]}: {resp.status_code}", "WARN")
    
    log("✅ Cleanup complete")

def main():
    """Run the two focused tests."""
    global admin_token
    
    log("="*60)
    log("PHASE 5 RE-VERIFICATION: SORT & IS_DUE")
    log("="*60)
    
    # Login
    admin_token = login(SUPER_ADMIN_EMAIL, SUPER_ADMIN_PASSWORD)
    if not admin_token:
        log("❌ FATAL: Could not login as super admin", "ERROR")
        sys.exit(1)
    
    # Run tests
    results = {
        "A) Sort parameter": test_sort_parameter(),
        "B) is_due field": test_is_due_field(),
    }
    
    # Cleanup
    cleanup()
    
    # Summary
    log("\n" + "="*60)
    log("TEST SUMMARY")
    log("="*60)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        log(f"{status}: {test_name}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    log(f"\nTotal: {passed}/{total} test groups passed")
    
    if passed == total:
        log("\n🎉 ALL TESTS PASSED! Sort and is_due features are working correctly.", "SUCCESS")
        sys.exit(0)
    else:
        log(f"\n❌ {total - passed} test group(s) failed", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()

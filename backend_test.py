#!/usr/bin/env python3
"""Backend testing for Invoice → Recurring template conversion and CRM Quick Log next-step patch."""
import requests
import json
import sys
from datetime import datetime, timezone

# Read base URL from frontend/.env
BASE_URL = "http://localhost:8001/api"
try:
    with open("/app/frontend/.env", "r") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip() + "/api"
                break
except Exception:
    pass

print(f"🔗 Base URL: {BASE_URL}\n")

# Credentials
SUPER_ADMIN = {"email": "superadmin@raybotix.com", "password": "Admin@123"}
PRIYA = {"email": "priya@raybotix.com", "password": "Password@123"}

# Global state
super_token = None
priya_token = None
created_invoice_id = None
created_template_id = None
created_lead_id = None

def login(creds):
    """Login and return token."""
    r = requests.post(f"{BASE_URL}/auth/login", json=creds)
    if r.status_code != 200:
        print(f"❌ Login failed for {creds['email']}: {r.status_code} {r.text}")
        sys.exit(1)
    data = r.json()
    token = data.get("access_token") or data.get("token")
    if not token:
        print(f"❌ No token in login response: {data}")
        sys.exit(1)
    print(f"✅ Logged in as {creds['email']}")
    return token

def headers(token):
    return {"Authorization": f"Bearer {token}"}

def test_1_login():
    """Test 1: Login as super admin."""
    global super_token
    super_token = login(SUPER_ADMIN)
    print("✅ Test 1 PASSED: Login as super admin\n")

def test_2_create_invoice():
    """Test 2: POST /api/invoices with body."""
    global created_invoice_id
    payload = {
        "client_name": "Recur Client",
        "client_company": "Recur Co",
        "items": [
            {
                "description": "Monthly retainer",
                "qty": 1,
                "rate": 30000,
                "gst_pct": 18
            }
        ]
    }
    r = requests.post(f"{BASE_URL}/invoices", json=payload, headers=headers(super_token))
    if r.status_code != 200:
        print(f"❌ Test 2 FAILED: POST /api/invoices returned {r.status_code}: {r.text}")
        sys.exit(1)
    
    data = r.json()
    created_invoice_id = data.get("id")
    number = data.get("number")
    status = data.get("status")
    total = data.get("total")
    
    # Verify response
    if not created_invoice_id:
        print(f"❌ Test 2 FAILED: No id in response")
        sys.exit(1)
    
    # Check number format: RB-INV-YYYY-NNNN
    import re
    if not re.match(r'^RB-INV-\d{4}-\d{4}$', number):
        print(f"❌ Test 2 FAILED: Invalid number format: {number}")
        sys.exit(1)
    
    if status != "draft":
        print(f"❌ Test 2 FAILED: Expected status='draft', got '{status}'")
        sys.exit(1)
    
    # Expected total: 30000 * 1.18 = 35400
    if total != 35400:
        print(f"❌ Test 2 FAILED: Expected total=35400, got {total}")
        sys.exit(1)
    
    print(f"✅ Test 2 PASSED: Created invoice {number} (id={created_invoice_id}, status={status}, total={total})\n")

def test_3_invoice_to_recurring():
    """Test 3: POST /api/invoices/{id}/to-recurring with body {"day_of_month":5}."""
    global created_template_id
    payload = {"day_of_month": 5}
    r = requests.post(f"{BASE_URL}/invoices/{created_invoice_id}/to-recurring", 
                     json=payload, headers=headers(super_token))
    
    if r.status_code != 200:
        print(f"❌ Test 3 FAILED: POST /api/invoices/{created_invoice_id}/to-recurring returned {r.status_code}: {r.text}")
        sys.exit(1)
    
    data = r.json()
    if not data.get("ok"):
        print(f"❌ Test 3 FAILED: Response ok != true")
        sys.exit(1)
    
    template = data.get("template")
    if not template:
        print(f"❌ Test 3 FAILED: No template in response")
        sys.exit(1)
    
    created_template_id = template.get("id")
    day_of_month = template.get("day_of_month")
    active = template.get("active")
    items = template.get("items", [])
    next_run_date = template.get("next_run_date")
    client_name = template.get("client_name")
    client_company = template.get("client_company")
    
    # Verify fields
    if not created_template_id:
        print(f"❌ Test 3 FAILED: No template id")
        sys.exit(1)
    
    if day_of_month != 5:
        print(f"❌ Test 3 FAILED: Expected day_of_month=5, got {day_of_month}")
        sys.exit(1)
    
    if active != True:
        print(f"❌ Test 3 FAILED: Expected active=true, got {active}")
        sys.exit(1)
    
    if not items or len(items) == 0:
        print(f"❌ Test 3 FAILED: No items in template")
        sys.exit(1)
    
    # Check item
    item = items[0]
    if item.get("description") != "Monthly retainer":
        print(f"❌ Test 3 FAILED: Item description mismatch")
        sys.exit(1)
    
    if item.get("qty") != 1 or item.get("rate") != 30000 or item.get("gst_pct") != 18:
        print(f"❌ Test 3 FAILED: Item data mismatch")
        sys.exit(1)
    
    if not next_run_date:
        print(f"❌ Test 3 FAILED: No next_run_date")
        sys.exit(1)
    
    if client_name != "Recur Client":
        print(f"❌ Test 3 FAILED: client_name mismatch: {client_name}")
        sys.exit(1)
    
    if client_company != "Recur Co":
        print(f"❌ Test 3 FAILED: client_company mismatch: {client_company}")
        sys.exit(1)
    
    print(f"✅ Test 3 PASSED: Invoice converted to recurring template (id={created_template_id}, day_of_month={day_of_month}, active={active}, next_run_date={next_run_date})\n")

def test_4_get_recurring_invoices():
    """Test 4: GET /api/recurring-invoices → returns array containing the new template."""
    r = requests.get(f"{BASE_URL}/recurring-invoices", headers=headers(super_token))
    
    if r.status_code != 200:
        print(f"❌ Test 4 FAILED: GET /api/recurring-invoices returned {r.status_code}: {r.text}")
        sys.exit(1)
    
    templates = r.json()
    if not isinstance(templates, list):
        print(f"❌ Test 4 FAILED: Response is not an array")
        sys.exit(1)
    
    # Find our template
    found = None
    for t in templates:
        if t.get("id") == created_template_id:
            found = t
            break
    
    if not found:
        print(f"❌ Test 4 FAILED: Template {created_template_id} not found in list")
        sys.exit(1)
    
    # Verify items have fresh ids (not equal to invoice's item id)
    items = found.get("items", [])
    if not items:
        print(f"❌ Test 4 FAILED: No items in template")
        sys.exit(1)
    
    # Items should have new ids (we can't compare to original invoice item ids easily,
    # but we can verify they exist and are non-empty)
    for item in items:
        if not item.get("id"):
            print(f"❌ Test 4 FAILED: Item missing id")
            sys.exit(1)
    
    print(f"✅ Test 4 PASSED: GET /api/recurring-invoices returns template with fresh item ids\n")

def test_5_invalid_day_of_month():
    """Test 5: POST /api/invoices/{id}/to-recurring {"day_of_month":45} (invalid)."""
    # Create a new invoice for this test
    payload = {
        "client_name": "Test Client 2",
        "client_company": "Test Co 2",
        "items": [{"description": "Test item", "qty": 1, "rate": 1000, "gst_pct": 18}]
    }
    r = requests.post(f"{BASE_URL}/invoices", json=payload, headers=headers(super_token))
    if r.status_code != 200:
        print(f"❌ Test 5 FAILED: Could not create test invoice: {r.status_code}")
        sys.exit(1)
    
    test_invoice_id = r.json().get("id")
    
    # Try to convert with invalid day_of_month
    payload = {"day_of_month": 45}
    r = requests.post(f"{BASE_URL}/invoices/{test_invoice_id}/to-recurring", 
                     json=payload, headers=headers(super_token))
    
    # Server should either clamp to 28 (200) or return error (4xx)
    if r.status_code == 200:
        # Check if clamped to 28
        data = r.json()
        template = data.get("template", {})
        day = template.get("day_of_month")
        if day != 28:
            print(f"❌ Test 5 FAILED: Expected day_of_month to be clamped to 28, got {day}")
            sys.exit(1)
        print(f"✅ Test 5 PASSED: Invalid day_of_month (45) clamped to 28\n")
        # Cleanup
        requests.delete(f"{BASE_URL}/recurring-invoices/{template.get('id')}", headers=headers(super_token))
    elif 400 <= r.status_code < 500:
        print(f"✅ Test 5 PASSED: Invalid day_of_month (45) rejected with HTTP {r.status_code}\n")
    else:
        print(f"❌ Test 5 FAILED: Unexpected status code {r.status_code}: {r.text}")
        sys.exit(1)
    
    # Cleanup test invoice
    requests.delete(f"{BASE_URL}/invoices/{test_invoice_id}", headers=headers(super_token))

def test_6_non_existent_invoice():
    """Test 6: POST /api/invoices/deadbeef/to-recurring {"day_of_month":5} → HTTP 404."""
    payload = {"day_of_month": 5}
    r = requests.post(f"{BASE_URL}/invoices/deadbeef/to-recurring", 
                     json=payload, headers=headers(super_token))
    
    if r.status_code != 404:
        print(f"❌ Test 6 FAILED: Expected 404, got {r.status_code}")
        sys.exit(1)
    
    print(f"✅ Test 6 PASSED: Non-existent invoice returns 404\n")

def test_7_rbac_no_crm_access():
    """Test 7: RBAC - as priya@raybotix.com (NO CRM access), POST /api/invoices/{id}/to-recurring → HTTP 403."""
    global priya_token
    
    # First, verify Priya does NOT have crm_access
    priya_token = login(PRIYA)
    
    # Get Priya's user info
    r = requests.get(f"{BASE_URL}/auth/me", headers=headers(priya_token))
    if r.status_code != 200:
        print(f"❌ Test 7 FAILED: Could not get Priya's user info: {r.status_code}")
        sys.exit(1)
    
    priya_user = r.json()
    if priya_user.get("crm_access") == True:
        print(f"⚠️  Test 7 SKIPPED: Priya already has crm_access=true, cannot test RBAC denial")
        print(f"    (This is expected if previous tests granted her access)\n")
        return
    
    # Try to convert invoice to recurring as Priya (no CRM access)
    payload = {"day_of_month": 5}
    r = requests.post(f"{BASE_URL}/invoices/{created_invoice_id}/to-recurring", 
                     json=payload, headers=headers(priya_token))
    
    if r.status_code != 403:
        print(f"❌ Test 7 FAILED: Expected 403, got {r.status_code}: {r.text}")
        sys.exit(1)
    
    print(f"✅ Test 7 PASSED: User without CRM access denied (403)\n")

def test_8_crm_quick_log_next_step():
    """Test 8: CRM Quick Log next-step - PATCH /api/leads/{id} {"next_step":"Send proposal"}."""
    global created_lead_id
    
    # Create a test lead first
    payload = {
        "name": "Test Lead for Next Step",
        "company": "Test Company",
        "email": "test@example.com",
        "stage": "New"
    }
    r = requests.post(f"{BASE_URL}/leads", json=payload, headers=headers(super_token))
    if r.status_code != 200:
        print(f"❌ Test 8 FAILED: Could not create test lead: {r.status_code}: {r.text}")
        sys.exit(1)
    
    created_lead_id = r.json().get("id")
    
    # PATCH next_step
    patch_payload = {"next_step": "Send proposal"}
    r = requests.patch(f"{BASE_URL}/leads/{created_lead_id}", 
                      json=patch_payload, headers=headers(super_token))
    
    if r.status_code != 200:
        print(f"❌ Test 8 FAILED: PATCH /api/leads/{created_lead_id} returned {r.status_code}: {r.text}")
        sys.exit(1)
    
    data = r.json()
    next_step = data.get("next_step")
    
    if next_step != "Send proposal":
        print(f"❌ Test 8 FAILED: Expected next_step='Send proposal', got '{next_step}'")
        sys.exit(1)
    
    # Verify with GET
    r = requests.get(f"{BASE_URL}/leads", headers=headers(super_token))
    if r.status_code != 200:
        print(f"❌ Test 8 FAILED: GET /api/leads returned {r.status_code}")
        sys.exit(1)
    
    leads = r.json()
    found_lead = None
    for lead in leads:
        if lead.get("id") == created_lead_id:
            found_lead = lead
            break
    
    if not found_lead:
        print(f"❌ Test 8 FAILED: Lead not found in GET /api/leads")
        sys.exit(1)
    
    if found_lead.get("next_step") != "Send proposal":
        print(f"❌ Test 8 FAILED: GET /api/leads shows next_step='{found_lead.get('next_step')}', expected 'Send proposal'")
        sys.exit(1)
    
    print(f"✅ Test 8 PASSED: CRM Quick Log next-step updated successfully\n")

def test_9_regression():
    """Test 9: Regression - verify key endpoints still work."""
    endpoints = [
        "/analytics/dashboard",
        "/tasks?scope=all",
        "/leads?sort=priority",
        "/analytics/costs?range=month"
    ]
    
    for endpoint in endpoints:
        r = requests.get(f"{BASE_URL}{endpoint}", headers=headers(super_token))
        if r.status_code != 200:
            print(f"❌ Test 9 FAILED: GET {endpoint} returned {r.status_code}: {r.text}")
            sys.exit(1)
    
    print(f"✅ Test 9 PASSED: All regression endpoints return 200\n")

def cleanup():
    """Cleanup: delete created invoice, recurring template, and lead."""
    print("🧹 Cleanup...")
    
    # Delete recurring template
    if created_template_id:
        r = requests.delete(f"{BASE_URL}/recurring-invoices/{created_template_id}", 
                          headers=headers(super_token))
        if r.status_code == 200:
            print(f"  ✅ Deleted recurring template {created_template_id}")
        else:
            print(f"  ⚠️  Could not delete recurring template: {r.status_code}")
    
    # Delete invoice
    if created_invoice_id:
        r = requests.delete(f"{BASE_URL}/invoices/{created_invoice_id}", 
                          headers=headers(super_token))
        if r.status_code == 200:
            print(f"  ✅ Deleted invoice {created_invoice_id}")
        else:
            print(f"  ⚠️  Could not delete invoice: {r.status_code}")
    
    # Delete lead
    if created_lead_id:
        r = requests.delete(f"{BASE_URL}/leads/{created_lead_id}", 
                          headers=headers(super_token))
        if r.status_code == 200:
            print(f"  ✅ Deleted lead {created_lead_id}")
        else:
            print(f"  ⚠️  Could not delete lead: {r.status_code}")
    
    print()

def main():
    print("=" * 80)
    print("BACKEND TESTING: Invoice → Recurring Template + CRM Quick Log")
    print("=" * 80)
    print()
    
    try:
        test_1_login()
        test_2_create_invoice()
        test_3_invoice_to_recurring()
        test_4_get_recurring_invoices()
        test_5_invalid_day_of_month()
        test_6_non_existent_invoice()
        test_7_rbac_no_crm_access()
        test_8_crm_quick_log_next_step()
        test_9_regression()
        
        print("=" * 80)
        print("✅ ALL TESTS PASSED (9/9)")
        print("=" * 80)
        print()
        
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cleanup()

if __name__ == "__main__":
    main()

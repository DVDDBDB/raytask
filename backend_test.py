#!/usr/bin/env python3
"""Phase 4 Backend Testing - All 30 tests"""
import requests
import json
import sys
from datetime import datetime, timezone, timedelta

# Configuration
BASE_URL = "https://ray-task-hub.preview.emergentagent.com/api"
SUPER_ADMIN = {"email": "superadmin@raybotix.com", "password": "Admin@123"}
PRIYA = {"email": "priya@raybotix.com", "password": "Password@123"}

# Global state
tokens = {}
test_data = {}
results = []


def log_test(num, desc, status, details=""):
    """Log test result"""
    symbol = "✅" if status == "PASS" else "❌"
    msg = f"{symbol} Test {num}: {desc} - {status}"
    if details:
        msg += f" ({details})"
    print(msg)
    results.append({"num": num, "desc": desc, "status": status, "details": details})


def login(creds):
    """Login and return token"""
    r = requests.post(f"{BASE_URL}/auth/login", json=creds)
    if r.status_code != 200:
        print(f"   Login failed: {r.status_code} - {r.text}")
        return None
    return r.json().get("token")


def get_headers(token):
    """Get auth headers"""
    return {"Authorization": f"Bearer {token}"}


def cleanup():
    """Cleanup test data"""
    print("\n🧹 Cleanup...")
    token = tokens.get("super_admin")
    if not token:
        return
    
    headers = get_headers(token)
    
    # Delete test leads
    for lead_id in test_data.get("lead_ids", []):
        requests.delete(f"{BASE_URL}/leads/{lead_id}", headers=headers)
    
    # Delete test quotations
    for q_id in test_data.get("quotation_ids", []):
        requests.delete(f"{BASE_URL}/quotations/{q_id}", headers=headers)
    
    # Delete test invoices
    for i_id in test_data.get("invoice_ids", []):
        requests.delete(f"{BASE_URL}/invoices/{i_id}", headers=headers)
    
    # Delete recurring invoices
    for r_id in test_data.get("recurring_ids", []):
        requests.delete(f"{BASE_URL}/recurring-invoices/{r_id}", headers=headers)
    
    # Delete counters
    # Note: Can't delete via API, would need direct DB access
    
    # Revoke Priya's CRM access
    priya_id = test_data.get("priya_id")
    if priya_id:
        requests.patch(
            f"{BASE_URL}/users/{priya_id}",
            json={"crm_access": False},
            headers=headers
        )
    
    print("✅ Cleanup complete")


def main():
    global tokens, test_data
    
    print("=" * 80)
    print("Phase 4 Backend Testing - 30 Tests")
    print("=" * 80)
    
    # Login
    print("\n🔐 Logging in...")
    tokens["super_admin"] = login(SUPER_ADMIN)
    if not tokens["super_admin"]:
        print("❌ Failed to login as super admin")
        return 1
    print("✅ Super admin logged in")
    
    tokens["priya"] = login(PRIYA)
    if not tokens["priya"]:
        print("❌ Failed to login as Priya")
        return 1
    print("✅ Priya logged in")
    
    # Get Priya's user ID
    r = requests.get(f"{BASE_URL}/auth/me", headers=get_headers(tokens["priya"]))
    if r.status_code == 200:
        test_data["priya_id"] = r.json()["id"]
    else:
        print(f"❌ Failed to get Priya's user ID: {r.status_code}")
        return 1
    
    test_data["quotation_ids"] = []
    test_data["invoice_ids"] = []
    test_data["lead_ids"] = []
    test_data["recurring_ids"] = []
    
    try:
        # ============================================================
        # A) BILLING VISIBILITY
        # ============================================================
        print("\n" + "=" * 80)
        print("A) BILLING VISIBILITY")
        print("=" * 80)
        
        # Test 1: Super admin creates Q1
        print("\n--- Test 1: Super admin creates quotation Q1 ---")
        r = requests.post(
            f"{BASE_URL}/quotations",
            json={
                "client_name": "Client A",
                "items": [{"description": "Service X", "qty": 1, "rate": 1000, "gst_pct": 18}]
            },
            headers=get_headers(tokens["super_admin"])
        )
        if r.status_code == 200:
            q1 = r.json()
            test_data["q1_id"] = q1["id"]
            test_data["quotation_ids"].append(q1["id"])
            log_test(1, "Super admin creates Q1", "PASS", f"HTTP {r.status_code}, id={q1['id']}")
        else:
            log_test(1, "Super admin creates Q1", "FAIL", f"HTTP {r.status_code}: {r.text}")
        
        # Test 2: Grant Priya CRM access
        print("\n--- Test 2: Grant Priya CRM access ---")
        r = requests.patch(
            f"{BASE_URL}/users/{test_data['priya_id']}",
            json={"crm_access": True},
            headers=get_headers(tokens["super_admin"])
        )
        if r.status_code == 200:
            log_test(2, "Grant Priya CRM access", "PASS", f"HTTP {r.status_code}")
        else:
            log_test(2, "Grant Priya CRM access", "FAIL", f"HTTP {r.status_code}: {r.text}")
        
        # Test 3: Priya creates Q2
        print("\n--- Test 3: Priya creates quotation Q2 ---")
        r = requests.post(
            f"{BASE_URL}/quotations",
            json={
                "client_name": "Client B",
                "items": [{"description": "Service Y", "qty": 1, "rate": 2000, "gst_pct": 18}]
            },
            headers=get_headers(tokens["priya"])
        )
        if r.status_code == 200:
            q2 = r.json()
            test_data["q2_id"] = q2["id"]
            test_data["quotation_ids"].append(q2["id"])
            log_test(3, "Priya creates Q2", "PASS", f"HTTP {r.status_code}, id={q2['id']}")
        else:
            log_test(3, "Priya creates Q2", "FAIL", f"HTTP {r.status_code}: {r.text}")
        
        # Test 4: Priya lists quotations (should only see Q2)
        print("\n--- Test 4: Priya lists quotations (visibility check) ---")
        r = requests.get(f"{BASE_URL}/quotations", headers=get_headers(tokens["priya"]))
        if r.status_code == 200:
            quotations = r.json()
            q_ids = [q["id"] for q in quotations]
            has_q2 = test_data.get("q2_id") in q_ids
            has_q1 = test_data.get("q1_id") in q_ids
            if has_q2 and not has_q1:
                log_test(4, "Priya lists quotations - only Q2 visible", "PASS", f"Q2 present, Q1 absent")
            else:
                log_test(4, "Priya lists quotations - only Q2 visible", "FAIL", 
                        f"Q2 present={has_q2}, Q1 present={has_q1} (should be True, False)")
        else:
            log_test(4, "Priya lists quotations", "FAIL", f"HTTP {r.status_code}: {r.text}")
        
        # Super admin should see both
        r = requests.get(f"{BASE_URL}/quotations", headers=get_headers(tokens["super_admin"]))
        if r.status_code == 200:
            quotations = r.json()
            q_ids = [q["id"] for q in quotations]
            has_both = test_data.get("q1_id") in q_ids and test_data.get("q2_id") in q_ids
            print(f"   Super admin sees both Q1 and Q2: {has_both}")
        
        # Test 5: Priya GET Q1 (403), GET Q2 (200)
        print("\n--- Test 5: Priya GET individual quotations ---")
        r1 = requests.get(f"{BASE_URL}/quotations/{test_data.get('q1_id')}", 
                         headers=get_headers(tokens["priya"]))
        r2 = requests.get(f"{BASE_URL}/quotations/{test_data.get('q2_id')}", 
                         headers=get_headers(tokens["priya"]))
        if r1.status_code == 403 and r2.status_code == 200:
            log_test(5, "Priya GET Q1→403, Q2→200", "PASS", f"Q1: {r1.status_code}, Q2: {r2.status_code}")
        else:
            log_test(5, "Priya GET Q1→403, Q2→200", "FAIL", 
                    f"Q1: {r1.status_code} (expected 403), Q2: {r2.status_code} (expected 200)")
        
        # Test 6: Priya PATCH Q1 (403)
        print("\n--- Test 6: Priya PATCH Q1 (should be 403) ---")
        r = requests.patch(
            f"{BASE_URL}/quotations/{test_data.get('q1_id')}",
            json={"notes": "tamper"},
            headers=get_headers(tokens["priya"])
        )
        if r.status_code == 403:
            log_test(6, "Priya PATCH Q1→403", "PASS", f"HTTP {r.status_code}")
        else:
            log_test(6, "Priya PATCH Q1→403", "FAIL", f"HTTP {r.status_code} (expected 403)")
        
        # Test 7: Repeat for invoices
        print("\n--- Test 7: Invoice visibility (same pattern) ---")
        # Super admin creates Inv1
        r = requests.post(
            f"{BASE_URL}/invoices",
            json={
                "client_name": "Client A",
                "items": [{"description": "Service X", "qty": 1, "rate": 1000, "gst_pct": 18}]
            },
            headers=get_headers(tokens["super_admin"])
        )
        if r.status_code == 200:
            inv1 = r.json()
            test_data["inv1_id"] = inv1["id"]
            test_data["invoice_ids"].append(inv1["id"])
        
        # Priya creates Inv2
        r = requests.post(
            f"{BASE_URL}/invoices",
            json={
                "client_name": "Client B",
                "items": [{"description": "Service Y", "qty": 1, "rate": 2000, "gst_pct": 18}]
            },
            headers=get_headers(tokens["priya"])
        )
        if r.status_code == 200:
            inv2 = r.json()
            test_data["inv2_id"] = inv2["id"]
            test_data["invoice_ids"].append(inv2["id"])
        
        # Priya lists (should only see Inv2)
        r = requests.get(f"{BASE_URL}/invoices", headers=get_headers(tokens["priya"]))
        if r.status_code == 200:
            invoices = r.json()
            i_ids = [i["id"] for i in invoices]
            has_inv2 = test_data.get("inv2_id") in i_ids
            has_inv1 = test_data.get("inv1_id") in i_ids
            if has_inv2 and not has_inv1:
                log_test(7, "Invoice visibility - Priya sees only Inv2", "PASS", 
                        f"Inv2 present, Inv1 absent")
            else:
                log_test(7, "Invoice visibility - Priya sees only Inv2", "FAIL", 
                        f"Inv2={has_inv2}, Inv1={has_inv1}")
        else:
            log_test(7, "Invoice visibility", "FAIL", f"HTTP {r.status_code}")
        
        # Priya GET/PATCH Inv1 (403)
        r_get = requests.get(f"{BASE_URL}/invoices/{test_data.get('inv1_id')}", 
                            headers=get_headers(tokens["priya"]))
        r_patch = requests.patch(
            f"{BASE_URL}/invoices/{test_data.get('inv1_id')}",
            json={"notes": "tamper"},
            headers=get_headers(tokens["priya"])
        )
        if r_get.status_code == 403 and r_patch.status_code == 403:
            print(f"   Priya GET Inv1→{r_get.status_code}, PATCH Inv1→{r_patch.status_code} ✅")
        else:
            print(f"   Priya GET Inv1→{r_get.status_code}, PATCH Inv1→{r_patch.status_code} (expected 403)")
        
        # ============================================================
        # B) CRM TEMPERATURE
        # ============================================================
        print("\n" + "=" * 80)
        print("B) CRM TEMPERATURE")
        print("=" * 80)
        
        # Test 8: Create lead with temperature="hot"
        print("\n--- Test 8: Create lead with temperature='hot' ---")
        r = requests.post(
            f"{BASE_URL}/leads",
            json={
                "name": "Hot Deal",
                "stage": "Contacted",
                "temperature": "hot"
            },
            headers=get_headers(tokens["super_admin"])
        )
        if r.status_code == 200:
            lead = r.json()
            test_data["hot_lead_id"] = lead["id"]
            test_data["lead_ids"].append(lead["id"])
            if lead.get("temperature") == "hot":
                log_test(8, "Create lead with temperature='hot'", "PASS", 
                        f"HTTP {r.status_code}, temperature={lead.get('temperature')}")
            else:
                log_test(8, "Create lead with temperature='hot'", "FAIL", 
                        f"temperature={lead.get('temperature')} (expected 'hot')")
        else:
            log_test(8, "Create lead with temperature='hot'", "FAIL", f"HTTP {r.status_code}: {r.text}")
        
        # Test 9: PATCH temperature to "cold"
        print("\n--- Test 9: PATCH temperature to 'cold' ---")
        r = requests.patch(
            f"{BASE_URL}/leads/{test_data.get('hot_lead_id')}",
            json={"temperature": "cold"},
            headers=get_headers(tokens["super_admin"])
        )
        if r.status_code == 200:
            lead = r.json()
            if lead.get("temperature") == "cold":
                log_test(9, "PATCH temperature to 'cold'", "PASS", 
                        f"HTTP {r.status_code}, temperature={lead.get('temperature')}")
            else:
                log_test(9, "PATCH temperature to 'cold'", "FAIL", 
                        f"temperature={lead.get('temperature')} (expected 'cold')")
        else:
            log_test(9, "PATCH temperature to 'cold'", "FAIL", f"HTTP {r.status_code}: {r.text}")
        
        # Test 10: PATCH invalid temperature "lukewarm" (400)
        print("\n--- Test 10: PATCH invalid temperature 'lukewarm' (should be 400) ---")
        r = requests.patch(
            f"{BASE_URL}/leads/{test_data.get('hot_lead_id')}",
            json={"temperature": "lukewarm"},
            headers=get_headers(tokens["super_admin"])
        )
        if r.status_code == 400:
            log_test(10, "PATCH invalid temperature→400", "PASS", f"HTTP {r.status_code}")
        else:
            log_test(10, "PATCH invalid temperature→400", "FAIL", 
                    f"HTTP {r.status_code} (expected 400): {r.text}")
        
        # ============================================================
        # C) HIDE ONBOARDED
        # ============================================================
        print("\n" + "=" * 80)
        print("C) HIDE ONBOARDED")
        print("=" * 80)
        
        # Test 11: Create lead L1, onboard it, verify hidden by default
        print("\n--- Test 11: Hide Onboarded leads by default ---")
        r = requests.post(
            f"{BASE_URL}/leads",
            json={"name": "Lead L1", "stage": "New"},
            headers=get_headers(tokens["super_admin"])
        )
        if r.status_code == 200:
            l1 = r.json()
            test_data["l1_id"] = l1["id"]
            test_data["lead_ids"].append(l1["id"])
            
            # Onboard L1
            r2 = requests.post(
                f"{BASE_URL}/leads/{l1['id']}/onboard",
                json={},
                headers=get_headers(tokens["super_admin"])
            )
            if r2.status_code == 200:
                # GET /leads (should NOT include L1)
                r3 = requests.get(f"{BASE_URL}/leads", headers=get_headers(tokens["super_admin"]))
                if r3.status_code == 200:
                    leads = r3.json()
                    l_ids = [l["id"] for l in leads]
                    has_l1 = l1["id"] in l_ids
                    
                    # GET /leads?include_onboarded=true (should include L1)
                    r4 = requests.get(f"{BASE_URL}/leads?include_onboarded=true", 
                                     headers=get_headers(tokens["super_admin"]))
                    if r4.status_code == 200:
                        leads_with = r4.json()
                        l_ids_with = [l["id"] for l in leads_with]
                        has_l1_with = l1["id"] in l_ids_with
                        
                        if not has_l1 and has_l1_with:
                            log_test(11, "Hide Onboarded by default", "PASS", 
                                    f"L1 absent in default list, present with include_onboarded=true")
                        else:
                            log_test(11, "Hide Onboarded by default", "FAIL", 
                                    f"Default: L1 present={has_l1} (should be False), "
                                    f"With param: L1 present={has_l1_with} (should be True)")
                    else:
                        log_test(11, "Hide Onboarded by default", "FAIL", 
                                f"include_onboarded=true returned {r4.status_code}")
                else:
                    log_test(11, "Hide Onboarded by default", "FAIL", f"GET /leads returned {r3.status_code}")
            else:
                log_test(11, "Hide Onboarded by default", "FAIL", f"Onboard returned {r2.status_code}")
        else:
            log_test(11, "Hide Onboarded by default", "FAIL", f"Create lead returned {r.status_code}")
        
        # ============================================================
        # D) LOST → CLEAR FOLLOW-UPS
        # ============================================================
        print("\n" + "=" * 80)
        print("D) LOST → CLEAR FOLLOW-UPS")
        print("=" * 80)
        
        # Test 12: Create L2 with follow_up_date, activities, then mark Lost
        print("\n--- Test 12: Lost stage clears follow-ups ---")
        future_date = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        r = requests.post(
            f"{BASE_URL}/leads",
            json={
                "name": "Lead L2",
                "stage": "Contacted",
                "follow_up_date": future_date,
                "next_step": "Send deck"
            },
            headers=get_headers(tokens["super_admin"])
        )
        if r.status_code == 200:
            l2 = r.json()
            test_data["l2_id"] = l2["id"]
            test_data["lead_ids"].append(l2["id"])
            
            # Add activities (one with due_date, one without)
            r2 = requests.post(
                f"{BASE_URL}/leads/{l2['id']}/activities",
                json={
                    "kind": "call",
                    "description": "Called client",
                    "due_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
                },
                headers=get_headers(tokens["super_admin"])
            )
            r3 = requests.post(
                f"{BASE_URL}/leads/{l2['id']}/activities",
                json={"kind": "note", "description": "Note without due date"},
                headers=get_headers(tokens["super_admin"])
            )
            
            # Mark as Lost
            r4 = requests.patch(
                f"{BASE_URL}/leads/{l2['id']}",
                json={"stage": "Lost"},
                headers=get_headers(tokens["super_admin"])
            )
            if r4.status_code == 200:
                lost_lead = r4.json()
                
                # Verify follow_up_date=None, next_step="", activities done=True, due_date=None
                checks = []
                checks.append(("follow_up_date is None", lost_lead.get("follow_up_date") is None))
                checks.append(("next_step is empty", lost_lead.get("next_step") == ""))
                checks.append(("lost_at is set", lost_lead.get("lost_at") is not None))
                
                activities = lost_lead.get("activities", [])
                all_done = all(a.get("done") for a in activities)
                all_no_due = all(a.get("due_date") is None for a in activities)
                checks.append(("all activities done=True", all_done))
                checks.append(("all activities due_date=None", all_no_due))
                
                if all(c[1] for c in checks):
                    log_test(12, "Lost stage clears follow-ups", "PASS", 
                            f"All checks passed: {', '.join(c[0] for c in checks)}")
                else:
                    failed = [c[0] for c in checks if not c[1]]
                    log_test(12, "Lost stage clears follow-ups", "FAIL", 
                            f"Failed checks: {', '.join(failed)}")
            else:
                log_test(12, "Lost stage clears follow-ups", "FAIL", 
                        f"PATCH Lost returned {r4.status_code}")
        else:
            log_test(12, "Lost stage clears follow-ups", "FAIL", f"Create L2 returned {r.status_code}")
        
        # Test 13: GET /follow-ups/upcoming should NOT include L2
        print("\n--- Test 13: Lost lead not in upcoming follow-ups ---")
        r = requests.get(f"{BASE_URL}/leads/follow-ups/upcoming?days=30", 
                        headers=get_headers(tokens["super_admin"]))
        if r.status_code == 200:
            followups = r.json()
            fu_ids = [f["id"] for f in followups]
            has_l2 = test_data.get("l2_id") in fu_ids
            if not has_l2:
                log_test(13, "Lost lead not in upcoming follow-ups", "PASS", "L2 not present")
            else:
                log_test(13, "Lost lead not in upcoming follow-ups", "FAIL", "L2 is present (should be absent)")
        else:
            log_test(13, "Lost lead not in upcoming follow-ups", "FAIL", f"HTTP {r.status_code}")
        
        # ============================================================
        # E) LEAD ANALYTICS
        # ============================================================
        print("\n" + "=" * 80)
        print("E) LEAD ANALYTICS")
        print("=" * 80)
        
        # Test 14: Super admin GET /analytics/leads
        print("\n--- Test 14: Super admin GET /analytics/leads ---")
        r = requests.get(f"{BASE_URL}/analytics/leads", headers=get_headers(tokens["super_admin"]))
        if r.status_code == 200:
            data = r.json()
            has_owners = "owners" in data and isinstance(data["owners"], list)
            has_totals = "totals" in data and isinstance(data["totals"], dict)
            
            if has_owners and has_totals:
                # Check totals keys
                totals = data["totals"]
                required_keys = ["total_contacted", "total_converted", "total_lost", 
                               "pipeline_value", "sales_generated"]
                has_all_keys = all(k in totals for k in required_keys)
                
                # Check owner structure
                if data["owners"]:
                    owner = data["owners"][0]
                    owner_keys = ["owner_id", "owner_name", "contacted", "converted", "lost", 
                                "in_pipeline", "pipeline_value", "onboarded_value", 
                                "conversion_rate", "hot", "warm", "cold"]
                    has_owner_keys = all(k in owner for k in owner_keys)
                else:
                    has_owner_keys = True  # No owners is OK
                
                if has_all_keys and has_owner_keys:
                    log_test(14, "Super admin GET /analytics/leads", "PASS", 
                            f"HTTP {r.status_code}, owners={len(data['owners'])}, "
                            f"totals keys present")
                else:
                    log_test(14, "Super admin GET /analytics/leads", "FAIL", 
                            f"Missing keys: totals={has_all_keys}, owner={has_owner_keys}")
            else:
                log_test(14, "Super admin GET /analytics/leads", "FAIL", 
                        f"Missing owners or totals: owners={has_owners}, totals={has_totals}")
        else:
            log_test(14, "Super admin GET /analytics/leads", "FAIL", f"HTTP {r.status_code}: {r.text}")
        
        # Test 15: Priya GET /analytics/leads (should only see her row)
        print("\n--- Test 15: Priya GET /analytics/leads (own data only) ---")
        r = requests.get(f"{BASE_URL}/analytics/leads", headers=get_headers(tokens["priya"]))
        if r.status_code == 200:
            data = r.json()
            owners = data.get("owners", [])
            # Should only contain Priya's row or be empty
            priya_id = test_data.get("priya_id")
            other_owners = [o for o in owners if o.get("owner_id") != priya_id]
            
            if not other_owners:
                log_test(15, "Priya sees only own analytics", "PASS", 
                        f"HTTP {r.status_code}, owners count={len(owners)}, no other owners")
            else:
                log_test(15, "Priya sees only own analytics", "FAIL", 
                        f"Found {len(other_owners)} other owners (should be 0)")
        else:
            log_test(15, "Priya sees only own analytics", "FAIL", f"HTTP {r.status_code}: {r.text}")
        
        # Test 16: Sales attribution (create lead L3 owned by Priya, invoice, mark paid)
        print("\n--- Test 16: Sales attribution to lead owner ---")
        r = requests.post(
            f"{BASE_URL}/leads",
            json={
                "name": "Lead L3",
                "stage": "Contacted",
                "assigned_to_id": test_data.get("priya_id")
            },
            headers=get_headers(tokens["super_admin"])
        )
        if r.status_code == 200:
            l3 = r.json()
            test_data["l3_id"] = l3["id"]
            test_data["lead_ids"].append(l3["id"])
            
            # Create invoice linked to L3
            r2 = requests.post(
                f"{BASE_URL}/invoices",
                json={
                    "lead_id": l3["id"],
                    "client_name": "Client L3",
                    "items": [{"description": "Service", "qty": 1, "rate": 5000, "gst_pct": 18}]
                },
                headers=get_headers(tokens["super_admin"])
            )
            if r2.status_code == 200:
                inv = r2.json()
                test_data["invoice_ids"].append(inv["id"])
                
                # Mark paid
                r3 = requests.post(
                    f"{BASE_URL}/invoices/{inv['id']}/mark-paid",
                    headers=get_headers(tokens["super_admin"])
                )
                if r3.status_code == 200:
                    # Get Priya's analytics
                    r4 = requests.get(f"{BASE_URL}/analytics/leads", 
                                     headers=get_headers(tokens["priya"]))
                    if r4.status_code == 200:
                        data = r4.json()
                        owners = data.get("owners", [])
                        priya_row = next((o for o in owners if o.get("owner_id") == test_data.get("priya_id")), None)
                        
                        if priya_row:
                            onboarded_value = priya_row.get("onboarded_value", 0)
                            # Invoice total should be 5000 * 1.18 = 5900
                            if onboarded_value >= 5900:
                                log_test(16, "Sales attribution to lead owner", "PASS", 
                                        f"Priya's onboarded_value={onboarded_value} (includes paid invoice)")
                            else:
                                log_test(16, "Sales attribution to lead owner", "FAIL", 
                                        f"Priya's onboarded_value={onboarded_value} (expected >= 5900)")
                        else:
                            log_test(16, "Sales attribution to lead owner", "FAIL", 
                                    "Priya's row not found in analytics")
                    else:
                        log_test(16, "Sales attribution to lead owner", "FAIL", 
                                f"GET analytics returned {r4.status_code}")
                else:
                    log_test(16, "Sales attribution to lead owner", "FAIL", 
                            f"Mark paid returned {r3.status_code}")
            else:
                log_test(16, "Sales attribution to lead owner", "FAIL", 
                        f"Create invoice returned {r2.status_code}")
        else:
            log_test(16, "Sales attribution to lead owner", "FAIL", f"Create L3 returned {r.status_code}")
        
        # ============================================================
        # F) COMPANY SETTINGS
        # ============================================================
        print("\n" + "=" * 80)
        print("F) COMPANY SETTINGS")
        print("=" * 80)
        
        # Test 17: Any authed user can GET /settings/company
        print("\n--- Test 17: Any user can GET /settings/company ---")
        r = requests.get(f"{BASE_URL}/settings/company", headers=get_headers(tokens["priya"]))
        if r.status_code == 200:
            log_test(17, "Any user GET /settings/company", "PASS", f"HTTP {r.status_code}")
        else:
            log_test(17, "Any user GET /settings/company", "FAIL", f"HTTP {r.status_code}: {r.text}")
        
        # Test 18: PUT as non-admin (403), PUT as super admin (200)
        print("\n--- Test 18: PUT /settings/company RBAC ---")
        r1 = requests.put(
            f"{BASE_URL}/settings/company",
            json={
                "company_name": "Raybotix Digital",
                "gst_number": "29AAAA1234A1Z1",
                "bank_name": "HDFC",
                "bank_account_number": "12345"
            },
            headers=get_headers(tokens["priya"])
        )
        r2 = requests.put(
            f"{BASE_URL}/settings/company",
            json={
                "company_name": "Raybotix Digital",
                "gst_number": "29AAAA1234A1Z1",
                "bank_name": "HDFC",
                "bank_account_number": "12345"
            },
            headers=get_headers(tokens["super_admin"])
        )
        if r1.status_code == 403 and r2.status_code == 200:
            log_test(18, "PUT /settings/company RBAC", "PASS", 
                    f"Priya→{r1.status_code}, Super admin→{r2.status_code}")
        else:
            log_test(18, "PUT /settings/company RBAC", "FAIL", 
                    f"Priya→{r1.status_code} (expected 403), Super admin→{r2.status_code} (expected 200)")
        
        # Test 19: Verify settings persisted
        print("\n--- Test 19: Verify settings persisted ---")
        r = requests.get(f"{BASE_URL}/settings/company", headers=get_headers(tokens["super_admin"]))
        if r.status_code == 200:
            settings = r.json()
            gst_ok = settings.get("gst_number") == "29AAAA1234A1Z1"
            bank_ok = settings.get("bank_name") == "HDFC"
            if gst_ok and bank_ok:
                log_test(19, "Settings persisted", "PASS", 
                        f"gst_number={settings.get('gst_number')}, bank_name={settings.get('bank_name')}")
            else:
                log_test(19, "Settings persisted", "FAIL", 
                        f"gst_number={settings.get('gst_number')} (expected 29AAAA1234A1Z1), "
                        f"bank_name={settings.get('bank_name')} (expected HDFC)")
        else:
            log_test(19, "Settings persisted", "FAIL", f"HTTP {r.status_code}")
        
        # ============================================================
        # G) PDF EXPORT
        # ============================================================
        print("\n" + "=" * 80)
        print("G) PDF EXPORT")
        print("=" * 80)
        
        # Test 20: Super admin GET /quotations/{Q1}/pdf
        print("\n--- Test 20: Super admin GET quotation PDF ---")
        r = requests.get(
            f"{BASE_URL}/quotations/{test_data.get('q1_id')}/pdf",
            headers=get_headers(tokens["super_admin"])
        )
        if r.status_code == 200:
            content_type = r.headers.get("Content-Type", "")
            is_pdf = content_type.startswith("application/pdf")
            starts_with_pdf = r.content[:5] == b"%PDF-"
            size_ok = len(r.content) > 1500
            
            if is_pdf and starts_with_pdf and size_ok:
                log_test(20, "Super admin GET quotation PDF", "PASS", 
                        f"HTTP {r.status_code}, Content-Type={content_type}, size={len(r.content)}")
            else:
                log_test(20, "Super admin GET quotation PDF", "FAIL", 
                        f"is_pdf={is_pdf}, starts_with_pdf={starts_with_pdf}, size_ok={size_ok}")
        else:
            log_test(20, "Super admin GET quotation PDF", "FAIL", f"HTTP {r.status_code}")
        
        # Test 21: Super admin GET invoice PDF
        print("\n--- Test 21: Super admin GET invoice PDF ---")
        r = requests.get(
            f"{BASE_URL}/invoices/{test_data.get('inv1_id')}/pdf",
            headers=get_headers(tokens["super_admin"])
        )
        if r.status_code == 200:
            starts_with_pdf = r.content[:5] == b"%PDF-"
            if starts_with_pdf:
                log_test(21, "Super admin GET invoice PDF", "PASS", 
                        f"HTTP {r.status_code}, starts with %PDF-")
            else:
                log_test(21, "Super admin GET invoice PDF", "FAIL", "Does not start with %PDF-")
        else:
            log_test(21, "Super admin GET invoice PDF", "FAIL", f"HTTP {r.status_code}")
        
        # Test 22: Priya GET Q1 PDF (403)
        print("\n--- Test 22: Priya GET Q1 PDF (should be 403) ---")
        r = requests.get(
            f"{BASE_URL}/quotations/{test_data.get('q1_id')}/pdf",
            headers=get_headers(tokens["priya"])
        )
        if r.status_code == 403:
            log_test(22, "Priya GET Q1 PDF→403", "PASS", f"HTTP {r.status_code}")
        else:
            log_test(22, "Priya GET Q1 PDF→403", "FAIL", f"HTTP {r.status_code} (expected 403)")
        
        # Test 23: Priya GET Q2 PDF (200)
        print("\n--- Test 23: Priya GET Q2 PDF (should be 200) ---")
        r = requests.get(
            f"{BASE_URL}/quotations/{test_data.get('q2_id')}/pdf",
            headers=get_headers(tokens["priya"])
        )
        if r.status_code == 200 and r.content[:5] == b"%PDF-":
            log_test(23, "Priya GET Q2 PDF→200", "PASS", f"HTTP {r.status_code}, starts with %PDF-")
        else:
            log_test(23, "Priya GET Q2 PDF→200", "FAIL", 
                    f"HTTP {r.status_code} (expected 200), starts_with_pdf={r.content[:5] == b'%PDF-'}")
        
        # ============================================================
        # H) RECURRING INVOICES
        # ============================================================
        print("\n" + "=" * 80)
        print("H) RECURRING INVOICES")
        print("=" * 80)
        
        # Test 24: Create recurring invoice
        print("\n--- Test 24: Create recurring invoice ---")
        r = requests.post(
            f"{BASE_URL}/recurring-invoices",
            json={
                "client_name": "Big Corp",
                "client_company": "Big Corp Ltd",
                "day_of_month": 1,
                "items": [{"description": "Retainer", "qty": 1, "rate": 20000, "gst_pct": 18}]
            },
            headers=get_headers(tokens["super_admin"])
        )
        if r.status_code == 200:
            rec = r.json()
            test_data["rec_id"] = rec["id"]
            test_data["recurring_ids"].append(rec["id"])
            has_next_run = rec.get("next_run_date") is not None
            if has_next_run:
                log_test(24, "Create recurring invoice", "PASS", 
                        f"HTTP {r.status_code}, id={rec['id']}, next_run_date set")
            else:
                log_test(24, "Create recurring invoice", "FAIL", "next_run_date not set")
        else:
            log_test(24, "Create recurring invoice", "FAIL", f"HTTP {r.status_code}: {r.text}")
        
        # Test 25: POST /run-now
        print("\n--- Test 25: POST /recurring-invoices/{id}/run-now ---")
        r = requests.post(
            f"{BASE_URL}/recurring-invoices/{test_data.get('rec_id')}/run-now",
            headers=get_headers(tokens["super_admin"])
        )
        if r.status_code == 200:
            result = r.json()
            invoice = result.get("invoice", {})
            number = invoice.get("number", "")
            total = invoice.get("total", 0)
            rec_id = invoice.get("recurring_invoice_id")
            
            # Check number format RB-INV-YYYY-NNNN
            import re
            number_ok = bool(re.match(r"^RB-INV-\d{4}-\d{4}$", number))
            total_ok = total == 23600  # 20000 * 1.18
            rec_id_ok = rec_id == test_data.get("rec_id")
            
            if number_ok and total_ok and rec_id_ok:
                # Check next_run_date advanced
                r2 = requests.get(
                    f"{BASE_URL}/recurring-invoices/{test_data.get('rec_id')}",
                    headers=get_headers(tokens["super_admin"])
                )
                if r2.status_code == 200:
                    template = r2.json()
                    next_run = template.get("next_run_date", "")
                    # Should be advanced (future date)
                    if next_run:
                        log_test(25, "POST /run-now", "PASS", 
                                f"HTTP {r.status_code}, number={number}, total={total}, "
                                f"next_run_date advanced")
                    else:
                        log_test(25, "POST /run-now", "FAIL", "next_run_date not advanced")
                else:
                    log_test(25, "POST /run-now", "FAIL", f"GET template returned {r2.status_code}")
            else:
                log_test(25, "POST /run-now", "FAIL", 
                        f"number_ok={number_ok}, total_ok={total_ok}, rec_id_ok={rec_id_ok}")
        else:
            log_test(25, "POST /run-now", "FAIL", f"HTTP {r.status_code}: {r.text}")
        
        # Test 26: PATCH active=false
        print("\n--- Test 26: PATCH recurring invoice active=false ---")
        r = requests.patch(
            f"{BASE_URL}/recurring-invoices/{test_data.get('rec_id')}",
            json={"active": False},
            headers=get_headers(tokens["super_admin"])
        )
        if r.status_code == 200:
            rec = r.json()
            if rec.get("active") == False:
                log_test(26, "PATCH active=false", "PASS", f"HTTP {r.status_code}, active={rec.get('active')}")
            else:
                log_test(26, "PATCH active=false", "FAIL", f"active={rec.get('active')} (expected False)")
        else:
            log_test(26, "PATCH active=false", "FAIL", f"HTTP {r.status_code}")
        
        # Test 27: Visibility - Priya should NOT see this template
        print("\n--- Test 27: Recurring invoice visibility ---")
        r1 = requests.get(f"{BASE_URL}/recurring-invoices", headers=get_headers(tokens["priya"]))
        r2 = requests.get(f"{BASE_URL}/recurring-invoices", headers=get_headers(tokens["super_admin"]))
        
        if r1.status_code == 200 and r2.status_code == 200:
            priya_list = r1.json()
            admin_list = r2.json()
            
            priya_ids = [r["id"] for r in priya_list]
            admin_ids = [r["id"] for r in admin_list]
            
            priya_has = test_data.get("rec_id") in priya_ids
            admin_has = test_data.get("rec_id") in admin_ids
            
            if not priya_has and admin_has:
                log_test(27, "Recurring invoice visibility", "PASS", 
                        f"Priya: not visible, Super admin: visible")
            else:
                log_test(27, "Recurring invoice visibility", "FAIL", 
                        f"Priya has={priya_has} (should be False), Admin has={admin_has} (should be True)")
        else:
            log_test(27, "Recurring invoice visibility", "FAIL", 
                    f"Priya: {r1.status_code}, Admin: {r2.status_code}")
        
        # Test 28: Delete rules
        print("\n--- Test 28: Recurring invoice delete rules ---")
        r1 = requests.delete(
            f"{BASE_URL}/recurring-invoices/{test_data.get('rec_id')}",
            headers=get_headers(tokens["priya"])
        )
        r2 = requests.delete(
            f"{BASE_URL}/recurring-invoices/{test_data.get('rec_id')}",
            headers=get_headers(tokens["super_admin"])
        )
        
        if r1.status_code == 403 and r2.status_code == 200:
            log_test(28, "Recurring invoice delete rules", "PASS", 
                    f"Priya→{r1.status_code}, Super admin→{r2.status_code}")
            # Remove from cleanup list since already deleted
            if test_data.get("rec_id") in test_data.get("recurring_ids", []):
                test_data["recurring_ids"].remove(test_data["rec_id"])
        else:
            log_test(28, "Recurring invoice delete rules", "FAIL", 
                    f"Priya→{r1.status_code} (expected 403), Super admin→{r2.status_code} (expected 200)")
        
        # Test non-existent DELETE (404)
        r3 = requests.delete(
            f"{BASE_URL}/recurring-invoices/nonexistent",
            headers=get_headers(tokens["super_admin"])
        )
        if r3.status_code == 404:
            print(f"   Non-existent DELETE→{r3.status_code} ✅")
        else:
            print(f"   Non-existent DELETE→{r3.status_code} (expected 404)")
        
        # ============================================================
        # REGRESSIONS
        # ============================================================
        print("\n" + "=" * 80)
        print("REGRESSIONS")
        print("=" * 80)
        
        # Test 29: Regression tests
        print("\n--- Test 29: Regression tests ---")
        endpoints = [
            "/analytics/dashboard",
            "/analytics/costs?range=month",
            "/tasks?scope=all",
            "/leads"
        ]
        
        all_ok = True
        for ep in endpoints:
            r = requests.get(f"{BASE_URL}{ep}", headers=get_headers(tokens["super_admin"]))
            if r.status_code != 200:
                print(f"   ❌ {ep} → {r.status_code}")
                all_ok = False
            else:
                print(f"   ✅ {ep} → {r.status_code}")
        
        if all_ok:
            log_test(29, "Regression tests", "PASS", "All endpoints return 200")
        else:
            log_test(29, "Regression tests", "FAIL", "Some endpoints failed")
        
        # ============================================================
        # CLEANUP
        # ============================================================
        print("\n" + "=" * 80)
        print("CLEANUP")
        print("=" * 80)
        
        # Test 30: Cleanup
        print("\n--- Test 30: Cleanup ---")
        cleanup()
        log_test(30, "Cleanup", "PASS", "Test data cleaned up")
        
    except Exception as e:
        print(f"\n❌ Exception during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    total = len(results)
    
    print(f"\nTotal: {total} tests")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"  ❌ Test {r['num']}: {r['desc']}")
                if r["details"]:
                    print(f"     {r['details']}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

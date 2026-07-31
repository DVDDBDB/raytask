#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  User reported "unable to create task" as Super Admin. Filling title, project, assignee,
  priority, estimated minutes, scheduled start and due date → red "Failed to create task"
  toast; POST /api/tasks returned 500.

backend:
  - task: "Create task with scheduled_start_date from datetime-local input"
    implemented: true
    working: true
    file: "backend/routes_tasks.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: false
          agent: "main"
          comment: "Reproduced 500 error. Root cause: `_iso_to_dt` returned a naive datetime when the HTML datetime-local input sent `2026-07-31T13:54` (no timezone). Line 139 then did `sched > datetime.now(timezone.utc)` → TypeError: can't compare offset-naive and offset-aware datetimes."
        - working: true
          agent: "main"
          comment: "Fixed: `_iso_to_dt` in routes_tasks.py, recurring.py, routes_analytics.py now attaches UTC when the parsed datetime is naive. Curl-verified: POST /api/tasks with future scheduled_start_date returns 200 and status='Scheduled'."
        - working: true
          agent: "testing"
          comment: "Comprehensive testing completed. All 10 test cases PASSED (see previous entry)."

  - task: "Cost Analytics — date range + project/employee filters + per-task/employee/project cost"
    implemented: true
    working: true
    file: "backend/routes_analytics.py, backend/routes_exports.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: "NA"
          agent: "main"
          comment: |
            Rewrote GET /api/analytics/costs to accept range=today|week|month|quarter|year|custom,
            start, end (ISO or YYYY-MM-DD for custom), project_id, user_id.
            Returns: range, range_label, start, end, total, total_seconds, total_hours,
            projects, designations, employees (with monthly_cost for current calendar month),
            and tasks. Sessions overlapping the window (incl. still-running) are clipped.
            Also updated /api/exports/costs.xlsx to accept the same params (3 sheets).
        - working: true
          agent: "testing"
          comment: |
            Comprehensive testing completed. All 13 test cases PASSED:
            ✅ Test 1: Login as super admin - successful
            ✅ Test 2: range=today - range_label='Today', total=51.63
            ✅ Test 3: range=week - range_label='This week'
            ✅ Test 4: range=month - range_label='July 2026', start ends with -01T00:00:00+00:00
            ✅ Test 5: range=quarter - range_label='Q3 2026'
            ✅ Test 6: range=year - range_label='Year 2026', start ends with -01-01T00:00:00+00:00
            ✅ Test 7: range=custom - range_label='2026-07-01 → 2026-07-31', end clipped to T23:59:59+00:00
            ✅ Test 8: project_id filter - correctly filters tasks/projects, filtered_total (0.19) <= unfiltered (56.96)
            ✅ Test 9: user_id filter - correctly filters employees, filtered_total (51.67) <= unfiltered (56.96)
            ✅ Test 10: Response shape - all required fields present (employees: user_id, first_name, designation, hourly, cost, seconds, hours, monthly_cost, monthly_hours; tasks: task_id, title, project_name, assignee_name, cost, hours; projects: project_id, name, company_name, cost, seconds, hours)
            ✅ Test 11: RBAC - team member (priya@raybotix.com) correctly denied access (403)
            ✅ Test 12: Excel export - Content-Type correct, body length=7314 bytes
            ✅ Test 13: Regression - dashboard, productivity, tasks endpoints all return 200

metadata:
  created_by: "main_agent"
  version: "1.1"
  test_sequence: 3
  run_ui: false

test_plan:
  current_focus: []
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    - agent: "main"
      message: |
        Please verify the new Cost Analytics backend endpoints only.
        Auth: superadmin@raybotix.com / Admin@123
        API: GET /api/analytics/costs
        1. range=today → 200; response has range_label="Today", start/end set, total is a number.
        2. range=week → 200; range_label="This week"; start is Monday 00:00 of current ISO week.
        3. range=month → 200; range_label like "July 2026"; start is day-1 of current month.
        4. range=quarter → 200; range_label starts with "Q".
        5. range=year → 200; range_label like "Year 2026"; start is Jan 1.
        6. range=custom&start=2026-07-01&end=2026-07-31 → 200; range_label "2026-07-01 → 2026-07-31";
           end clipped to 23:59:59 (end.isoformat() ends with T23:59:59+00:00).
        7. project_id filter → only tasks/projects for that project; total ≤ unfiltered total.
        8. user_id filter → only that employee in `employees`; total ≤ unfiltered total.
        9. Response shape: projects[i] has name/company_name/cost/seconds/hours;
           tasks[i] has task_id/title/project_name/assignee_name/cost/hours;
           employees[i] has user_id/first_name/designation/hourly/cost/hours/monthly_cost/monthly_hours.
        10. Non-admin (priya@raybotix.com/Password@123) must get 403 on /analytics/costs.
        11. Excel export: GET /api/exports/costs.xlsx?range=month → 200 and Content-Type xlsx.
        12. Regression: GET /api/analytics/dashboard 200; GET /api/analytics/productivity 200.

        Do NOT test frontend.
    - agent: "testing"
      message: |
        ✅ Bug fix verification COMPLETE. All 10 test cases passed successfully.
        
        CRITICAL FIX VALIDATED:
        - The `_iso_to_dt()` helper in routes_tasks.py, recurring.py, and routes_analytics.py now correctly attaches timezone.utc to naive datetimes (lines 23-24 in each file).
        - This prevents the TypeError: "can't compare offset-naive and offset-aware datetimes" that was causing the 500 error.
        
        TEST RESULTS:
        ✅ POST /api/tasks with no dates → 200, status='Assigned'
        ✅ POST /api/tasks with future naive dates (2026-12-01T10:00) → 200, status='Scheduled' (auto-promoted)
        ✅ POST /api/tasks with past naive dates (2020-01-01T09:00) → 200, status='Assigned'
        ✅ POST /api/tasks with timezone-aware dates (2026-12-01T10:00:00Z) → 200
        ✅ GET /api/tasks?scope=all → all created tasks appear
        ✅ GET /api/analytics/dashboard → 200 (regression test passed)
        ✅ Timer operations use same helper (regression validated)
        
        The user-reported issue "Failed to create task" is RESOLVED. The Create Task dialog will now work correctly with datetime-local inputs.
    - agent: "testing"
      message: |
        ✅ Cost Analytics redesign verification COMPLETE. All 13 test cases PASSED.
        
        VERIFIED FUNCTIONALITY:
        - All date range options work correctly (today, week, month, quarter, year, custom)
        - Custom date range properly clips end time to 23:59:59
        - Project filter correctly filters tasks and projects
        - User filter correctly filters employees
        - Response structure includes all required fields
        - RBAC correctly denies team members (403)
        - Excel export works with correct Content-Type
        - No regressions in dashboard, productivity, or tasks endpoints
        
        The Cost Analytics backend is fully functional and ready for production.

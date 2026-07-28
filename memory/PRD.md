# Raybotix Digital — PRD

## Original problem statement
Build a Digital Marketing Team Task Management PWA for **Raybotix Digital** (roles: Super Admin, Admin, Manager, Team Member) with task workflow, timers, handoffs, projects & cost tracking in ₹ INR, calendar, real-time messaging, notifications, analytics, staff management with signup approval, and PWA install support.

## Architecture (v1)
- **Frontend**: React (CRA/craco) + Tailwind + Shadcn UI + Recharts + Lucide icons. Routes guarded by role; PWA manifest + service worker.
- **Backend**: FastAPI + Motor (async MongoDB) + JWT auth (bcrypt). All endpoints prefixed with `/api`.
- **DB**: Users, Projects, Tasks, TimerSessions, Conversations, Messages, Notifications, ActivityLogs, TaskComments, Settings.
- **Auth**: JWT bearer tokens (30-day). Signup → pending; Super Admin approves & assigns role/designation.

## User personas
- **Super Admin (Aditya)** — full access incl. salaries, costs, roles, settings.
- **Admin / Manager (Neha)** — team task management, analytics.
- **Team Member (Priya, Rahul, Amit, Karan)** — own tasks, timer, messages.

## Implemented — Feb 2026 (v1)
- Signup → Super Admin approval flow, role/designation on approval
- JWT auth, session persistence, forgot/change password, profile update, theme (light/dark/system)
- Sidebar layout with role-based menus + PWA install button + notifications bell + theme toggle
- Task board with priority-first sort (Urgent → Medium → Low), tabbed views (All/Today/Upcoming/Planned/Overdue/Completed), filters (priority, status, project, assignee), search
- Task creation with project/assignee/priority/schedule/due/estimate/instructions
- **Task detail**: server-side timer (Start/Pause/Resume/Complete), workflow timeline (avatars + tooltip on hover), time by teammate, cost breakdown (admin only), reassignment, comments
- **Complete-task popup**: Mark Completed / Assign or Handoff (Continue Same Task | Create Next Task) — auto-closes on success
- Parent-child task linking (workflow preserved end-to-end)
- Reopen completed tasks with reason & new schedule
- Review approve / request changes / reopen
- Projects folder with monthly ₹ cost badge (Super Admin only)
- Calendar (month view, click-through)
- Messages (1-1 and group), polling-based real-time (4s), optimistic send, unread badges
- Notifications inbox + role-aware push
- Analytics: my daily hours, team productivity, employee costs
- Cost Analytics (Super Admin): monthly cost by project (bar) + by designation (pie)
- Staff Management: approve/reject signups, edit role/designation/salary, reset password, activate/deactivate
- Settings: company info, working hours/days, multiple timers switch, designations
- Activity Log (audit trail)
- PWA: manifest + custom SVG icons + install prompt + service worker

## Test credentials
See `/app/memory/test_credentials.md`.

## Implemented — Feb 2026 (v2)
- **Attachments Upload** — drop-zone on Create Task, Complete/Handoff (next task) and Task Detail. Files stored in Emergent Object Storage; metadata in `db.files`. Images preview inline via `?auth=<jwt>` URL; downloads via authenticated blob.
- **Live Messaging** — FastAPI WebSocket at `/api/ws?token=…`. In-process `ConnectionManager` broadcasts `{type:'message'}` to all conversation participants (incl. sender) instantly. Auto-reconnect + ping/pong keep-alive; live/reconnecting badge in UI.
- **Excel Exports** — openpyxl reports at `/api/exports/tasks.xlsx`, `/costs.xlsx` (Super Admin/Admin), `/productivity.xlsx`. Export buttons in Tasks, Cost Analytics, Analytics pages.
- **Recurring Tasks** — `recurrence: {enabled, frequency, next_run_at, last_run_at}` on Task. Background asyncio scheduler ticks every 5 min and clones templates to fresh tasks (daily/weekly/monthly). Toggle + frequency picker inside Create Task dialog; recurring badge on Task detail.

## Prioritized backlog (v3)
- **P0**: Email verification via Resend, mention `@name` auto-suggest, task tagging inside chat with rich preview
- **P1**: Drag-and-drop task rescheduling on calendar, CSV/PDF exports, weekly/monthly efficiency comparison charts, offline PWA caching
- **P2**: Salary history & bonus tracking, Slack/Telegram notification bridges, calendar-accurate monthly recurrence, streaming uploads for >25 MB files

## Known limitations
- Recurring "monthly" uses a 30-day step (not calendar-month accurate)
- `_tick` scheduler is single-process (fine for one backend pod; add distributed lock for horizontal scale)
- Uploads read into memory before size check (25 MB hard cap)

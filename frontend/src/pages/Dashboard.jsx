import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Link } from "react-router-dom";
import { UserAvatar } from "@/components/UserAvatar";
import { PriorityBadge, StatusBadge } from "@/components/Badges";
import { formatDate, formatDuration, formatINR } from "@/lib/format";
import { Clock, Flame, ListTodo, CheckCircle2, AlertTriangle, Calendar, Users, IndianRupee, Zap } from "lucide-react";

function Stat({ icon: Icon, label, value, sub, testId, tone = "default" }) {
  return (
    <div className="card-flat p-5 hover-lift" data-testid={testId}>
      <div className="flex items-center justify-between">
        <div className="text-overline">{label}</div>
        <Icon className={`w-4 h-4 ${
          tone === "primary" ? "text-primary" : "text-muted-foreground"
        }`} />
      </div>
      <div className="mt-3 text-3xl font-semibold tabular-nums" style={{ fontFamily: "Outfit" }}>{value}</div>
      {sub && <div className="text-[11px] text-muted-foreground mt-1">{sub}</div>}
    </div>
  );
}

export default function Dashboard() {
  const { user, isAdmin } = useAuth();
  const [stats, setStats] = useState(null);
  const [tasks, setTasks] = useState([]);
  useEffect(() => {
    api.get("/analytics/dashboard").then((r) => setStats(r.data)).catch(() => {});
    api.get("/tasks", { params: { scope: isAdmin ? "all" : "mine" } })
      .then((r) => setTasks(r.data.slice(0, 6))).catch(() => {});
  }, [isAdmin]);

  return (
    <div className="space-y-8" data-testid="dashboard-root">
      <div className="flex items-end justify-between gap-6 flex-wrap">
        <div>
          <div className="text-overline">Welcome back</div>
          <h1 className="text-4xl sm:text-5xl font-semibold" style={{ fontFamily: "Outfit" }}>
            Hey {user?.first_name},<br />
            <span className="text-muted-foreground text-2xl sm:text-3xl">
              here's your day at a glance.
            </span>
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <UserAvatar user={user} size={48} />
          <div>
            <div className="text-sm font-semibold">{user?.first_name} {user?.last_name}</div>
            <div className="text-[11px] uppercase tracking-widest text-muted-foreground">{user?.designation}</div>
          </div>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <Stat icon={ListTodo} label={isAdmin ? "Total tasks" : "My tasks"} value={stats?.total ?? "—"} testId="stat-total" />
        <Stat icon={Zap} label="In progress" value={stats?.in_progress ?? "—"} testId="stat-in-progress" />
        <Stat icon={Flame} label="Urgent" value={stats?.urgent ?? "—"} testId="stat-urgent" tone="primary" />
        <Stat icon={AlertTriangle} label="Overdue" value={stats?.overdue ?? "—"} testId="stat-overdue" />
        <Stat icon={CheckCircle2} label="Completed" value={stats?.completed ?? "—"} testId="stat-completed" />
        <Stat icon={Calendar} label="Planned" value={stats?.planned ?? "—"} testId="stat-planned" />
        <Stat icon={Clock} label="Today worked" value={formatDuration(stats?.today_seconds || 0)} sub="Since 00:00" testId="stat-today-seconds" />
        {isAdmin ? (
          <Stat icon={IndianRupee} label="Monthly cost" value={formatINR(stats?.monthly_cost || 0)} sub="This month · all projects" testId="stat-monthly-cost" tone="primary" />
        ) : (
          <Stat icon={Zap} label="Productivity" value={`${stats?.productivity_today ?? 0}%`} sub="vs expected work today" testId="stat-productivity" tone="primary" />
        )}
      </div>

      {isAdmin && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Stat icon={Users} label="Active users" value={stats?.active_users ?? "—"} testId="stat-active-users" />
          <Stat icon={Zap} label="Active timers" value={stats?.active_timers ?? "—"} testId="stat-active-timers" tone="primary" />
          <Stat icon={Clock} label="Team worked (week)" value={formatDuration(stats?.week_seconds || 0)} testId="stat-week-seconds" />
          <Stat icon={AlertTriangle} label="Waiting review" value={stats?.review ?? "—"} testId="stat-review" />
        </div>
      )}

      {/* Priority tasks */}
      <div>
        <div className="flex items-end justify-between mb-4">
          <div>
            <div className="text-overline">Top priority</div>
            <h2 className="text-2xl font-semibold" style={{ fontFamily: "Outfit" }}>
              What's up next
            </h2>
          </div>
          <Link to="/tasks" className="text-sm text-primary hover:underline">View all tasks →</Link>
        </div>
        <div className="grid gap-3">
          {tasks.length === 0 && (
            <div className="card-flat p-8 text-center text-sm text-muted-foreground">
              You're all clear — no active tasks right now.
            </div>
          )}
          {tasks.map((t) => (
            <Link
              to={`/tasks/${t.id}`}
              key={t.id}
              className="card-flat p-4 hover-lift flex items-center gap-4"
              data-testid={`dashboard-task-${t.id}`}
            >
              <PriorityBadge priority={t.priority} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                  <span>{t.project?.company_name || t.project?.name || "No project"}</span>
                  <span>•</span>
                  <span>Due {formatDate(t.due_date)}</span>
                </div>
                <div className="font-semibold truncate mt-0.5">{t.title}</div>
              </div>
              {t.assignee && (
                <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
                  <UserAvatar user={t.assignee} size={22} />
                  <span className="hidden sm:inline">{t.assignee.first_name}</span>
                </div>
              )}
              <StatusBadge status={t.status} />
            </Link>
          ))}
        </div>
      </div>

      <FollowUpWidget />
    </div>
  );
}

function FollowUpWidget() {
  const { user } = useAuth();
  const [items, setItems] = React.useState([]);
  const [loaded, setLoaded] = React.useState(false);
  React.useEffect(() => {
    const canSee = user?.role === "super_admin" || user?.role === "admin" || user?.crm_access;
    if (!canSee) { setLoaded(true); return; }
    api.get("/leads/follow-ups/upcoming", { params: { days: 14 } })
      .then((r) => setItems(r.data || []))
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, [user]);
  const canSee = user?.role === "super_admin" || user?.role === "admin" || user?.crm_access;
  if (!canSee || !loaded) return null;
  return (
    <div className="card-flat p-6" data-testid="dashboard-followups">
      <div className="flex items-end justify-between mb-3">
        <div>
          <div className="text-overline">CRM</div>
          <h3 className="text-xl font-semibold" style={{ fontFamily: "Outfit" }}>Pending follow-ups (next 14 days)</h3>
        </div>
        <Link to="/crm" className="text-xs text-primary hover:underline">Open CRM →</Link>
      </div>
      {items.length === 0 ? (
        <div className="text-sm text-muted-foreground">You&apos;re all caught up — no follow-ups scheduled.</div>
      ) : (
        <div className="divide-y divide-border">
          {items.map((l) => (
            <Link key={l.id} to="/crm" className="flex items-center justify-between py-2.5 hover:bg-secondary/30 -mx-2 px-2 rounded"
                  data-testid={`followup-${l.id}`}>
              <div className="min-w-0">
                <div className="font-semibold truncate">{l.name} {l.company && <span className="text-muted-foreground font-normal">· {l.company}</span>}</div>
                <div className="text-[11px] text-muted-foreground mt-0.5">
                  {l.stage} · {l.next_step || "No next step set"}
                </div>
              </div>
              <div className="text-[11px] text-muted-foreground shrink-0 ml-3">
                {formatDate(l.follow_up_date)}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

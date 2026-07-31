import React, { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { formatINR } from "@/lib/format";
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, CartesianGrid, Tooltip,
  PieChart, Pie, Cell,
} from "recharts";
import {
  IndianRupee, FileSpreadsheet, Clock, Users, FolderKanban,
  CalendarRange, Filter, X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { downloadFromPath } from "@/lib/uploads";

const COLORS = [
  "hsl(355 76% 56%)", "hsl(33 96% 44%)", "hsl(217 91% 60%)", "hsl(158 64% 42%)",
  "hsl(262 83% 58%)", "hsl(38 92% 50%)", "hsl(199 89% 48%)", "hsl(340 82% 52%)",
];

const RANGE_TABS = [
  { key: "today", label: "Today" },
  { key: "week", label: "This Week" },
  { key: "month", label: "This Month" },
  { key: "quarter", label: "This Quarter" },
  { key: "year", label: "This Year" },
  { key: "custom", label: "Custom" },
];

function formatHours(h) {
  if (!h) return "0h";
  if (h < 1) return `${Math.round(h * 60)}m`;
  return `${h.toFixed(1)}h`;
}

export default function CostAnalytics() {
  const [range, setRange] = useState("month");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [projectId, setProjectId] = useState("all");
  const [userId, setUserId] = useState("all");
  const [projects, setProjects] = useState([]);
  const [users, setUsers] = useState([]);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  // Load once: projects + users for filter selects
  useEffect(() => {
    api.get("/projects").then((r) => setProjects(r.data || []));
    api.get("/users").then((r) => setUsers(r.data || []));
  }, []);

  const fetchData = () => {
    const params = { range };
    if (range === "custom") {
      if (start) params.start = start;
      if (end) params.end = end;
    }
    if (projectId && projectId !== "all") params.project_id = projectId;
    if (userId && userId !== "all") params.user_id = userId;
    setLoading(true);
    api.get("/analytics/costs", { params })
      .then((r) => setData(r.data))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    // Auto-fetch when non-custom range or filters change.
    // For custom, wait until user has both dates (or clicks Apply).
    if (range !== "custom") fetchData();
    else if (start && end) fetchData();
  }, [range, projectId, userId]);

  const applyCustom = () => fetchData();

  const clearFilters = () => {
    setProjectId("all");
    setUserId("all");
  };

  const exportUrl = useMemo(() => {
    const p = new URLSearchParams();
    p.set("range", range);
    if (range === "custom") {
      if (start) p.set("start", start);
      if (end) p.set("end", end);
    }
    if (projectId !== "all") p.set("project_id", projectId);
    if (userId !== "all") p.set("user_id", userId);
    return `/exports/costs.xlsx?${p.toString()}`;
  }, [range, start, end, projectId, userId]);

  return (
    <div className="space-y-6" data-testid="cost-analytics-page">
      {/* Header */}
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="text-overline flex items-center gap-1.5">
            <CalendarRange className="w-3.5 h-3.5" />
            {data?.range_label || "…"}
          </div>
          <h1 className="text-3xl sm:text-4xl font-semibold" style={{ fontFamily: "Outfit" }}>
            Cost Analytics
          </h1>
        </div>
        <Button
          variant="outline"
          onClick={() => downloadFromPath(exportUrl, "raybotix-costs.xlsx")}
          className="gap-2 rounded-full"
          data-testid="export-costs-button"
        >
          <FileSpreadsheet className="w-4 h-4" /> Export Excel
        </Button>
      </div>

      {/* Filter bar */}
      <div className="card-flat p-4 space-y-4">
        <div className="flex flex-wrap gap-2">
          {RANGE_TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setRange(t.key)}
              data-testid={`range-tab-${t.key}`}
              className={`px-3.5 py-1.5 rounded-full text-sm font-medium transition ${
                range === t.key
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {range === "custom" && (
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1.5">
              <label className="text-[11px] text-muted-foreground font-medium">From</label>
              <Input
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                className="w-44"
                data-testid="custom-start"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[11px] text-muted-foreground font-medium">To</label>
              <Input
                type="date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                className="w-44"
                data-testid="custom-end"
              />
            </div>
            <Button onClick={applyCustom} disabled={!start || !end} className="rounded-full">
              Apply
            </Button>
          </div>
        )}

        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5">
            <label className="text-[11px] text-muted-foreground font-medium flex items-center gap-1">
              <FolderKanban className="w-3 h-3" /> Project
            </label>
            <Select value={projectId} onValueChange={setProjectId}>
              <SelectTrigger className="w-64" data-testid="filter-project">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All projects</SelectItem>
                {projects.map((p) => (
                  <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <label className="text-[11px] text-muted-foreground font-medium flex items-center gap-1">
              <Users className="w-3 h-3" /> Employee
            </label>
            <Select value={userId} onValueChange={setUserId}>
              <SelectTrigger className="w-64" data-testid="filter-user">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All employees</SelectItem>
                {users.map((u) => (
                  <SelectItem key={u.id} value={u.id}>
                    {u.first_name} {u.last_name || ""} — {u.designation}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {(projectId !== "all" || userId !== "all") && (
            <Button variant="ghost" onClick={clearFilters} className="gap-1.5" size="sm">
              <X className="w-3.5 h-3.5" /> Clear filters
            </Button>
          )}
        </div>
      </div>

      {/* Summary tiles */}
      {data && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Tile
            label="Total cost"
            value={
              <>
                <IndianRupee className="w-5 h-5 inline -mt-1" />
                {formatINR(data.total).replace("₹", "")}
              </>
            }
            testId="tile-total"
          />
          <Tile label="Total hours" value={formatHours(data.total_hours)} icon={<Clock className="w-4 h-4" />} testId="tile-hours" />
          <Tile label="Employees" value={data.employees.length} icon={<Users className="w-4 h-4" />} testId="tile-employees" />
          <Tile label="Projects" value={data.projects.length} icon={<FolderKanban className="w-4 h-4" />} testId="tile-projects" />
        </div>
      )}

      {loading && <div className="text-sm text-muted-foreground">Loading…</div>}

      {data && data.total_seconds === 0 && (
        <div className="card-flat p-10 text-center text-muted-foreground">
          <Filter className="w-6 h-6 mx-auto mb-2 opacity-60" />
          No logged time in <b>{data.range_label}</b> for the selected filters.
        </div>
      )}

      {data && data.total_seconds > 0 && (
        <>
          {/* Cost per Project + Cost share by role */}
          <div className="grid lg:grid-cols-2 gap-6">
            <div className="card-flat p-6" data-testid="section-projects">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <div className="text-overline">By project</div>
                  <h3 className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>Cost per project</h3>
                </div>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.projects} layout="vertical" margin={{ left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis type="number" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                    <YAxis dataKey="name" type="category" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} width={120} />
                    <Tooltip
                      contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }}
                      formatter={(v) => [formatINR(v), "Cost"]}
                    />
                    <Bar dataKey="cost" fill="hsl(var(--primary))" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 divide-y divide-border">
                {data.projects.map((p) => (
                  <div key={p.project_id} className="flex items-center justify-between py-2">
                    <div>
                      <div className="text-sm font-semibold">{p.name}</div>
                      <div className="text-[11px] text-muted-foreground">
                        {p.company_name} · {formatHours(p.hours)}
                      </div>
                    </div>
                    <div className="text-primary font-semibold tabular-nums">{formatINR(p.cost)}</div>
                  </div>
                ))}
                {data.projects.length === 0 && (
                  <div className="text-xs text-muted-foreground py-3">No project time in this range.</div>
                )}
              </div>
            </div>

            <div className="card-flat p-6" data-testid="section-designations">
              <div className="mb-4">
                <div className="text-overline">By designation</div>
                <h3 className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>Cost share by role</h3>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={data.designations} dataKey="cost" nameKey="designation" cx="50%" cy="50%" outerRadius={90} label={(e) => e.designation}>
                      {data.designations.map((_, idx) => (
                        <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v) => formatINR(v)} contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 divide-y divide-border">
                {data.designations.map((d, i) => (
                  <div key={d.designation} className="flex items-center justify-between py-2 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                      {d.designation}
                    </div>
                    <div className="text-primary font-semibold tabular-nums">{formatINR(d.cost)}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Cost per Employee */}
          <div className="card-flat p-6" data-testid="section-employees">
            <div className="mb-4 flex items-center justify-between flex-wrap gap-2">
              <div>
                <div className="text-overline">By employee</div>
                <h3 className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>
                  Cost per employee
                </h3>
              </div>
              <div className="text-[11px] text-muted-foreground">
                “Monthly work cost” always reflects the current calendar month.
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground text-[11px] uppercase tracking-wider">
                    <th className="py-2 pr-3">Employee</th>
                    <th className="py-2 pr-3">Designation</th>
                    <th className="py-2 pr-3 text-right">Hours (range)</th>
                    <th className="py-2 pr-3 text-right">Cost (range)</th>
                    <th className="py-2 pr-3 text-right">Hourly ₹</th>
                    <th className="py-2 pr-3 text-right">Monthly cost ₹</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {data.employees.map((e) => (
                    <tr key={e.user_id} data-testid={`emp-row-${e.user_id}`}>
                      <td className="py-2.5 pr-3">
                        <div className="flex items-center gap-2">
                          {e.avatar_url ? (
                            <img src={e.avatar_url} alt="" className="w-7 h-7 rounded-full object-cover" />
                          ) : (
                            <div className="w-7 h-7 rounded-full bg-secondary flex items-center justify-center text-[11px] font-semibold">
                              {(e.first_name || "?").charAt(0)}
                            </div>
                          )}
                          <div>
                            <div className="font-semibold">{e.first_name} {e.last_name}</div>
                          </div>
                        </div>
                      </td>
                      <td className="py-2.5 pr-3 text-muted-foreground">{e.designation}</td>
                      <td className="py-2.5 pr-3 text-right tabular-nums">{formatHours(e.hours)}</td>
                      <td className="py-2.5 pr-3 text-right text-primary font-semibold tabular-nums">
                        {formatINR(e.cost)}
                      </td>
                      <td className="py-2.5 pr-3 text-right tabular-nums">₹{e.hourly}</td>
                      <td className="py-2.5 pr-3 text-right tabular-nums">
                        {formatINR(e.monthly_cost)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {data.employees.length === 0 && (
                <div className="text-xs text-muted-foreground py-3">No employee activity in this range.</div>
              )}
            </div>
          </div>

          {/* Cost per Task */}
          <div className="card-flat p-6" data-testid="section-tasks">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-overline">By task</div>
                <h3 className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>
                  Cost per task
                </h3>
              </div>
              <div className="text-[11px] text-muted-foreground">Top 100</div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground text-[11px] uppercase tracking-wider">
                    <th className="py-2 pr-3">Task</th>
                    <th className="py-2 pr-3">Project</th>
                    <th className="py-2 pr-3">Assignee</th>
                    <th className="py-2 pr-3">Status</th>
                    <th className="py-2 pr-3 text-right">Hours</th>
                    <th className="py-2 pr-3 text-right">Cost ₹</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {data.tasks.slice(0, 100).map((t) => (
                    <tr key={t.task_id} data-testid={`task-row-${t.task_id}`}>
                      <td className="py-2.5 pr-3 font-semibold max-w-[280px] truncate" title={t.title}>{t.title}</td>
                      <td className="py-2.5 pr-3 text-muted-foreground">{t.project_name}</td>
                      <td className="py-2.5 pr-3 text-muted-foreground">{t.assignee_name}</td>
                      <td className="py-2.5 pr-3">
                        <span className="inline-flex items-center rounded-full bg-secondary px-2 py-0.5 text-[11px] font-medium text-secondary-foreground">
                          {t.status}
                        </span>
                      </td>
                      <td className="py-2.5 pr-3 text-right tabular-nums">{formatHours(t.hours)}</td>
                      <td className="py-2.5 pr-3 text-right text-primary font-semibold tabular-nums">
                        {formatINR(t.cost)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {data.tasks.length === 0 && (
                <div className="text-xs text-muted-foreground py-3">No task activity in this range.</div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function Tile({ label, value, icon, testId }) {
  return (
    <div className="card-flat p-5" data-testid={testId}>
      <div className="text-overline flex items-center gap-1.5">
        {icon}
        {label}
      </div>
      <div className="text-3xl font-semibold text-primary tabular-nums mt-1" style={{ fontFamily: "Outfit" }}>
        {value}
      </div>
    </div>
  );
}

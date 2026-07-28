import React, { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import TaskCard from "@/components/TaskCard";
import CreateTaskDialog from "@/components/CreateTaskDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus, Search, Filter, FileSpreadsheet } from "lucide-react";
import { TASK } from "@/constants/testIds";
import { downloadFromPath } from "@/lib/uploads";
import EmptyState from "@/components/EmptyState";

const VIEWS = [
  { key: "all", label: "All Tasks" },
  { key: "today", label: "Today" },
  { key: "upcoming", label: "Upcoming" },
  { key: "planned", label: "Planned" },
  { key: "overdue", label: "Overdue" },
  { key: "completed", label: "Completed" },
];

export default function Tasks() {
  const { user, isAdmin, canManageTasks } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [users, setUsers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [view, setView] = useState("all");
  const [search, setSearch] = useState("");
  const [priority, setPriority] = useState("");
  const [assignee, setAssignee] = useState("");
  const [status, setStatus] = useState("");
  const [projectId, setProjectId] = useState("");
  const [createOpen, setCreateOpen] = useState(false);

  const load = () => {
    api.get("/tasks", { params: {
      scope: isAdmin ? "all" : "mine",
      search, priority,
      assignee_id: assignee,
      status,
      project_id: projectId,
    }}).then((r) => setTasks(r.data));
  };

  useEffect(() => { load(); }, [search, priority, assignee, status, projectId, isAdmin]);
  useEffect(() => {
    api.get("/users").then((r) => setUsers(r.data));
    api.get("/projects").then((r) => setProjects(r.data));
  }, []);

  const filtered = useMemo(() => {
    const now = new Date();
    const startToday = new Date(); startToday.setHours(0,0,0,0);
    const endToday = new Date(); endToday.setHours(23,59,59,999);
    return tasks.filter((t) => {
      if (t.deleted) return false;
      const due = t.due_date ? new Date(t.due_date) : null;
      const sched = t.scheduled_start_date ? new Date(t.scheduled_start_date) : null;
      switch (view) {
        case "today":
          return (due && due >= startToday && due <= endToday) || (sched && sched >= startToday && sched <= endToday);
        case "upcoming":
          return sched && sched > endToday && !["Completed", "Cancelled"].includes(t.status);
        case "planned":
          return ["Planned", "Scheduled"].includes(t.status);
        case "overdue":
          return due && due < now && !["Completed", "Cancelled"].includes(t.status);
        case "completed":
          return t.status === "Completed";
        default:
          return true;
      }
    });
  }, [tasks, view]);

  return (
    <div className="space-y-6" data-testid="tasks-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="text-overline">Task workspace</div>
          <h1 className="text-3xl sm:text-4xl font-semibold" style={{ fontFamily: "Outfit" }}>
            {isAdmin ? "All Tasks" : "My Tasks"}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          {canManageTasks && (
            <Button
              variant="outline"
              onClick={() => downloadFromPath("/exports/tasks.xlsx", "raybotix-tasks.xlsx")}
              className="gap-2 rounded-full"
              data-testid="export-tasks-button"
            >
              <FileSpreadsheet className="w-4 h-4" /> Export
            </Button>
          )}
          <Button
            onClick={() => setCreateOpen(true)}
            className="gap-2 rounded-full"
            data-testid={TASK.createButton}
          >
            <Plus className="w-4 h-4" /> New task
          </Button>
        </div>
      </div>

      <Tabs value={view} onValueChange={setView}>
        <TabsList className="flex flex-wrap h-auto">
          {VIEWS.map((v) => (
            <TabsTrigger key={v.key} value={v.key} data-testid={`view-${v.key}`}>
              {v.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <div className="card-flat p-4 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[180px]">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Search title or description"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            data-testid="task-search-input"
          />
        </div>
        <Select value={priority || "all"} onValueChange={(v) => setPriority(v === "all" ? "" : v)}>
          <SelectTrigger className="w-[140px]" data-testid="filter-priority"><SelectValue placeholder="Priority" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All priority</SelectItem>
            <SelectItem value="Urgent">Urgent</SelectItem>
            <SelectItem value="Medium">Medium</SelectItem>
            <SelectItem value="Low">Low</SelectItem>
          </SelectContent>
        </Select>
        <Select value={status || "all"} onValueChange={(v) => setStatus(v === "all" ? "" : v)}>
          <SelectTrigger className="w-[160px]" data-testid="filter-status"><SelectValue placeholder="Status" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {["Planned","Scheduled","Assigned","In Progress","Paused","Waiting for Review","Completed","Reopened"].map((s) =>
              <SelectItem key={s} value={s}>{s}</SelectItem>
            )}
          </SelectContent>
        </Select>
        <Select value={projectId || "all"} onValueChange={(v) => setProjectId(v === "all" ? "" : v)}>
          <SelectTrigger className="w-[180px]" data-testid="filter-project"><SelectValue placeholder="Project" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All projects</SelectItem>
            {projects.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
          </SelectContent>
        </Select>
        {isAdmin && (
          <Select value={assignee || "all"} onValueChange={(v) => setAssignee(v === "all" ? "" : v)}>
            <SelectTrigger className="w-[180px]" data-testid="filter-assignee"><SelectValue placeholder="Employee" /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All employees</SelectItem>
              {users.filter((u) => u.status === "active").map((u) =>
                <SelectItem key={u.id} value={u.id}>{u.first_name} — {u.designation}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          icon={Filter}
          title="No tasks yet"
          description="Nothing matches your filters. Try widening the search or creating a new task."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((t) => <TaskCard key={t.id} task={t} showCost={isAdmin} />)}
        </div>
      )}

      <CreateTaskDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        users={users}
        projects={projects}
        onCreated={load}
      />
    </div>
  );
}

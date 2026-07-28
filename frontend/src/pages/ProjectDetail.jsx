import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import TaskCard from "@/components/TaskCard";
import CreateTaskDialog from "@/components/CreateTaskDialog";
import { Button } from "@/components/ui/button";
import { formatINR } from "@/lib/format";
import { IndianRupee, Plus, ArrowLeft } from "lucide-react";
import EmptyState from "@/components/EmptyState";

export default function ProjectDetail() {
  const { id } = useParams();
  const { canSeeCosts, canManageTasks } = useAuth();
  const [project, setProject] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [users, setUsers] = useState([]);
  const [projects, setProjects] = useState([]);
  const [createOpen, setCreateOpen] = useState(false);

  const load = () => {
    api.get(`/projects/${id}`).then((r) => setProject(r.data));
    api.get(`/tasks`, { params: { project_id: id, scope: "all" }}).then((r) => setTasks(r.data));
  };
  useEffect(() => {
    load();
    api.get("/users").then((r) => setUsers(r.data));
    api.get("/projects").then((r) => setProjects(r.data));
  }, [id]);

  if (!project) return null;

  return (
    <div className="space-y-6">
      <Link to="/projects" className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-primary">
        <ArrowLeft className="w-4 h-4" /> All projects
      </Link>
      <div className="flex items-end justify-between flex-wrap gap-6">
        <div>
          <div className="text-overline">{project.company_name || "Project"}</div>
          <h1 className="text-3xl sm:text-4xl font-semibold" style={{ fontFamily: "Outfit" }}>
            {project.name}
          </h1>
          <p className="mt-2 text-sm text-muted-foreground max-w-2xl">{project.description}</p>
        </div>
        <div className="flex items-center gap-3">
          {canSeeCosts && (
            <div className="text-right">
              <div className="text-overline">This month</div>
              <div className="text-2xl font-semibold text-primary tabular-nums" style={{ fontFamily: "Outfit" }}>
                <IndianRupee className="w-5 h-5 inline -mt-1" />{formatINR(project.monthly_cost || 0).replace("₹", "")}
              </div>
              <div className="text-[11px] text-muted-foreground">Total: {formatINR(project.total_cost || 0)}</div>
            </div>
          )}
          {canManageTasks && (
            <Button onClick={() => setCreateOpen(true)} className="gap-2 rounded-full" data-testid="project-task-create">
              <Plus className="w-4 h-4" /> New task
            </Button>
          )}
        </div>
      </div>

      {tasks.length === 0 ? (
        <EmptyState title="No tasks in this project yet" description="Create the first task to start tracking work in this folder." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {tasks.map((t) => <TaskCard key={t.id} task={t} showCost={canSeeCosts} />)}
        </div>
      )}

      <CreateTaskDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        users={users}
        projects={projects}
        defaultProjectId={id}
        onCreated={load}
      />
    </div>
  );
}

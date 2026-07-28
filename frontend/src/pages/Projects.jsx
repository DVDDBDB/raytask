import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { formatINR } from "@/lib/format";
import { toast } from "sonner";
import { FolderKanban, Plus, IndianRupee } from "lucide-react";
import EmptyState from "@/components/EmptyState";

export default function Projects() {
  const { canManageTasks, canSeeCosts } = useAuth();
  const [projects, setProjects] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", company_name: "", client_name: "", description: "" });

  const load = () => api.get("/projects").then((r) => setProjects(r.data));
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.name.trim()) { toast.error("Name is required"); return; }
    await api.post("/projects", form);
    toast.success("Project created");
    setOpen(false); setForm({ name: "", company_name: "", client_name: "", description: "" });
    load();
  };

  return (
    <div className="space-y-6" data-testid="projects-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="text-overline">Projects & folders</div>
          <h1 className="text-3xl sm:text-4xl font-semibold" style={{ fontFamily: "Outfit" }}>
            Client & campaign work
          </h1>
        </div>
        {canManageTasks && (
          <Button onClick={() => setOpen(true)} className="gap-2 rounded-full" data-testid="project-create-button">
            <Plus className="w-4 h-4" /> New project
          </Button>
        )}
      </div>

      {projects.length === 0 ? (
        <EmptyState icon={FolderKanban} title="No projects yet" description="Create your first client or internal project." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {projects.map((p) => (
            <Link
              key={p.id}
              to={`/projects/${p.id}`}
              className="card-flat p-5 hover-lift block"
              data-testid={`project-card-${p.id}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="text-overline mb-1">{p.company_name || "—"}</div>
                  <h3 className="text-lg font-semibold truncate" style={{ fontFamily: "Outfit" }}>{p.name}</h3>
                </div>
                {canSeeCosts && (
                  <div className="text-right shrink-0">
                    <div className="text-overline">This month</div>
                    <div className="inline-flex items-center gap-1 text-primary font-semibold">
                      <IndianRupee className="w-3.5 h-3.5" />
                      {formatINR(p.monthly_cost || 0).replace("₹", "")}
                    </div>
                  </div>
                )}
              </div>
              <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
                {p.description || "No description"}
              </p>
              <div className="flex items-center gap-4 mt-4 text-[12px] text-muted-foreground">
                <span>{p.total_tasks || 0} tasks</span>
                <span>·</span>
                <span>{p.completed_tasks || 0} completed</span>
                <span>·</span>
                <span>{p.pending_tasks || 0} pending</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle style={{ fontFamily: "Outfit" }}>New project</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5"><Label>Name</Label><Input data-testid="project-create-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div className="space-y-1.5"><Label>Company</Label><Input value={form.company_name} onChange={(e) => setForm({ ...form, company_name: e.target.value })} /></div>
            <div className="space-y-1.5"><Label>Client</Label><Input value={form.client_name} onChange={(e) => setForm({ ...form, client_name: e.target.value })} /></div>
            <div className="space-y-1.5"><Label>Description</Label><Textarea rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={create} data-testid="project-create-submit">Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

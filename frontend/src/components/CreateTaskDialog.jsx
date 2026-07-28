import React, { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import UserSelect from "@/components/UserSelect";
import api from "@/lib/api";
import { toast } from "sonner";
import { TASK } from "@/constants/testIds";

export default function CreateTaskDialog({ open, onOpenChange, users = [], projects = [], onCreated, defaultProjectId }) {
  const [form, setForm] = useState({
    title: "", description: "", project_id: defaultProjectId || "",
    assignee_id: "", priority: "Medium", status: "Assigned",
    scheduled_start_date: "", due_date: "",
    estimated_duration_minutes: 60, instructions: "",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm((f) => ({ ...f, project_id: defaultProjectId || f.project_id }));
    }
  }, [open, defaultProjectId]);

  const submit = async () => {
    if (!form.title.trim()) { toast.error("Task title is required"); return; }
    setSaving(true);
    try {
      const payload = { ...form };
      Object.keys(payload).forEach((k) => { if (payload[k] === "") delete payload[k]; });
      const r = await api.post("/tasks", payload);
      toast.success("Task created");
      onOpenChange(false);
      onCreated && onCreated(r.data);
      setForm({ title: "", description: "", project_id: "", assignee_id: "", priority: "Medium", status: "Assigned", scheduled_start_date: "", due_date: "", estimated_duration_minutes: 60, instructions: "" });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to create task");
    } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle style={{ fontFamily: "Outfit" }}>Create a task</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Title</Label>
            <Input
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="e.g. Create a reel for XYZ Company"
              data-testid={TASK.createTitle}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Description</Label>
            <Textarea
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Project</Label>
              <Select value={form.project_id || ""} onValueChange={(v) => setForm({ ...form, project_id: v })}>
                <SelectTrigger data-testid="task-create-project-select"><SelectValue placeholder="Select project" /></SelectTrigger>
                <SelectContent>
                  {projects.map((p) => (
                    <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Assignee</Label>
              <UserSelect
                users={users}
                value={form.assignee_id}
                onChange={(v) => setForm({ ...form, assignee_id: v })}
                testId="task-create-assignee-select"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Priority</Label>
              <Select value={form.priority} onValueChange={(v) => setForm({ ...form, priority: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="Urgent">Urgent</SelectItem>
                  <SelectItem value="Medium">Medium</SelectItem>
                  <SelectItem value="Low">Low</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Estimated (min)</Label>
              <Input
                type="number"
                value={form.estimated_duration_minutes}
                onChange={(e) => setForm({ ...form, estimated_duration_minutes: parseInt(e.target.value || "0") })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Scheduled start</Label>
              <Input
                type="datetime-local"
                value={form.scheduled_start_date}
                onChange={(e) => setForm({ ...form, scheduled_start_date: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Due date</Label>
              <Input
                type="datetime-local"
                value={form.due_date}
                onChange={(e) => setForm({ ...form, due_date: e.target.value })}
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Instructions</Label>
            <Textarea rows={2}
              value={form.instructions}
              onChange={(e) => setForm({ ...form, instructions: e.target.value })}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button
            onClick={submit}
            disabled={saving}
            data-testid={TASK.createSubmit}
          >
            {saving ? "Creating…" : "Create task"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

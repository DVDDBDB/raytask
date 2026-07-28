import React, { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import UserSelect from "@/components/UserSelect";
import AttachmentUploader from "@/components/AttachmentUploader";
import api from "@/lib/api";
import { toast } from "sonner";
import { TASK } from "@/constants/testIds";
import { Repeat } from "lucide-react";

const emptyForm = {
  title: "", description: "", project_id: "", assignee_id: "",
  priority: "Medium", status: "Assigned",
  scheduled_start_date: "", due_date: "",
  estimated_duration_minutes: 60, instructions: "",
  attachments: [],
  recurrence_enabled: false, recurrence_frequency: "weekly",
};

export default function CreateTaskDialog({ open, onOpenChange, users = [], projects = [], onCreated, defaultProjectId }) {
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setForm({ ...emptyForm, project_id: defaultProjectId || "" });
    }
  }, [open, defaultProjectId]);

  const submit = async () => {
    if (!form.title.trim()) { toast.error("Task title is required"); return; }
    setSaving(true);
    try {
      const {
        recurrence_enabled, recurrence_frequency, ...rest
      } = form;
      const payload = { ...rest };
      Object.keys(payload).forEach((k) => { if (payload[k] === "") delete payload[k]; });
      if (recurrence_enabled) {
        payload.recurrence = { enabled: true, frequency: recurrence_frequency };
      }
      const r = await api.post("/tasks", payload);
      toast.success(recurrence_enabled ? "Recurring task saved" : "Task created");
      onOpenChange(false);
      onCreated && onCreated(r.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to create task");
    } finally { setSaving(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[92vh] overflow-y-auto">
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
            <Textarea rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Project</Label>
              <Select value={form.project_id || ""} onValueChange={(v) => setForm({ ...form, project_id: v })}>
                <SelectTrigger data-testid="task-create-project-select"><SelectValue placeholder="Select project" /></SelectTrigger>
                <SelectContent>
                  {projects.map((p) => <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Assignee</Label>
              <UserSelect users={users} value={form.assignee_id} onChange={(v) => setForm({ ...form, assignee_id: v })} testId="task-create-assignee-select" />
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
              <Input type="number" value={form.estimated_duration_minutes} onChange={(e) => setForm({ ...form, estimated_duration_minutes: parseInt(e.target.value || "0") })} />
            </div>
            <div className="space-y-1.5">
              <Label>Scheduled start</Label>
              <Input type="datetime-local" value={form.scheduled_start_date} onChange={(e) => setForm({ ...form, scheduled_start_date: e.target.value })} />
            </div>
            <div className="space-y-1.5">
              <Label>Due date</Label>
              <Input type="datetime-local" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label>Instructions</Label>
            <Textarea rows={2} value={form.instructions} onChange={(e) => setForm({ ...form, instructions: e.target.value })} />
          </div>

          <div className="space-y-1.5">
            <Label>Attachments</Label>
            <AttachmentUploader
              value={form.attachments}
              onChange={(v) => setForm({ ...form, attachments: v })}
              testId="task-create-attachments"
              compact
            />
          </div>

          <div className="rounded-md border border-border p-3 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Repeat className="w-4 h-4 text-primary" />
                <div>
                  <div className="text-sm font-semibold">Recurring task</div>
                  <div className="text-[11px] text-muted-foreground">Auto-create a fresh copy on a schedule.</div>
                </div>
              </div>
              <Switch
                checked={form.recurrence_enabled}
                onCheckedChange={(v) => setForm({ ...form, recurrence_enabled: v })}
                data-testid="recurrence-switch"
              />
            </div>
            {form.recurrence_enabled && (
              <div className="space-y-1.5">
                <Label>Repeat every</Label>
                <Select value={form.recurrence_frequency} onValueChange={(v) => setForm({ ...form, recurrence_frequency: v })}>
                  <SelectTrigger data-testid="recurrence-frequency"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="daily">Day</SelectItem>
                    <SelectItem value="weekly">Week</SelectItem>
                    <SelectItem value="monthly">Month</SelectItem>
                  </SelectContent>
                </Select>
                <div className="text-[11px] text-muted-foreground">
                  The next instance is created automatically and assigned to the same teammate.
                </div>
              </div>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={submit} disabled={saving} data-testid={TASK.createSubmit}>
            {saving ? "Creating…" : "Create task"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

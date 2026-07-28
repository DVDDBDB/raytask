import React, { useEffect, useState } from "react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import UserSelect from "@/components/UserSelect";
import api from "@/lib/api";
import { toast } from "sonner";
import { TASK } from "@/constants/testIds";
import { CheckCircle2, ArrowRightCircle } from "lucide-react";

/**
 * Complete-task popup:
 *  - Mark as Completed
 *  - Assign / Handoff (with Continue Same Task | Create Next Task)
 *  Popup MUST auto-close on success.
 */
export default function CompleteTaskDialog({ open, onOpenChange, task, users = [], onDone }) {
  const [mode, setMode] = useState("complete");
  const [handoffMode, setHandoffMode] = useState("continue");
  const [nextAssignee, setNextAssignee] = useState("");
  const [remarks, setRemarks] = useState("");
  const [next, setNext] = useState({
    title: "", description: "", priority: "Medium",
    estimated_duration_minutes: 60, due_date: "", scheduled_start_date: "",
    instructions: "",
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open) {
      setMode("complete"); setHandoffMode("continue");
      setNextAssignee(""); setRemarks("");
      setNext({ title: "", description: "", priority: "Medium", estimated_duration_minutes: 60, due_date: "", scheduled_start_date: "", instructions: "" });
    }
  }, [open]);

  const submit = async () => {
    setSaving(true);
    try {
      if (mode === "complete") {
        await api.post(`/tasks/${task.id}/complete`);
        toast.success("Task marked as completed");
      } else {
        if (!nextAssignee) { toast.error("Select an employee"); setSaving(false); return; }
        const payload = {
          next_assignee_id: nextAssignee,
          remarks,
          create_next_task: handoffMode === "next",
          next_task: handoffMode === "next" ? {
            ...next,
            project_id: task.project?.id || task.project_id,
            assignee_id: nextAssignee,
          } : null,
        };
        await api.post(`/tasks/${task.id}/handoff`, payload);
        toast.success(handoffMode === "next" ? "Next task created & assigned" : "Task handed off");
      }
      onOpenChange(false);  // ⚠️ auto-close on success
      onDone && onDone();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        data-testid={TASK.completeDialog}
        className="max-w-lg"
      >
        <DialogHeader>
          <DialogTitle style={{ fontFamily: "Outfit" }}>Finish this task</DialogTitle>
          <DialogDescription>
            Choose how to close out <span className="font-medium text-foreground">{task?.title}</span>.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={mode} onValueChange={setMode} className="w-full">
          <TabsList className="grid grid-cols-2">
            <TabsTrigger value="complete" data-testid={TASK.completeMark}>
              <CheckCircle2 className="w-4 h-4 mr-2" /> Mark as Completed
            </TabsTrigger>
            <TabsTrigger value="handoff" data-testid={TASK.completeHandoff}>
              <ArrowRightCircle className="w-4 h-4 mr-2" /> Assign / Handoff
            </TabsTrigger>
          </TabsList>

          <TabsContent value="complete" className="pt-4 space-y-3">
            <p className="text-sm text-muted-foreground">
              This will stop the timer and mark the task as Completed. The workflow history is preserved.
            </p>
          </TabsContent>

          <TabsContent value="handoff" className="pt-4 space-y-4">
            <div className="space-y-1.5">
              <Label>Next employee</Label>
              <UserSelect
                users={users}
                value={nextAssignee}
                onChange={setNextAssignee}
                testId="handoff-user-select"
                placeholder="Choose an employee"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Handoff remarks</Label>
              <Textarea
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                placeholder="Notes for the next teammate…"
                data-testid="handoff-remarks-input"
              />
            </div>
            <RadioGroup value={handoffMode} onValueChange={setHandoffMode} className="grid grid-cols-2 gap-2">
              <label
                className={`cursor-pointer border rounded-md p-3 flex items-center gap-2 ${
                  handoffMode === "continue" ? "border-primary bg-primary/5" : "border-border"
                }`}
                data-testid={TASK.handoffContinue}
              >
                <RadioGroupItem value="continue" />
                <div>
                  <div className="text-sm font-semibold">Continue same task</div>
                  <div className="text-[11px] text-muted-foreground">Same task moves forward</div>
                </div>
              </label>
              <label
                className={`cursor-pointer border rounded-md p-3 flex items-center gap-2 ${
                  handoffMode === "next" ? "border-primary bg-primary/5" : "border-border"
                }`}
                data-testid={TASK.handoffCreateNext}
              >
                <RadioGroupItem value="next" />
                <div>
                  <div className="text-sm font-semibold">Create next task</div>
                  <div className="text-[11px] text-muted-foreground">Link a new sub-step</div>
                </div>
              </label>
            </RadioGroup>

            {handoffMode === "next" && (
              <div className="space-y-3 border-t border-border pt-3">
                <div className="space-y-1.5">
                  <Label>Next task title</Label>
                  <Input
                    value={next.title}
                    onChange={(e) => setNext({ ...next, title: e.target.value })}
                    placeholder="e.g. Edit reel"
                    data-testid="next-task-title-input"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label>Priority</Label>
                    <Select value={next.priority} onValueChange={(v) => setNext({ ...next, priority: v })}>
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
                      value={next.estimated_duration_minutes}
                      onChange={(e) => setNext({ ...next, estimated_duration_minutes: parseInt(e.target.value || "0") })}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Scheduled start</Label>
                    <Input type="datetime-local"
                      value={next.scheduled_start_date}
                      onChange={(e) => setNext({ ...next, scheduled_start_date: e.target.value })}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Due date</Label>
                    <Input type="datetime-local"
                      value={next.due_date}
                      onChange={(e) => setNext({ ...next, due_date: e.target.value })}
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label>Instructions</Label>
                  <Textarea rows={3}
                    value={next.instructions}
                    onChange={(e) => setNext({ ...next, instructions: e.target.value })}
                  />
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button
            onClick={submit}
            disabled={saving}
            data-testid={TASK.handoffSubmit}
          >
            {saving ? "Saving…" : (mode === "complete" ? "Mark Completed" : "Confirm Handoff")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

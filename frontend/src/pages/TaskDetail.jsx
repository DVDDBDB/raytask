import React, { useEffect, useState, useCallback } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import TaskTimer from "@/components/TaskTimer";
import CompleteTaskDialog from "@/components/CompleteTaskDialog";
import WorkflowTimeline from "@/components/WorkflowTimeline";
import { UserAvatar } from "@/components/UserAvatar";
import { PriorityBadge, StatusBadge } from "@/components/Badges";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { formatDate, formatDateTime, formatDuration, formatINR, userLabel } from "@/lib/format";
import { ArrowLeft, IndianRupee, ChevronRight, RotateCcw, MessagesSquare, FolderKanban, User } from "lucide-react";

export default function TaskDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { user, isAdmin, canManageTasks, canSeeCosts } = useAuth();
  const [task, setTask] = useState(null);
  const [users, setUsers] = useState([]);
  const [comment, setComment] = useState("");
  const [completeOpen, setCompleteOpen] = useState(false);
  const [reopenOpen, setReopenOpen] = useState(false);
  const [reopenForm, setReopenForm] = useState({ assignee_id: "", reason: "", priority: "Medium", due_date: "", scheduled_start_date: "", instructions: "" });
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewForm, setReviewForm] = useState({ action: "approve", comment: "" });

  const load = useCallback(async () => {
    try {
      const r = await api.get(`/tasks/${id}`);
      setTask(r.data);
    } catch { toast.error("Task not found"); nav("/tasks"); }
  }, [id, nav]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { api.get("/users").then((r) => setUsers(r.data)); }, []);

  // Poll every 5s to keep timer & workflow fresh
  useEffect(() => {
    const iv = setInterval(load, 8000);
    return () => clearInterval(iv);
  }, [load]);

  if (!task) return <div className="text-sm text-muted-foreground">Loading…</div>;

  const isAssignee = task.assignee_id === user?.id;
  const canControlTimer = isAssignee;
  const showCost = canSeeCosts && typeof task.cost === "number";

  const onStart = async () => { try { await api.post(`/tasks/${id}/start`); toast.success("Timer started"); load(); } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); } };
  const onPause = async () => { await api.post(`/tasks/${id}/pause`); toast.success("Timer paused"); load(); };

  const submitComment = async () => {
    if (!comment.trim()) return;
    await api.post(`/tasks/${id}/comments`, { body: comment });
    setComment("");
    load();
  };

  const submitReopen = async () => {
    if (!reopenForm.assignee_id || !reopenForm.reason) { toast.error("Assignee and reason are required"); return; }
    await api.post(`/tasks/${id}/reopen`, reopenForm);
    toast.success("Task reopened");
    setReopenOpen(false);
    load();
  };

  const submitReview = async () => {
    await api.post(`/tasks/${id}/review`, reviewForm);
    toast.success("Review recorded");
    setReviewOpen(false);
    load();
  };

  const changeAssignee = async (newId) => {
    await api.patch(`/tasks/${id}`, { assignee_id: newId });
    toast.success("Task reassigned");
    load();
  };

  // Group timer sessions by user
  const sessionsByUser = {};
  for (const s of task.timer_sessions || []) {
    (sessionsByUser[s.user_id] = sessionsByUser[s.user_id] || { user_id: s.user_id, first_name: s.user_first_name, designation: s.user_designation, seconds: 0 }).seconds += s.duration_seconds || 0;
  }

  return (
    <div className="space-y-6" data-testid="task-detail-page">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => nav(-1)} data-testid="back-button">
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div className="text-overline">Task</div>
        <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
        <div className="text-sm text-muted-foreground truncate">{task.project?.name || "No project"}</div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left column */}
        <div className="lg:col-span-2 space-y-6">
          <div className="card-flat p-6">
            <div className="flex flex-wrap items-center gap-2 mb-2">
              <PriorityBadge priority={task.priority} />
              <StatusBadge status={task.status} />
              {task.review_status && task.review_status !== "pending" && (
                <span className="text-[11px] uppercase tracking-widest text-muted-foreground">
                  Review: {task.review_status}
                </span>
              )}
            </div>
            <h1 className="text-2xl sm:text-3xl font-semibold" style={{ fontFamily: "Outfit" }}>
              {task.title}
            </h1>
            <p className="mt-3 text-sm text-muted-foreground whitespace-pre-line">
              {task.description || "No description provided."}
            </p>
            {task.instructions && (
              <div className="mt-4 border-l-2 border-primary/40 pl-4 text-sm">
                <div className="text-overline mb-1">Instructions</div>
                <p>{task.instructions}</p>
              </div>
            )}
          </div>

          {/* Workflow */}
          <div className="card-flat p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-overline">Workflow</div>
                <h3 className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>
                  Where the task has moved
                </h3>
              </div>
              {task.parent && (
                <Link to={`/tasks/${task.parent.id}`} className="text-[11px] text-primary hover:underline">
                  ← Parent: {task.parent.title}
                </Link>
              )}
            </div>
            <WorkflowTimeline workflow={task.workflow || []} sessions={task.timer_sessions || []} />
            {task.children?.length > 0 && (
              <div className="mt-4 border-t border-border pt-4 space-y-1">
                <div className="text-overline">Next tasks</div>
                {task.children.map((c) => (
                  <Link key={c.id} to={`/tasks/${c.id}`} className="text-sm text-primary hover:underline block">
                    → {c.title}
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Time breakdown per member */}
          <div className="card-flat p-6">
            <div className="text-overline mb-3">Time by teammate</div>
            <div className="space-y-2">
              {Object.values(sessionsByUser).length === 0 && (
                <div className="text-sm text-muted-foreground">No time logged yet.</div>
              )}
              {Object.values(sessionsByUser).map((s) => (
                <div key={s.user_id} className="flex items-center justify-between text-sm">
                  <div>
                    <span className="font-medium">{s.first_name}</span>
                    <span className="text-muted-foreground"> — {s.designation}</span>
                  </div>
                  <div className="tabular-nums timer-display">{formatDuration(s.seconds)}</div>
                </div>
              ))}
              <div className="pt-2 mt-2 border-t border-border flex items-center justify-between text-sm">
                <span className="font-semibold">Total team time</span>
                <span className="timer-display font-semibold">{formatDuration(task.total_team_seconds || 0)}</span>
              </div>
              {showCost && (
                <div className="flex items-center justify-between text-sm mt-1 text-primary">
                  <span className="inline-flex items-center gap-1.5"><IndianRupee className="w-3.5 h-3.5" /> Total task cost</span>
                  <span className="font-semibold">{formatINR(task.cost)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Comments */}
          <div className="card-flat p-6">
            <div className="text-overline mb-3">Comments</div>
            <div className="space-y-3 max-h-72 overflow-y-auto pr-2">
              {(task.comments || []).length === 0 && (
                <div className="text-sm text-muted-foreground">No comments yet.</div>
              )}
              {(task.comments || []).map((c) => (
                <div key={c.id} className="flex gap-3">
                  <UserAvatar user={{ first_name: c.user_first_name }} size={28} />
                  <div className="min-w-0 flex-1">
                    <div className="text-[12px] text-muted-foreground">
                      <span className="text-foreground font-semibold">{c.user_first_name}</span> — {c.user_designation} · {formatDateTime(c.created_at)}
                      {c.kind === "review" && <span className="ml-2 text-primary text-[10px] uppercase tracking-widest">review</span>}
                    </div>
                    <div className="text-sm">{c.body}</div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3 flex items-start gap-2">
              <Textarea
                rows={2}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Add a comment…"
                data-testid="task-comment-input"
              />
              <Button onClick={submitComment} data-testid="task-comment-submit">Send</Button>
            </div>
          </div>
        </div>

        {/* Right column */}
        <div className="space-y-6">
          {/* Timer */}
          {canControlTimer && (
            <TaskTimer
              task={task}
              onStart={onStart}
              onPause={onPause}
              onComplete={() => setCompleteOpen(true)}
              disabled={task.status === "Completed" || task.status === "Cancelled"}
            />
          )}

          {/* Meta */}
          <div className="card-flat p-5 space-y-4 text-sm">
            <div>
              <div className="text-overline mb-1">Assignee</div>
              {canManageTasks ? (
                <Select value={task.assignee_id || ""} onValueChange={changeAssignee}>
                  <SelectTrigger data-testid="reassign-select"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {users.filter((u) => u.status === "active").map((u) => (
                      <SelectItem key={u.id} value={u.id}>{userLabel(u)}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <div className="flex items-center gap-2">
                  <UserAvatar user={task.assignee} size={28} />
                  <div>
                    <div className="font-semibold">{task.assignee?.first_name}</div>
                    <div className="text-[11px] text-muted-foreground">{task.assignee?.designation}</div>
                  </div>
                </div>
              )}
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-overline mb-1">Priority</div>
                <PriorityBadge priority={task.priority} />
              </div>
              <div>
                <div className="text-overline mb-1">Status</div>
                <StatusBadge status={task.status} />
              </div>
              <div>
                <div className="text-overline mb-1">Scheduled</div>
                <div className="text-[13px]">{formatDate(task.scheduled_start_date)}</div>
              </div>
              <div>
                <div className="text-overline mb-1">Due</div>
                <div className="text-[13px]">{formatDate(task.due_date)}</div>
              </div>
              <div>
                <div className="text-overline mb-1">Estimate</div>
                <div className="text-[13px]">{task.estimated_duration_minutes} min</div>
              </div>
              <div>
                <div className="text-overline mb-1">Created</div>
                <div className="text-[13px]">{formatDate(task.created_at)}</div>
              </div>
            </div>
            {task.project && (
              <Link to={`/projects/${task.project.id}`} className="flex items-center gap-2 text-sm text-primary hover:underline">
                <FolderKanban className="w-4 h-4" /> {task.project.name}
              </Link>
            )}
            {task.creator && (
              <div className="flex items-center gap-2 text-[12px] text-muted-foreground">
                <User className="w-3.5 h-3.5" /> Created by {task.creator.first_name} — {task.creator.designation}
              </div>
            )}
          </div>

          {/* Admin actions */}
          {canManageTasks && (
            <div className="card-flat p-5 space-y-2">
              <div className="text-overline">Admin actions</div>
              {task.status === "Waiting for Review" && (
                <Button variant="outline" className="w-full gap-2" onClick={() => setReviewOpen(true)} data-testid="open-review-button">
                  <MessagesSquare className="w-4 h-4" /> Review task
                </Button>
              )}
              {task.status === "Completed" && (
                <Button variant="outline" className="w-full gap-2" onClick={() => setReopenOpen(true)} data-testid="open-reopen-button">
                  <RotateCcw className="w-4 h-4" /> Reopen task
                </Button>
              )}
            </div>
          )}
        </div>
      </div>

      <CompleteTaskDialog
        open={completeOpen}
        onOpenChange={setCompleteOpen}
        task={task}
        users={users}
        onDone={load}
      />

      {/* Reopen dialog */}
      <Dialog open={reopenOpen} onOpenChange={setReopenOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle style={{ fontFamily: "Outfit" }}>Reopen task</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label>Assign to</Label>
              <Select value={reopenForm.assignee_id} onValueChange={(v) => setReopenForm({ ...reopenForm, assignee_id: v })}>
                <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                <SelectContent>
                  {users.filter((u) => u.status === "active").map((u) => (
                    <SelectItem key={u.id} value={u.id}>{userLabel(u)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Reason</Label>
              <Textarea value={reopenForm.reason} onChange={(e) => setReopenForm({ ...reopenForm, reason: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Priority</Label>
                <Select value={reopenForm.priority} onValueChange={(v) => setReopenForm({ ...reopenForm, priority: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Urgent">Urgent</SelectItem>
                    <SelectItem value="Medium">Medium</SelectItem>
                    <SelectItem value="Low">Low</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Due date</Label>
                <Input type="datetime-local" value={reopenForm.due_date} onChange={(e) => setReopenForm({ ...reopenForm, due_date: e.target.value })} />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReopenOpen(false)}>Cancel</Button>
            <Button onClick={submitReopen} data-testid="submit-reopen-button">Reopen</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Review dialog */}
      <Dialog open={reviewOpen} onOpenChange={setReviewOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle style={{ fontFamily: "Outfit" }}>Review task</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <Select value={reviewForm.action} onValueChange={(v) => setReviewForm({ ...reviewForm, action: v })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="approve">Approve</SelectItem>
                <SelectItem value="request_changes">Request changes</SelectItem>
                <SelectItem value="reopen">Reopen</SelectItem>
              </SelectContent>
            </Select>
            <Textarea placeholder="Comment (optional)" value={reviewForm.comment} onChange={(e) => setReviewForm({ ...reviewForm, comment: e.target.value })} />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setReviewOpen(false)}>Cancel</Button>
            <Button onClick={submitReview} data-testid="submit-review-button">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

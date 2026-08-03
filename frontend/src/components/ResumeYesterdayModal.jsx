import React, { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Clock, Play, X, AlertCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import api from "@/lib/api";
import { toast } from "sonner";

const SESSION_KEY = "raybotix_resume_prompt_shown";

function humanDuration(seconds) {
  if (!seconds || seconds < 60) return `${Math.max(0, seconds || 0)}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h) return `${h}h ${m}m`;
  return `${m}m`;
}

export default function ResumeYesterdayModal() {
  const { user, token } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [busyId, setBusyId] = useState(null);

  useEffect(() => {
    // Show at most once per browser session per user login.
    if (!user || !token) return;
    const shownFor = sessionStorage.getItem(SESSION_KEY);
    if (shownFor === token) return;

    let cancelled = false;
    api.get("/tasks/resumable")
      .then((r) => {
        if (cancelled) return;
        const list = r.data || [];
        if (list.length > 0) {
          setTasks(list);
          setOpen(true);
        }
        sessionStorage.setItem(SESSION_KEY, token);
      })
      .catch(() => {
        // silent — never block the app
      });
    return () => { cancelled = true; };
  }, [user, token]);

  const resume = async (t) => {
    setBusyId(t.id);
    try {
      await api.post(`/tasks/${t.id}/resume`);
      toast.success(`Resumed "${t.title}"`);
      // remove from list, close if empty
      setTasks((prev) => {
        const rest = prev.filter((x) => x.id !== t.id);
        if (rest.length === 0) setOpen(false);
        return rest;
      });
      navigate(`/tasks/${t.id}`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Could not resume task");
    } finally {
      setBusyId(null);
    }
  };

  const startFresh = (t) => {
    // Just dismiss; task stays "Paused" until user manually starts it.
    setTasks((prev) => {
      const rest = prev.filter((x) => x.id !== t.id);
      if (rest.length === 0) setOpen(false);
      return rest;
    });
  };

  if (!open) return null;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2" style={{ fontFamily: "Outfit" }}>
            <AlertCircle className="w-5 h-5 text-primary" />
            Pick up where you left off?
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            Your timer was auto-stopped at <b>6 PM IST yesterday</b>. Resume the task
            to keep tracking time, or start fresh.
          </p>
          <ul className="mt-3 divide-y divide-border rounded-md border border-border">
            {tasks.map((t) => (
              <li key={t.id} className="p-3 flex items-center justify-between gap-3" data-testid={`resume-row-${t.id}`}>
                <div className="min-w-0">
                  <div className="font-semibold truncate" title={t.title}>{t.title}</div>
                  <div className="text-[11px] text-muted-foreground flex items-center gap-2 mt-0.5">
                    {t.project_name && <span>{t.project_name}</span>}
                    <span className="inline-flex items-center gap-1">
                      <Clock className="w-3 h-3" /> Ran {humanDuration(t.yesterday_seconds)} yesterday
                    </span>
                    <span className="inline-flex rounded-full bg-secondary text-secondary-foreground px-2 py-0.5 font-medium">
                      {t.priority}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => startFresh(t)}
                    data-testid={`resume-startfresh-${t.id}`}
                  >
                    Start fresh
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => resume(t)}
                    disabled={busyId === t.id}
                    className="gap-1.5"
                    data-testid={`resume-btn-${t.id}`}
                  >
                    <Play className="w-3.5 h-3.5" />
                    {busyId === t.id ? "Resuming…" : "Resume"}
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} className="gap-1.5">
            <X className="w-3.5 h-3.5" /> Dismiss all
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

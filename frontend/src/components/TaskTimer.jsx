import React, { useEffect, useState } from "react";
import { Play, Pause, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatTimer } from "@/lib/format";
import { TASK } from "@/constants/testIds";
import { cn } from "@/lib/utils";

export default function TaskTimer({ task, onStart, onPause, onComplete, disabled = false }) {
  const [tick, setTick] = useState(0);
  const active = task?.active_session && !task.active_session.ended_at;
  useEffect(() => {
    if (!active) return;
    const iv = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(iv);
  }, [active]);

  let seconds = task?.total_team_seconds || 0;
  if (active) {
    const started = new Date(task.active_session.started_at).getTime();
    seconds = (task.total_team_seconds || 0) + 0; // already includes running in enrich
    // small +tick offset for smoothness
  }
  // seconds already includes the running elapsed thanks to backend enrichment,
  // re-render every second only for display

  return (
    <div className={cn(
      "card-flat p-5 flex flex-col gap-4",
      active && "border-primary/50",
    )}>
      <div className="flex items-center justify-between">
        <div className="text-overline">Total Team Time</div>
        {active && (
          <div className="relative flex items-center gap-2 text-primary">
            <span className="relative w-2 h-2 rounded-full bg-primary">
              <span className="absolute inset-0 rounded-full bg-primary active-pulse" />
            </span>
            <span className="text-[11px] uppercase tracking-widest font-semibold">Live</span>
          </div>
        )}
      </div>
      <div
        className="timer-display text-4xl md:text-5xl font-bold tabular-nums leading-none"
        data-testid={TASK.timer}
      >
        {formatTimer(seconds + (active ? tick : 0))}
      </div>
      <div className="flex flex-wrap gap-2 pt-2">
        {!active ? (
          <Button
            onClick={onStart}
            disabled={disabled}
            data-testid={TASK.startButton}
            className="gap-2 rounded-full"
          >
            <Play className="w-4 h-4" /> Start Task
          </Button>
        ) : (
          <Button
            onClick={onPause}
            variant="outline"
            disabled={disabled}
            data-testid={TASK.pauseButton}
            className="gap-2 rounded-full"
          >
            <Pause className="w-4 h-4" /> Pause
          </Button>
        )}
        <Button
          variant="secondary"
          onClick={onComplete}
          disabled={disabled}
          data-testid={TASK.completeButton}
          className="gap-2 rounded-full"
        >
          <CheckCircle2 className="w-4 h-4" /> Complete Task
        </Button>
      </div>
    </div>
  );
}

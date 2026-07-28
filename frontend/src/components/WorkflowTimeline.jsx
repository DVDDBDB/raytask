import React from "react";
import { UserAvatar } from "@/components/UserAvatar";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { formatDateTime, formatDuration } from "@/lib/format";
import { CheckCircle2, Circle, PlayCircle, PauseCircle } from "lucide-react";

const statusIcon = (s) => {
  if (s === "completed") return CheckCircle2;
  if (s === "in_progress" || s === "started") return PlayCircle;
  if (s === "paused") return PauseCircle;
  return Circle;
};

export default function WorkflowTimeline({ workflow = [], sessions = [] }) {
  const secondsByUser = {};
  for (const s of sessions) {
    secondsByUser[s.user_id] = (secondsByUser[s.user_id] || 0) + (s.duration_seconds || 0);
  }
  if (!workflow.length) {
    return (
      <div className="text-sm text-muted-foreground italic">
        No workflow steps yet — the workflow begins when the task is assigned.
      </div>
    );
  }
  return (
    <TooltipProvider delayDuration={100}>
      <div className="flex flex-wrap items-center gap-2">
        {workflow.map((step, idx) => {
          const Icon = statusIcon(step.status);
          const secs = secondsByUser[step.user_id] || 0;
          return (
            <React.Fragment key={idx}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div
                    className={`relative flex flex-col items-center gap-1 hover-lift px-3 py-2 rounded-md border ${
                      step.status === "completed"
                        ? "bg-emerald-500/5 border-emerald-500/30"
                        : "bg-primary/5 border-primary/30"
                    }`}
                    data-testid={`workflow-step-${idx}`}
                  >
                    <div className="relative">
                      <UserAvatar user={step} size={36} />
                      <Icon className={`w-4 h-4 absolute -bottom-1 -right-1 bg-card rounded-full ${
                        step.status === "completed" ? "text-emerald-500" : "text-primary"
                      }`} />
                    </div>
                    <div className="text-[11px] font-semibold leading-tight">{step.first_name}</div>
                    <div className="text-[10px] text-muted-foreground leading-tight">{step.designation}</div>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="top" className="text-xs">
                  <div className="font-semibold">{step.first_name} — {step.designation}</div>
                  <div>Assigned: {formatDateTime(step.assigned_at)}</div>
                  {step.completed_at && <div>Completed: {formatDateTime(step.completed_at)}</div>}
                  <div>Time: {formatDuration(secs)}</div>
                  {step.handoff_remarks && (
                    <div className="max-w-[240px]">Note: {step.handoff_remarks}</div>
                  )}
                </TooltipContent>
              </Tooltip>
              {idx < workflow.length - 1 && (
                <div className="w-6 h-[2px] bg-border" />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </TooltipProvider>
  );
}

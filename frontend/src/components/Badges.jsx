import React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function PriorityBadge({ priority, className }) {
  const p = priority || "Medium";
  const cls =
    p === "Urgent" ? "badge-priority-urgent"
    : p === "Low" ? "badge-priority-low"
    : "badge-priority-medium";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 h-6 px-2 rounded text-[11px] uppercase tracking-widest font-semibold",
        cls, className,
      )}
      data-testid={`priority-badge-${p.toLowerCase()}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {p}
    </span>
  );
}

const statusColor = {
  "Planned": "bg-muted text-muted-foreground",
  "Scheduled": "bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/25",
  "Assigned": "bg-muted text-muted-foreground border border-border",
  "Not Started": "bg-muted text-muted-foreground border border-border",
  "In Progress": "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30",
  "Paused": "bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/25",
  "Waiting for Review": "bg-violet-500/10 text-violet-600 dark:text-violet-400 border border-violet-500/25",
  "Completed": "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/25",
  "Reopened": "bg-primary/10 text-primary border border-primary/25",
  "Overdue": "bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/25",
  "Cancelled": "bg-muted text-muted-foreground line-through",
};

export function StatusBadge({ status, className }) {
  const cls = statusColor[status] || "bg-muted text-muted-foreground";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 h-6 px-2 rounded text-[11px] uppercase tracking-widest font-semibold",
        cls, className,
      )}
      data-testid={`status-badge-${(status || "").toLowerCase().replace(/\s+/g, "-")}`}
    >
      {status}
    </span>
  );
}

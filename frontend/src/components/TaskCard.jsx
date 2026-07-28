import React from "react";
import { Link } from "react-router-dom";
import { UserAvatar } from "@/components/UserAvatar";
import { PriorityBadge, StatusBadge } from "@/components/Badges";
import { formatDate, formatDuration, formatINR } from "@/lib/format";
import { Clock, FolderKanban, Calendar, IndianRupee } from "lucide-react";

export default function TaskCard({ task, showCost = false }) {
  return (
    <Link
      to={`/tasks/${task.id}`}
      className="card-flat p-5 hover-lift block group"
      data-testid={`task-card-${task.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-overline text-[10px] mb-1.5">
            {task.project?.company_name || task.project?.name || "No project"}
          </div>
          <h3 className="text-base font-semibold leading-tight truncate group-hover:text-primary transition-colors" style={{ fontFamily: "Outfit" }}>
            {task.title}
          </h3>
        </div>
        <PriorityBadge priority={task.priority} />
      </div>
      <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
        {task.description || "No description"}
      </p>
      <div className="flex flex-wrap items-center gap-3 mt-4 text-[12px] text-muted-foreground">
        <StatusBadge status={task.status} />
        <span className="inline-flex items-center gap-1.5">
          <Calendar className="w-3.5 h-3.5" />
          Due {formatDate(task.due_date)}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          {formatDuration(task.total_team_seconds)}
        </span>
        {showCost && typeof task.cost === "number" && (
          <span className="inline-flex items-center gap-1.5 text-primary">
            <IndianRupee className="w-3.5 h-3.5" />{formatINR(task.cost).replace("₹", "")}
          </span>
        )}
      </div>
      {task.assignee && (
        <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border">
          <UserAvatar user={task.assignee} size={24} />
          <div className="text-[12px]">
            <span className="font-medium">{task.assignee.first_name}</span>
            <span className="text-muted-foreground"> — {task.assignee.designation}</span>
          </div>
        </div>
      )}
    </Link>
  );
}

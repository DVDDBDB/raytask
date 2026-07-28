import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { PriorityBadge } from "@/components/Badges";
import { Button } from "@/components/ui/button";
import { ChevronLeft, ChevronRight } from "lucide-react";

const DOW = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function CalendarPage() {
  const nav = useNavigate();
  const [tasks, setTasks] = useState([]);
  const [cursor, setCursor] = useState(new Date());

  useEffect(() => {
    api.get("/tasks", { params: { scope: "all" }}).then((r) => setTasks(r.data));
  }, []);

  const { grid, monthLabel } = useMemo(() => {
    const first = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
    const startDow = (first.getDay() + 6) % 7; // Monday-first
    const days = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0).getDate();
    const grid = [];
    for (let i = 0; i < startDow; i++) grid.push(null);
    for (let d = 1; d <= days; d++) grid.push(new Date(cursor.getFullYear(), cursor.getMonth(), d));
    return {
      grid,
      monthLabel: cursor.toLocaleDateString("en-IN", { month: "long", year: "numeric" }),
    };
  }, [cursor]);

  const tasksByDate = useMemo(() => {
    const map = {};
    for (const t of tasks) {
      const iso = t.due_date || t.scheduled_start_date;
      if (!iso) continue;
      const key = new Date(iso).toDateString();
      (map[key] = map[key] || []).push(t);
    }
    return map;
  }, [tasks]);

  const today = new Date().toDateString();

  return (
    <div className="space-y-6" data-testid="calendar-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <div className="text-overline">Calendar</div>
          <h1 className="text-3xl sm:text-4xl font-semibold" style={{ fontFamily: "Outfit" }}>
            {monthLabel}
          </h1>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="icon" onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))} data-testid="cal-prev">
            <ChevronLeft className="w-4 h-4" />
          </Button>
          <Button variant="outline" onClick={() => setCursor(new Date())} data-testid="cal-today">Today</Button>
          <Button variant="outline" size="icon" onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))} data-testid="cal-next">
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
      <div className="card-flat p-4">
        <div className="grid grid-cols-7 text-[11px] uppercase tracking-widest text-muted-foreground border-b border-border pb-2 mb-2">
          {DOW.map((d) => <div key={d} className="px-2">{d}</div>)}
        </div>
        <div className="grid grid-cols-7 gap-1">
          {grid.map((day, i) => {
            if (!day) return <div key={i} className="h-24 sm:h-28 rounded-md bg-muted/40" />;
            const key = day.toDateString();
            const dayTasks = tasksByDate[key] || [];
            const isToday = key === today;
            return (
              <div
                key={i}
                className={`h-24 sm:h-28 border rounded-md p-1.5 overflow-hidden ${
                  isToday ? "border-primary/50 bg-primary/5" : "border-border bg-card"
                }`}
              >
                <div className={`text-[11px] font-semibold ${isToday ? "text-primary" : "text-muted-foreground"}`}>
                  {day.getDate()}
                </div>
                <div className="mt-1 space-y-0.5">
                  {dayTasks.slice(0, 3).map((t) => (
                    <button
                      key={t.id}
                      className="w-full text-left text-[11px] px-1.5 py-0.5 rounded truncate hover:bg-muted transition-colors flex items-center gap-1"
                      onClick={() => nav(`/tasks/${t.id}`)}
                      data-testid={`cal-task-${t.id}`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                        t.priority === "Urgent" ? "bg-primary" : t.priority === "Medium" ? "bg-amber-500" : "bg-blue-500"
                      }`} />
                      {t.title}
                    </button>
                  ))}
                  {dayTasks.length > 3 && (
                    <div className="text-[10px] text-muted-foreground pl-1.5">+{dayTasks.length - 3} more</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

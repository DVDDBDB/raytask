import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { History } from "lucide-react";
import EmptyState from "@/components/EmptyState";

export default function ActivityLog() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get("/activity").then((r) => setItems(r.data)); }, []);
  return (
    <div className="space-y-4" data-testid="activity-page">
      <div>
        <div className="text-overline">Audit trail</div>
        <h1 className="text-3xl sm:text-4xl font-semibold" style={{ fontFamily: "Outfit" }}>Activity Log</h1>
      </div>
      {items.length === 0 ? (
        <EmptyState icon={History} title="No activity yet" description="Every action taken by staff appears here." />
      ) : (
        <div className="card-flat divide-y divide-border">
          {items.map((i) => (
            <div key={i.id} className="p-4 flex items-start gap-3 text-sm">
              <div className="w-2 h-2 rounded-full bg-primary mt-2 shrink-0" />
              <div className="flex-1 min-w-0">
                <div>
                  <span className="font-semibold">{i.actor_name || "System"}</span>
                  <span className="text-muted-foreground"> — {i.actor_designation}</span>
                  <span className="mx-2 text-muted-foreground">·</span>
                  <span className="text-primary">{i.action.replace(/_/g, " ")}</span>
                </div>
                <div className="text-[12px] text-muted-foreground">
                  {i.target_type}:{i.target_id?.slice(0,8)} · {formatDateTime(i.created_at)}
                  {i.reason ? ` · ${i.reason}` : ""}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { formatDateTime } from "@/lib/format";
import { Bell, Check } from "lucide-react";
import EmptyState from "@/components/EmptyState";

export default function NotificationsPage() {
  const nav = useNavigate();
  const [items, setItems] = useState([]);

  const load = () => api.get("/notifications").then((r) => setItems(r.data.items || []));
  useEffect(() => { load(); const iv = setInterval(load, 10000); return () => clearInterval(iv); }, []);

  const openNotif = async (n) => {
    if (!n.read) await api.post(`/notifications/${n.id}/read`);
    if (n.link_type === "task") nav(`/tasks/${n.link_id}`);
    else if (n.link_type === "conversation") nav(`/messages`);
    else if (n.link_type === "staff") nav(`/staff`);
    else nav(`/`);
  };

  const markAll = async () => { await api.post("/notifications/read-all"); load(); };

  return (
    <div className="space-y-6" data-testid="notifications-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="text-overline">Inbox</div>
          <h1 className="text-3xl sm:text-4xl font-semibold" style={{ fontFamily: "Outfit" }}>Notifications</h1>
        </div>
        <Button variant="outline" className="gap-2" onClick={markAll} data-testid="mark-all-read">
          <Check className="w-4 h-4" /> Mark all read
        </Button>
      </div>
      {items.length === 0 ? (
        <EmptyState icon={Bell} title="You're all caught up" description="No notifications right now." />
      ) : (
        <div className="card-flat divide-y divide-border">
          {items.map((n) => (
            <button
              key={n.id}
              onClick={() => openNotif(n)}
              data-testid={`notif-${n.id}`}
              className={`w-full text-left p-4 flex items-start gap-3 hover:bg-muted transition-colors ${
                !n.read ? "bg-primary/5" : ""
              }`}
            >
              <div className={`w-2 h-2 rounded-full mt-2 shrink-0 ${!n.read ? "bg-primary" : "bg-muted-foreground"}`} />
              <div className="min-w-0 flex-1">
                <div className="text-sm font-semibold truncate">{n.title}</div>
                <div className="text-[13px] text-muted-foreground truncate">{n.body}</div>
                <div className="text-[11px] text-muted-foreground mt-1">{formatDateTime(n.created_at)}</div>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

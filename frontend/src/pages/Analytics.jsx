import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { formatDuration, formatINR } from "@/lib/format";
import { UserAvatar } from "@/components/UserAvatar";
import { Button } from "@/components/ui/button";
import { downloadFromPath } from "@/lib/uploads";
import { FileSpreadsheet } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, CartesianGrid, Tooltip,
  LineChart, Line,
} from "recharts";

export default function Analytics() {
  const { user, isAdmin, canManageTasks } = useAuth();
  const [my, setMy] = useState(null);
  const [team, setTeam] = useState([]);

  useEffect(() => {
    api.get(`/analytics/employee/${user.id}`).then((r) => setMy(r.data));
    if (canManageTasks) {
      api.get("/analytics/productivity").then((r) => setTeam(r.data)).catch(() => {});
    }
  }, [user, canManageTasks]);

  return (
    <div className="space-y-8" data-testid="analytics-page">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <div className="text-overline">Analytics</div>
          <h1 className="text-3xl sm:text-4xl font-semibold" style={{ fontFamily: "Outfit" }}>
            {isAdmin ? "Team performance" : "My productivity"}
          </h1>
        </div>
        {canManageTasks && (
          <Button
            variant="outline"
            onClick={() => downloadFromPath("/exports/productivity.xlsx", "raybotix-productivity.xlsx")}
            className="gap-2 rounded-full"
            data-testid="export-productivity-button"
          >
            <FileSpreadsheet className="w-4 h-4" /> Export Excel
          </Button>
        )}
      </div>

      {/* My daily hours */}
      <div className="card-flat p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-overline">Last 30 days</div>
            <h3 className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>Daily work hours</h3>
          </div>
          <div className="text-right">
            <div className="text-overline">Total time</div>
            <div className="text-2xl font-semibold tabular-nums timer-display">{formatDuration(my?.total_seconds || 0)}</div>
          </div>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={my?.daily || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="date" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
              <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }}
                formatter={(v) => [`${v}h`, "Hours"]}
              />
              <Bar dataKey="hours" fill="hsl(var(--primary))" radius={[6,6,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="grid grid-cols-3 gap-3 mt-4">
          <div className="border border-border rounded-md p-3">
            <div className="text-overline">Completed</div>
            <div className="text-xl font-semibold">{my?.completed ?? 0}</div>
          </div>
          <div className="border border-border rounded-md p-3">
            <div className="text-overline">Reopened</div>
            <div className="text-xl font-semibold">{my?.reopened ?? 0}</div>
          </div>
          <div className="border border-border rounded-md p-3">
            <div className="text-overline">Overdue</div>
            <div className="text-xl font-semibold">{my?.overdue ?? 0}</div>
          </div>
        </div>
      </div>

      {canManageTasks && (
        <div className="card-flat p-6">
          <div className="mb-4">
            <div className="text-overline">This month</div>
            <h3 className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>Team productivity</h3>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={team}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis dataKey="first_name" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }} />
                <Bar dataKey="productivity" fill="hsl(var(--primary))" radius={[6,6,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-6 divide-y divide-border">
            {team.map((t) => (
              <div key={t.user_id} className="flex items-center gap-4 py-3" data-testid={`team-row-${t.user_id}`}>
                <UserAvatar user={t} size={32} />
                <div className="flex-1">
                  <div className="text-sm font-semibold">{t.first_name} — {t.designation}</div>
                  <div className="text-[11px] text-muted-foreground">{formatDuration(t.seconds)} logged this month</div>
                </div>
                <div className="text-right">
                  <div className="text-lg font-semibold text-primary tabular-nums">{t.productivity}%</div>
                  {isAdmin && <div className="text-[11px] text-muted-foreground">{formatINR(t.monthly_cost)}</div>}
                </div>
              </div>
            ))}
            {team.length === 0 && (
              <div className="text-sm text-muted-foreground py-6">No time logged yet this month.</div>
            )}
          </div>
        </div>
      )}

      <LeadAnalyticsSection />
    </div>
  );
}

function LeadAnalyticsSection() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  useEffect(() => {
    api.get("/analytics/leads").then((r) => setData(r.data)).catch(() => setData({ owners: [], totals: {} }));
  }, []);
  if (!data) return null;
  const hasAccess = user?.role === "super_admin" || user?.role === "admin" || user?.crm_access;
  if (!hasAccess) return null;
  const { owners = [], totals = {} } = data;
  return (
    <div className="space-y-4" data-testid="lead-analytics-section">
      <div>
        <div className="text-overline">CRM</div>
        <h2 className="text-2xl font-semibold" style={{ fontFamily: "Outfit" }}>Lead Analytics</h2>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Tile label="Contacted" value={totals.total_contacted || 0} />
        <Tile label="Converted" value={totals.total_converted || 0} />
        <Tile label="Pipeline value" value={formatINR(totals.pipeline_value || 0)} />
        <Tile label="Sales generated" value={formatINR(totals.sales_generated || 0)} highlight />
      </div>
      <div className="card-flat p-6">
        <h3 className="text-lg font-semibold mb-3" style={{ fontFamily: "Outfit" }}>Per owner</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={owners.map((o) => ({ name: o.owner_name, Contacted: o.contacted, Converted: o.converted, Lost: o.lost }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="name" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
              <YAxis tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }} />
              <Bar dataKey="Contacted" fill="hsl(217 91% 60%)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Converted" fill="hsl(158 64% 42%)" radius={[4, 4, 0, 0]} />
              <Bar dataKey="Lost" fill="hsl(0 74% 55%)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="overflow-x-auto mt-4">
          <table className="w-full text-sm">
            <thead className="text-[11px] uppercase text-muted-foreground">
              <tr>
                <th className="text-left py-2 pr-2">Owner</th>
                <th className="text-right py-2 px-2">Contacted</th>
                <th className="text-right py-2 px-2">Converted</th>
                <th className="text-right py-2 px-2">Conv. %</th>
                <th className="text-right py-2 px-2">Pipeline ₹</th>
                <th className="text-right py-2 pl-2">Sales ₹</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {owners.map((o) => (
                <tr key={o.owner_id}>
                  <td className="py-2 pr-2">
                    <div className="font-semibold">{o.owner_name}</div>
                    <div className="text-[11px] text-muted-foreground">{o.designation}</div>
                  </td>
                  <td className="py-2 px-2 text-right tabular-nums">{o.contacted}</td>
                  <td className="py-2 px-2 text-right tabular-nums">{o.converted}</td>
                  <td className="py-2 px-2 text-right tabular-nums">{o.conversion_rate}%</td>
                  <td className="py-2 px-2 text-right tabular-nums">{formatINR(o.pipeline_value)}</td>
                  <td className="py-2 pl-2 text-right tabular-nums text-primary font-semibold">{formatINR(o.onboarded_value)}</td>
                </tr>
              ))}
              {owners.length === 0 && (
                <tr><td colSpan={6} className="py-6 text-center text-muted-foreground">No lead activity yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Tile({ label, value, highlight }) {
  return (
    <div className={`card-flat p-4 ${highlight ? "ring-1 ring-primary/20" : ""}`}>
      <div className="text-overline">{label}</div>
      <div className={`text-2xl font-semibold tabular-nums mt-1 ${highlight ? "text-primary" : ""}`}
           style={{ fontFamily: "Outfit" }}>
        {value}
      </div>
    </div>
  );
}

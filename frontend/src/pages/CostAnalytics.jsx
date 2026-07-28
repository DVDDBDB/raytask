import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { formatINR } from "@/lib/format";
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import { IndianRupee, FileSpreadsheet } from "lucide-react";
import { Button } from "@/components/ui/button";
import { downloadFromPath } from "@/lib/uploads";

const COLORS = [
  "hsl(355 76% 56%)", "hsl(33 96% 44%)", "hsl(217 91% 60%)", "hsl(158 64% 42%)",
  "hsl(262 83% 58%)", "hsl(38 92% 50%)", "hsl(199 89% 48%)", "hsl(340 82% 52%)",
];

export default function CostAnalytics() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/analytics/costs").then((r) => setData(r.data)); }, []);
  if (!data) return null;
  return (
    <div className="space-y-6" data-testid="cost-analytics-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="text-overline">Month {data.month}</div>
          <h1 className="text-3xl sm:text-4xl font-semibold" style={{ fontFamily: "Outfit" }}>Cost Analytics</h1>
        </div>
        <div className="text-right space-y-2">
          <div>
            <div className="text-overline">Total this month</div>
            <div className="text-3xl font-semibold text-primary tabular-nums" style={{ fontFamily: "Outfit" }}>
              <IndianRupee className="w-6 h-6 inline -mt-1" />
              {formatINR(data.total).replace("₹", "")}
            </div>
          </div>
          <Button
            variant="outline"
            onClick={() => downloadFromPath("/exports/costs.xlsx", "raybotix-costs.xlsx")}
            className="gap-2 rounded-full"
            data-testid="export-costs-button"
          >
            <FileSpreadsheet className="w-4 h-4" /> Export Excel
          </Button>
        </div>
      </div>
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="card-flat p-6">
          <div className="mb-4">
            <div className="text-overline">By project</div>
            <h3 className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>Monthly cost per project</h3>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.projects} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis type="number" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} />
                <YAxis dataKey="name" type="category" tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }} width={120} />
                <Tooltip
                  contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }}
                  formatter={(v) => [formatINR(v), "Cost"]}
                />
                <Bar dataKey="cost" fill="hsl(var(--primary))" radius={[0,6,6,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 divide-y divide-border">
            {data.projects.map((p) => (
              <div key={p.project_id} className="flex items-center justify-between py-2">
                <div>
                  <div className="text-sm font-semibold">{p.name}</div>
                  <div className="text-[11px] text-muted-foreground">{p.company_name}</div>
                </div>
                <div className="text-primary font-semibold tabular-nums">{formatINR(p.cost)}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="card-flat p-6">
          <div className="mb-4">
            <div className="text-overline">By designation</div>
            <h3 className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>Cost share by role</h3>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data.designations} dataKey="cost" nameKey="designation" cx="50%" cy="50%" outerRadius={90} label={(e) => e.designation}>
                  {data.designations.map((_, idx) => (
                    <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => formatINR(v)} contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8 }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 divide-y divide-border">
            {data.designations.map((d, i) => (
              <div key={d.designation} className="flex items-center justify-between py-2 text-sm">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                  {d.designation}
                </div>
                <div className="text-primary font-semibold tabular-nums">{formatINR(d.cost)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

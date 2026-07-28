import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";

export default function Settings() {
  const [settings, setSettings] = useState(null);

  useEffect(() => { api.get("/settings").then((r) => setSettings(r.data)); }, []);
  if (!settings) return null;

  const set = (k, v) => setSettings({ ...settings, [k]: v });

  const save = async () => {
    await api.patch("/settings", settings);
    toast.success("Settings saved");
  };

  return (
    <div className="space-y-6" data-testid="settings-page">
      <div>
        <div className="text-overline">Company & app</div>
        <h1 className="text-3xl sm:text-4xl font-semibold" style={{ fontFamily: "Outfit" }}>Settings</h1>
      </div>

      <div className="card-flat p-6 space-y-4">
        <h3 className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>Company</h3>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-1.5"><Label>Company name</Label><Input value={settings.company_name || ""} onChange={(e) => set("company_name", e.target.value)} data-testid="setting-company-name" /></div>
          <div className="space-y-1.5"><Label>Address</Label><Input value={settings.address || ""} onChange={(e) => set("address", e.target.value)} /></div>
          <div className="space-y-1.5"><Label>Contact</Label><Input value={settings.contact || ""} onChange={(e) => set("contact", e.target.value)} /></div>
          <div className="space-y-1.5"><Label>Company logo URL</Label><Input value={settings.company_logo_url || ""} onChange={(e) => set("company_logo_url", e.target.value)} /></div>
        </div>
      </div>

      <div className="card-flat p-6 space-y-4">
        <h3 className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>Work rules</h3>
        <div className="grid md:grid-cols-3 gap-4">
          <div className="space-y-1.5"><Label>Currency</Label><Input value={settings.currency} onChange={(e) => set("currency", e.target.value)} /></div>
          <div className="space-y-1.5"><Label>Working days / month</Label><Input type="number" value={settings.working_days_per_month} onChange={(e) => set("working_days_per_month", parseInt(e.target.value || "0"))} /></div>
          <div className="space-y-1.5"><Label>Default hours / day</Label><Input type="number" value={settings.default_working_hours_per_day} onChange={(e) => set("default_working_hours_per_day", parseFloat(e.target.value || "0"))} /></div>
        </div>
        <div className="flex items-center justify-between border-t border-border pt-4">
          <div>
            <div className="font-semibold text-sm">Allow multiple active timers</div>
            <div className="text-[12px] text-muted-foreground">By default, an employee can only have one running task.</div>
          </div>
          <Switch
            checked={settings.allow_multiple_active_timers || false}
            onCheckedChange={(v) => set("allow_multiple_active_timers", v)}
            data-testid="setting-multi-timer-switch"
          />
        </div>
      </div>

      <div className="card-flat p-6 space-y-4">
        <h3 className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>Designations</h3>
        <div className="text-sm text-muted-foreground">One per line.</div>
        <textarea
          className="w-full rounded-md border border-input bg-transparent p-3 text-sm font-mono"
          rows={8}
          value={(settings.designations || []).join("\n")}
          onChange={(e) => set("designations", e.target.value.split("\n").map((s) => s.trim()).filter(Boolean))}
          data-testid="setting-designations"
        />
      </div>

      <Button onClick={save} className="rounded-full" data-testid="settings-save">Save changes</Button>
    </div>
  );
}

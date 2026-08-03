import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";

export default function Settings() {
  const [settings, setSettings] = useState(null);
  const [company, setCompany] = useState(null);

  useEffect(() => {
    api.get("/settings").then((r) => setSettings(r.data));
    api.get("/settings/company").then((r) => setCompany(r.data));
  }, []);
  if (!settings) return null;

  const set = (k, v) => setSettings({ ...settings, [k]: v });
  const setC = (k, v) => setCompany({ ...(company || {}), [k]: v });

  const save = async () => {
    await api.patch("/settings", settings);
    toast.success("Settings saved");
  };

  const saveCompany = async () => {
    try {
      await api.put("/settings/company", company || {});
      toast.success("Company & billing details saved");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to save company settings");
    }
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

      {company && (
        <div className="card-flat p-6 space-y-4" data-testid="company-billing-section">
          <div className="flex items-end justify-between flex-wrap gap-3">
            <div>
              <h3 className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>
                Company & GST — for Quotation / Invoice PDF
              </h3>
              <div className="text-[11px] text-muted-foreground">
                These details appear as header, GST, and bank block on every quotation & invoice PDF.
              </div>
            </div>
            <Button onClick={saveCompany} className="rounded-full" data-testid="save-company-button">
              Save company details
            </Button>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-1.5"><Label>Company name *</Label>
              <Input value={company.company_name || ""} onChange={(e) => setC("company_name", e.target.value)} data-testid="co-name" /></div>
            <div className="space-y-1.5"><Label>Tagline</Label>
              <Input value={company.tagline || ""} onChange={(e) => setC("tagline", e.target.value)} /></div>
            <div className="space-y-1.5"><Label>GSTIN</Label>
              <Input value={company.gst_number || ""} onChange={(e) => setC("gst_number", e.target.value)} data-testid="co-gst" /></div>
            <div className="space-y-1.5"><Label>PAN</Label>
              <Input value={company.pan_number || ""} onChange={(e) => setC("pan_number", e.target.value)} /></div>
            <div className="space-y-1.5 md:col-span-2"><Label>Address</Label>
              <Input value={company.address || ""} onChange={(e) => setC("address", e.target.value)} /></div>
            <div className="space-y-1.5"><Label>City</Label>
              <Input value={company.city || ""} onChange={(e) => setC("city", e.target.value)} /></div>
            <div className="space-y-1.5"><Label>State</Label>
              <Input value={company.state || ""} onChange={(e) => setC("state", e.target.value)} /></div>
            <div className="space-y-1.5"><Label>Pincode</Label>
              <Input value={company.pincode || ""} onChange={(e) => setC("pincode", e.target.value)} /></div>
            <div className="space-y-1.5"><Label>Phone</Label>
              <Input value={company.phone || ""} onChange={(e) => setC("phone", e.target.value)} /></div>
            <div className="space-y-1.5"><Label>Email</Label>
              <Input value={company.email || ""} onChange={(e) => setC("email", e.target.value)} /></div>
            <div className="space-y-1.5"><Label>Website</Label>
              <Input value={company.website || ""} onChange={(e) => setC("website", e.target.value)} /></div>
            <div className="space-y-1.5 md:col-span-2"><Label>Logo URL</Label>
              <Input value={company.logo_url || ""} onChange={(e) => setC("logo_url", e.target.value)} placeholder="https://…/raybotix-logo.png" /></div>
          </div>

          <div className="border-t border-border pt-4">
            <div className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">Bank details (shown on invoices)</div>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-1.5"><Label>Account name</Label>
                <Input value={company.bank_account_name || ""} onChange={(e) => setC("bank_account_name", e.target.value)} /></div>
              <div className="space-y-1.5"><Label>Account number</Label>
                <Input value={company.bank_account_number || ""} onChange={(e) => setC("bank_account_number", e.target.value)} data-testid="co-bank-account" /></div>
              <div className="space-y-1.5"><Label>IFSC</Label>
                <Input value={company.bank_ifsc || ""} onChange={(e) => setC("bank_ifsc", e.target.value)} /></div>
              <div className="space-y-1.5"><Label>Bank name</Label>
                <Input value={company.bank_name || ""} onChange={(e) => setC("bank_name", e.target.value)} /></div>
              <div className="space-y-1.5"><Label>Branch</Label>
                <Input value={company.bank_branch || ""} onChange={(e) => setC("bank_branch", e.target.value)} /></div>
              <div className="space-y-1.5"><Label>UPI ID</Label>
                <Input value={company.bank_upi || ""} onChange={(e) => setC("bank_upi", e.target.value)} /></div>
            </div>
          </div>

          <div className="border-t border-border pt-4 grid md:grid-cols-2 gap-4">
            <div className="space-y-1.5"><Label>Quotation footer</Label>
              <Input value={company.quotation_footer || ""} onChange={(e) => setC("quotation_footer", e.target.value)} /></div>
            <div className="space-y-1.5"><Label>Invoice footer</Label>
              <Input value={company.invoice_footer || ""} onChange={(e) => setC("invoice_footer", e.target.value)} /></div>
          </div>
        </div>
      )}
    </div>
  );
}

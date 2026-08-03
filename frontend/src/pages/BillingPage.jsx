import React, { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { formatINR } from "@/lib/format";
import BillingDialog, { STATUS_CHIP } from "@/components/BillingDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Plus, FileText, Receipt, ArrowRightLeft, Search, Repeat, Play, Pause, X } from "lucide-react";
import { toast } from "sonner";
import { useSearchParams, useNavigate } from "react-router-dom";

const QUOTATION_STATUSES = ["draft", "sent", "accepted", "rejected"];
const INVOICE_STATUSES = ["draft", "sent", "paid", "overdue"];

function StatusChip({ status }) {
  return (
    <span className={`text-[11px] uppercase font-semibold px-2 py-0.5 rounded-full ${STATUS_CHIP[status] || "bg-secondary"}`}>
      {status}
    </span>
  );
}

function Timeline({ doc, kind }) {
  const steps = kind === "invoice"
    ? [
        { key: "draft", label: "Draft", at: doc.created_at },
        { key: "sent", label: "Sent", at: doc.sent_at },
        { key: "paid", label: "Paid", at: doc.paid_at },
      ]
    : [
        { key: "draft", label: "Draft", at: doc.created_at },
        { key: "sent", label: "Sent", at: doc.sent_at },
        { key: doc.status === "rejected" ? "rejected" : "accepted",
          label: doc.status === "rejected" ? "Rejected" : "Accepted",
          at: doc.status === "rejected" ? doc.rejected_at : doc.accepted_at },
      ];
  return (
    <div className="flex items-center gap-1.5">
      {steps.map((s, i) => (
        <React.Fragment key={s.key + i}>
          <div className={`px-2 py-0.5 rounded-full text-[10px] ${s.at ? "bg-primary/15 text-primary font-semibold" : "bg-secondary/50 text-muted-foreground"}`}>
            {s.label}
          </div>
          {i < steps.length - 1 && (
            <div className={`h-px w-4 ${steps[i + 1]?.at ? "bg-primary" : "bg-border"}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
}

export default function BillingPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [tab, setTab] = useState("quotations");
  const [quotations, setQuotations] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [recurring, setRecurring] = useState([]);
  const [leads, setLeads] = useState([]);
  const [projects, setProjects] = useState([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogInitial, setDialogInitial] = useState(null);
  const [dialogKind, setDialogKind] = useState("quotation");
  const [recurringDialog, setRecurringDialog] = useState({ open: false, initial: null });

  const acceptedQuotations = useMemo(
    () => quotations.filter((q) => q.status === "accepted"),
    [quotations]
  );

  const load = async () => {
    try {
      const [qs, invs, rec, ls, ps] = await Promise.all([
        api.get("/quotations"),
        api.get("/invoices"),
        api.get("/recurring-invoices").catch(() => ({ data: [] })),
        api.get("/leads").catch(() => ({ data: [] })),
        api.get("/projects").catch(() => ({ data: [] })),
      ]);
      setQuotations(qs.data || []);
      setInvoices(invs.data || []);
      setRecurring(rec.data || []);
      setLeads(ls.data || []);
      setProjects(ps.data || []);
    } catch (e) { /* silent */ }
  };
  useEffect(() => { load(); }, []);

  // If ?leadId=... is present, auto-open a new quotation prefilled with that lead.
  useEffect(() => {
    const leadId = searchParams.get("leadId");
    if (!leadId || leads.length === 0) return;
    const l = leads.find((x) => x.id === leadId);
    if (!l) return;
    setDialogKind("quotation");
    setDialogInitial({
      client_name: l.name || "",
      client_company: l.company || "",
      client_email: l.email || "",
      client_phone: l.phone || "",
      client_address: "",
      items: [{ description: "", qty: 1, rate: 0, gst_pct: 18 }],
      notes: "",
      terms: "",
      valid_till: "",
      lead_id: l.id,
      project_id: null,
    });
    setDialogOpen(true);
    // Clear the param so a refresh doesn't reopen
    searchParams.delete("leadId");
    setSearchParams(searchParams, { replace: true });
  }, [leads]);

  const openNew = () => {
    if (tab === "recurring") {
      setRecurringDialog({ open: true, initial: null });
      return;
    }
    setDialogKind(tab === "invoices" ? "invoice" : "quotation");
    setDialogInitial(null);
    setDialogOpen(true);
  };
  const openEdit = (doc, kind) => {
    setDialogKind(kind);
    setDialogInitial(doc);
    setDialogOpen(true);
  };
  const onSaved = (data) => {
    if (dialogKind === "invoice") {
      setInvoices((prev) => {
        const i = prev.findIndex((x) => x.id === data.id);
        if (i === -1) return [data, ...prev];
        const next = [...prev]; next[i] = data; return next;
      });
    } else {
      setQuotations((prev) => {
        const i = prev.findIndex((x) => x.id === data.id);
        if (i === -1) return [data, ...prev];
        const next = [...prev]; next[i] = data; return next;
      });
    }
    setDialogInitial(data);
  };
  const onDeleted = (doc) => {
    if (dialogKind === "invoice") setInvoices((p) => p.filter((x) => x.id !== doc.id));
    else setQuotations((p) => p.filter((x) => x.id !== doc.id));
  };

  const convertToInvoice = async (q) => {
    try {
      const r = await api.post(`/invoices/from-quotation/${q.id}`);
      toast.success(`Invoice ${r.data.number} created`);
      setInvoices((prev) => [r.data, ...prev]);
      setTab("invoices");
      openEdit(r.data, "invoice");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to convert");
    }
  };

  const rows = useMemo(() => {
    const src = tab === "invoices" ? invoices : quotations;
    const s = search.trim().toLowerCase();
    return src.filter((d) => {
      if (statusFilter !== "all" && d.status !== statusFilter) return false;
      if (!s) return true;
      return [d.number, d.client_name, d.client_company, d.client_email]
        .some((x) => (x || "").toLowerCase().includes(s));
    });
  }, [tab, invoices, quotations, statusFilter, search]);

  const totals = useMemo(() => {
    const src = tab === "invoices" ? invoices : quotations;
    const totalCount = src.length;
    const totalValue = src.reduce((s, d) => s + (d.total || 0), 0);
    const won = tab === "invoices"
      ? src.filter((x) => x.status === "paid").reduce((s, d) => s + (d.total || 0), 0)
      : src.filter((x) => x.status === "accepted").reduce((s, d) => s + (d.total || 0), 0);
    const pending = tab === "invoices"
      ? src.filter((x) => x.status === "sent").reduce((s, d) => s + (d.total || 0), 0)
      : src.filter((x) => x.status === "sent").reduce((s, d) => s + (d.total || 0), 0);
    return { totalCount, totalValue, won, pending };
  }, [tab, invoices, quotations]);

  return (
    <div className="space-y-6" data-testid="billing-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="text-overline">Billing</div>
          <h1 className="text-3xl sm:text-4xl font-semibold" style={{ fontFamily: "Outfit" }}>
            Quotations & Invoices
          </h1>
        </div>
        {tab !== "recurring" && (
          <Button onClick={openNew} className="gap-1.5 rounded-full" data-testid="new-bill-button">
            <Plus className="w-4 h-4" /> New {tab === "invoices" ? "invoice" : "quotation"}
          </Button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => { setTab("quotations"); setStatusFilter("all"); }}
          data-testid="tab-quotations"
          className={`px-4 py-2 rounded-full text-sm font-medium inline-flex items-center gap-2 transition ${
            tab === "quotations" ? "bg-primary text-primary-foreground shadow" : "bg-secondary hover:bg-secondary/80"
          }`}
        >
          <FileText className="w-4 h-4" /> Quotations · {quotations.length}
        </button>
        <button
          onClick={() => { setTab("invoices"); setStatusFilter("all"); }}
          data-testid="tab-invoices"
          className={`px-4 py-2 rounded-full text-sm font-medium inline-flex items-center gap-2 transition ${
            tab === "invoices" ? "bg-primary text-primary-foreground shadow" : "bg-secondary hover:bg-secondary/80"
          }`}
        >
          <Receipt className="w-4 h-4" /> Invoices · {invoices.length}
        </button>
        <button
          onClick={() => { setTab("recurring"); setStatusFilter("all"); }}
          data-testid="tab-recurring"
          className={`px-4 py-2 rounded-full text-sm font-medium inline-flex items-center gap-2 transition ${
            tab === "recurring" ? "bg-primary text-primary-foreground shadow" : "bg-secondary hover:bg-secondary/80"
          }`}
        >
          <Repeat className="w-4 h-4" /> Recurring · {recurring.length}
        </button>
      </div>

      {/* Tiles */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Tile label={`${tab === "invoices" ? "Invoices" : "Quotations"} total`} value={totals.totalCount} />
        <Tile label="Total value" value={formatINR(totals.totalValue)} />
        <Tile label={tab === "invoices" ? "Paid" : "Accepted"} value={formatINR(totals.won)} highlight />
        <Tile label="Sent (awaiting)" value={formatINR(totals.pending)} />
      </div>

      {/* Filter bar */}
      <div className="card-flat p-3 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input placeholder="Search number, client, company or email…"
                 value={search} onChange={(e) => setSearch(e.target.value)}
                 className="pl-9" data-testid="bill-search" />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-44" data-testid="bill-status-filter"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {(tab === "invoices" ? INVOICE_STATUSES : QUOTATION_STATUSES).map((s) => (
              <SelectItem key={s} value={s}>{s.toUpperCase()}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {tab !== "recurring" && (
      <div className="card-flat p-0 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-secondary/40 text-[11px] uppercase text-muted-foreground">
            <tr>
              <th className="text-left px-4 py-2.5 w-36">Number</th>
              <th className="text-left px-4 py-2.5">Client</th>
              <th className="text-left px-4 py-2.5 w-24">Status</th>
              <th className="text-left px-4 py-2.5 w-64">Timeline</th>
              <th className="text-right px-4 py-2.5 w-32">Total ₹</th>
              <th className="px-4 py-2.5 w-32" />
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((d) => (
              <tr key={d.id} className="hover:bg-secondary/30 cursor-pointer" data-testid={`row-${d.id}`}
                  onClick={() => openEdit(d, tab === "invoices" ? "invoice" : "quotation")}>
                <td className="px-4 py-3 font-mono text-primary font-semibold">{d.number}</td>
                <td className="px-4 py-3">
                  <div className="font-semibold">{d.client_company || d.client_name}</div>
                  {d.client_company && d.client_name && (
                    <div className="text-[11px] text-muted-foreground">{d.client_name}</div>
                  )}
                </td>
                <td className="px-4 py-3"><StatusChip status={d.status} /></td>
                <td className="px-4 py-3"><Timeline doc={d} kind={tab === "invoices" ? "invoice" : "quotation"} /></td>
                <td className="px-4 py-3 text-right tabular-nums font-semibold text-primary">
                  {formatINR(d.total)}
                </td>
                <td className="px-4 py-3 text-right">
                  {tab === "quotations" && d.status === "accepted" && (
                    <Button size="sm" variant="outline" className="gap-1.5"
                            onClick={(e) => { e.stopPropagation(); convertToInvoice(d); }}
                            data-testid={`convert-${d.id}`}>
                      <ArrowRightLeft className="w-3.5 h-3.5" /> Invoice
                    </Button>
                  )}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center text-muted-foreground py-10 text-sm">
                  No {tab} yet. Click <b>New {tab === "invoices" ? "invoice" : "quotation"}</b> to create one.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      )}

      {tab === "recurring" && (
        <div className="card-flat p-4 text-xs text-muted-foreground">
          Recurring templates are created from an existing invoice — open any invoice and click <b>Save as recurring</b>.
        </div>
      )}

      {tab === "recurring" && (
        <RecurringList
          items={recurring}
          onEdit={(r) => setRecurringDialog({ open: true, initial: r })}
          onRun={async (r) => {
            try {
              const res = await api.post(`/recurring-invoices/${r.id}/run-now`);
              toast.success(`Draft invoice ${res.data.invoice.number} created`);
              await load();
            } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
          }}
          onToggle={async (r) => {
            try {
              await api.patch(`/recurring-invoices/${r.id}`, { active: !r.active });
              await load();
            } catch (e) { toast.error("Failed"); }
          }}
        />
      )}

      <BillingDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        kind={dialogKind}
        initial={dialogInitial}
        leads={leads}
        projects={projects}
        acceptedQuotations={acceptedQuotations}
        onSaved={onSaved}
        onDeleted={onDeleted}
      />

      <RecurringDialog
        open={recurringDialog.open}
        initial={recurringDialog.initial}
        leads={leads}
        projects={projects}
        onClose={() => setRecurringDialog({ open: false, initial: null })}
        onSaved={async () => { await load(); setRecurringDialog({ open: false, initial: null }); }}
      />
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



function RecurringList({ items, onEdit, onRun, onToggle }) {
  if (!items || items.length === 0) {
    return (
      <div className="card-flat p-10 text-center text-muted-foreground text-sm">
        <Repeat className="w-6 h-6 mx-auto mb-2 opacity-60" />
        No recurring templates yet. Create one to auto-generate a Draft invoice every month.
      </div>
    );
  }
  return (
    <div className="card-flat p-0 overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-secondary/40 text-[11px] uppercase text-muted-foreground">
          <tr>
            <th className="text-left px-4 py-2.5">Client</th>
            <th className="text-left px-4 py-2.5 w-24">Day</th>
            <th className="text-left px-4 py-2.5 w-40">Next run</th>
            <th className="text-left px-4 py-2.5 w-40">Last run</th>
            <th className="text-right px-4 py-2.5 w-28">Amount ₹</th>
            <th className="text-center px-4 py-2.5 w-20">Active</th>
            <th className="px-4 py-2.5 w-44" />
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {items.map((r) => {
            const total = (r.items || []).reduce((s, it) => {
              const lt = parseFloat(it.qty || 0) * parseFloat(it.rate || 0);
              return s + lt + lt * parseFloat(it.gst_pct || 0) / 100;
            }, 0);
            return (
              <tr key={r.id} className="hover:bg-secondary/30 cursor-pointer"
                  onClick={() => onEdit(r)}
                  data-testid={`recurring-row-${r.id}`}>
                <td className="px-4 py-3">
                  <div className="font-semibold">{r.client_company || r.client_name}</div>
                  {r.client_company && r.client_name && (
                    <div className="text-[11px] text-muted-foreground">{r.client_name}</div>
                  )}
                </td>
                <td className="px-4 py-3 font-mono">{r.day_of_month || 1}</td>
                <td className="px-4 py-3 text-muted-foreground">{(r.next_run_date || "").slice(0, 10) || "—"}</td>
                <td className="px-4 py-3 text-muted-foreground">{(r.last_run_at || "").slice(0, 10) || "Never"}</td>
                <td className="px-4 py-3 text-right tabular-nums font-semibold text-primary">
                  {formatINR(total)}
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`inline-flex text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full ${r.active ? "bg-emerald-500/10 text-emerald-600" : "bg-slate-500/10 text-slate-500"}`}>
                    {r.active ? "Active" : "Paused"}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="inline-flex gap-1">
                    <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); onToggle(r); }}
                            data-testid={`toggle-${r.id}`}
                            className={r.active ? "text-amber-600" : "text-emerald-600"}>
                      {r.active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    </Button>
                    <Button size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); onRun(r); }}
                            data-testid={`run-${r.id}`}>
                      Run now
                    </Button>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function RecurringDialog({ open, initial, leads, projects, onClose, onSaved }) {
  const emptyForm = {
    client_name: "", client_company: "", client_email: "", client_phone: "", client_address: "",
    items: [{ description: "", qty: 1, rate: 0, gst_pct: 18 }],
    notes: "", terms: "", day_of_month: 1, active: true, lead_id: null, project_id: null,
  };
  const [form, setForm] = React.useState(initial || emptyForm);
  React.useEffect(() => { setForm(initial || emptyForm); /* eslint-disable-next-line */ }, [initial, open]);
  if (!open) return null;

  const total = (form.items || []).reduce((s, it) => {
    const lt = parseFloat(it.qty || 0) * parseFloat(it.rate || 0);
    return s + lt + lt * parseFloat(it.gst_pct || 0) / 100;
  }, 0);
  const updateItem = (i, patch) => {
    const items = [...(form.items || [])];
    items[i] = { ...items[i], ...patch };
    setForm({ ...form, items });
  };
  const save = async () => {
    if (!form.client_name && !form.client_company) return toast.error("Add a client name");
    if (!form.items?.length) return toast.error("Add at least one line item");
    try {
      if (initial?.id) await api.patch(`/recurring-invoices/${initial.id}`, form);
      else await api.post("/recurring-invoices", form);
      toast.success(initial?.id ? "Saved" : "Recurring template created");
      onSaved();
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };
  const del = async () => {
    if (!initial?.id) return;
    if (!window.confirm("Delete this template?")) return;
    try { await api.delete(`/recurring-invoices/${initial.id}`); toast.success("Deleted"); onSaved(); }
    catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
         onClick={onClose}>
      <div className="bg-card rounded-lg shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col"
           onClick={(e) => e.stopPropagation()}>
        <div className="px-6 py-4 border-b border-border">
          <div className="text-lg font-semibold flex items-center gap-2" style={{ fontFamily: "Outfit" }}>
            <Repeat className="w-5 h-5 text-primary" />
            {initial?.id ? "Edit recurring template" : "New recurring template"}
          </div>
          <div className="text-[11px] text-muted-foreground mt-0.5">
            A Draft invoice will be auto-created every month on the chosen day.
          </div>
        </div>
        <div className="px-6 py-4 overflow-y-auto flex-1 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1"><label className="text-[11px] font-semibold">Client name</label>
              <input className="w-full h-9 rounded-md border border-border bg-background px-2 text-sm"
                     value={form.client_name} onChange={(e) => setForm({ ...form, client_name: e.target.value })} /></div>
            <div className="space-y-1"><label className="text-[11px] font-semibold">Company</label>
              <input className="w-full h-9 rounded-md border border-border bg-background px-2 text-sm"
                     value={form.client_company} onChange={(e) => setForm({ ...form, client_company: e.target.value })} /></div>
            <div className="space-y-1"><label className="text-[11px] font-semibold">Client email</label>
              <input className="w-full h-9 rounded-md border border-border bg-background px-2 text-sm"
                     value={form.client_email} onChange={(e) => setForm({ ...form, client_email: e.target.value })} /></div>
            <div className="space-y-1"><label className="text-[11px] font-semibold">Day of month (1–28)</label>
              <input type="number" min="1" max="28"
                     className="w-full h-9 rounded-md border border-border bg-background px-2 text-sm"
                     value={form.day_of_month || 1}
                     onChange={(e) => setForm({ ...form, day_of_month: parseInt(e.target.value || "1", 10) })} /></div>
          </div>
          <div>
            <div className="text-[11px] font-semibold mb-1">Line items</div>
            <div className="border border-border rounded-md overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-secondary/40 text-[10px] uppercase text-muted-foreground">
                  <tr>
                    <th className="text-left px-2 py-1.5">Description</th>
                    <th className="text-right px-2 py-1.5 w-16">Qty</th>
                    <th className="text-right px-2 py-1.5 w-24">Rate ₹</th>
                    <th className="text-right px-2 py-1.5 w-16">GST %</th>
                    <th className="w-6" />
                  </tr>
                </thead>
                <tbody>
                  {(form.items || []).map((it, idx) => (
                    <tr key={idx} className="border-t border-border">
                      <td className="px-1.5 py-1"><input className="w-full h-8 rounded border border-border bg-background px-2 text-sm"
                        value={it.description} onChange={(e) => updateItem(idx, { description: e.target.value })} /></td>
                      <td className="px-1.5 py-1"><input type="number" className="w-full h-8 rounded border border-border bg-background px-2 text-sm text-right"
                        value={it.qty} onChange={(e) => updateItem(idx, { qty: e.target.value })} /></td>
                      <td className="px-1.5 py-1"><input type="number" className="w-full h-8 rounded border border-border bg-background px-2 text-sm text-right"
                        value={it.rate} onChange={(e) => updateItem(idx, { rate: e.target.value })} /></td>
                      <td className="px-1.5 py-1"><input type="number" className="w-full h-8 rounded border border-border bg-background px-2 text-sm text-right"
                        value={it.gst_pct} onChange={(e) => updateItem(idx, { gst_pct: e.target.value })} /></td>
                      <td className="px-1"><Button size="icon" variant="ghost" className="h-7 w-7 text-red-600"
                        onClick={() => setForm({ ...form, items: form.items.filter((_, i) => i !== idx) })}>
                        <X className="w-3.5 h-3.5" /></Button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex items-center justify-between mt-2">
              <Button size="sm" variant="outline"
                      onClick={() => setForm({ ...form, items: [...(form.items || []), { description: "", qty: 1, rate: 0, gst_pct: 18 }] })}>
                <Plus className="w-3.5 h-3.5 mr-1" /> Add row
              </Button>
              <div className="text-sm text-muted-foreground">
                Estimated monthly total: <b className="text-primary tabular-nums">{formatINR(total)}</b>
              </div>
            </div>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" className="accent-primary" checked={!!form.active}
                   onChange={(e) => setForm({ ...form, active: e.target.checked })} />
            Active (auto-generate every month)
          </label>
        </div>
        <div className="px-6 py-3 border-t border-border flex justify-end gap-2">
          {initial?.id && (
            <Button variant="outline" className="text-red-600 mr-auto" onClick={del}>Delete</Button>
          )}
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={save} data-testid="recurring-save-button">Save</Button>
        </div>
      </div>
    </div>
  );
}

// Import X icon for RecurringDialog (already imported top-level via lucide-react)

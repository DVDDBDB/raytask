import React, { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { formatINR } from "@/lib/format";
import BillingDialog, { STATUS_CHIP } from "@/components/BillingDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Plus, FileText, Receipt, ArrowRightLeft, Search } from "lucide-react";
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
  const [leads, setLeads] = useState([]);
  const [projects, setProjects] = useState([]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogInitial, setDialogInitial] = useState(null);
  const [dialogKind, setDialogKind] = useState("quotation");

  const load = async () => {
    try {
      const [qs, invs, ls, ps] = await Promise.all([
        api.get("/quotations"),
        api.get("/invoices"),
        api.get("/leads").catch(() => ({ data: [] })),
        api.get("/projects").catch(() => ({ data: [] })),
      ]);
      setQuotations(qs.data || []);
      setInvoices(invs.data || []);
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
        <Button onClick={openNew} className="gap-1.5 rounded-full" data-testid="new-bill-button">
          <Plus className="w-4 h-4" /> New {tab === "invoices" ? "invoice" : "quotation"}
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
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

      <BillingDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        kind={dialogKind}
        initial={dialogInitial}
        leads={leads}
        projects={projects}
        onSaved={onSaved}
        onDeleted={onDeleted}
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

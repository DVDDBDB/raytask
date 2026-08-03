// Shared line-item editor used by Quotation & Invoice dialogs.
import React, { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { Plus, Trash2, Save, Send, IndianRupee, CheckCircle2, XCircle, Building2, Download, ArrowRightLeft, Repeat, Wallet } from "lucide-react";
import { formatINR } from "@/lib/format";
import { toast } from "sonner";
import api from "@/lib/api";
import { downloadFromPath } from "@/lib/uploads";

const STATUS_CHIP = {
  draft: "bg-slate-500/10 text-slate-600 dark:text-slate-300",
  sent: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  accepted: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  rejected: "bg-red-500/10 text-red-600 dark:text-red-400",
  paid: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  overdue: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
};

const emptyItem = { description: "", qty: 1, rate: 0, gst_pct: 18 };

const emptyForm = (kind) => ({
  client_name: "",
  client_company: "",
  client_email: "",
  client_phone: "",
  client_address: "",
  items: [{ ...emptyItem }],
  notes: "",
  terms: "",
  ...(kind === "invoice" ? { due_date: "" } : { valid_till: "" }),
  lead_id: null,
  project_id: null,
});

function computeTotals(items) {
  let subtotal = 0, gst = 0;
  for (const it of items) {
    const qty = parseFloat(it.qty || 0);
    const rate = parseFloat(it.rate || 0);
    const gstPct = parseFloat(it.gst_pct || 0);
    const lt = qty * rate;
    subtotal += lt;
    gst += lt * gstPct / 100;
  }
  return { subtotal, gst, total: subtotal + gst };
}

export default function BillingDialog({
  open, onOpenChange, kind, initial,
  leads = [], projects = [], onSaved, onDeleted,
}) {
  const isInvoice = kind === "invoice";
  const [form, setForm] = useState(initial || emptyForm(kind));
  const [busy, setBusy] = useState(false);
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [recurringOpen, setRecurringOpen] = useState(false);
  const isEdit = !!initial?.id;

  useEffect(() => {
    setForm(initial || emptyForm(kind));
  }, [initial, kind]);

  const { subtotal, gst, total } = computeTotals(form.items || []);

  const updateItem = (idx, patch) => {
    const items = [...(form.items || [])];
    items[idx] = { ...items[idx], ...patch };
    setForm({ ...form, items });
  };
  const addItem = () => setForm({ ...form, items: [...(form.items || []), { ...emptyItem }] });
  const removeItem = (idx) => setForm({ ...form, items: form.items.filter((_, i) => i !== idx) });

  const attachLead = (id) => {
    const l = leads.find((x) => x.id === id);
    setForm({
      ...form,
      lead_id: id === "none" ? null : id,
      client_name: form.client_name || l?.name || "",
      client_company: form.client_company || l?.company || "",
      client_email: form.client_email || l?.email || "",
      client_phone: form.client_phone || l?.phone || "",
    });
  };
  const attachProject = (id) => {
    const p = projects.find((x) => x.id === id);
    setForm({
      ...form,
      project_id: id === "none" ? null : id,
      client_name: form.client_name || p?.client_name || "",
      client_company: form.client_company || p?.company_name || "",
    });
  };

  const base = isInvoice ? "/invoices" : "/quotations";

  const save = async () => {
    if (!form.client_name && !form.client_company) {
      return toast.error("Add a client name or company");
    }
    if (!form.items?.length) return toast.error("Add at least one line item");
    setBusy(true);
    try {
      const r = isEdit
        ? await api.patch(`${base}/${initial.id}`, form)
        : await api.post(base, form);
      toast.success(isEdit ? "Saved" : `${isInvoice ? "Invoice" : "Quotation"} created`);
      onSaved(r.data);
      if (!isEdit) onOpenChange(false);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to save");
    } finally { setBusy(false); }
  };

  const send = async () => {
    if (!isEdit) return toast.error("Save the draft first");
    setBusy(true);
    try {
      const r = await api.post(`${base}/${initial.id}/send`);
      toast.success("Marked as sent — team notified in-app");
      onSaved(isInvoice ? r.data.invoice : r.data.quotation);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to send");
    } finally { setBusy(false); }
  };

  const setStatus = async (status) => {
    if (!isEdit) return;
    setBusy(true);
    try {
      const r = isInvoice
        ? (status === "paid"
            ? await api.post(`${base}/${initial.id}/mark-paid`)
            : await api.post(`${base}/${initial.id}/mark-status`, { status }))
        : await api.post(`${base}/${initial.id}/mark-status`, { status });
      toast.success(`Marked ${status}`);
      onSaved(r.data);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  };

  const convertToInvoice = async () => {
    if (!isEdit || isInvoice) return;
    try {
      const r = await api.post(`/invoices/from-quotation/${initial.id}`);
      toast.success(`Invoice ${r.data.number} created`);
      onOpenChange(false);
      onSaved(r.data);
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const convertToRecurring = async (day) => {
    if (!isEdit || !isInvoice) return;
    try {
      const r = await api.post(`/invoices/${initial.id}/to-recurring`, { day_of_month: day });
      toast.success(`Recurring template created (day ${day} each month)`);
      setRecurringOpen(false);
      onSaved({ ...initial });
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const recordPayment = async ({ amount, mode, received_on, reference, notes }) => {
    try {
      const r = await api.post(`/invoices/${initial.id}/record-payment`, {
        amount: parseFloat(amount || 0), mode, received_on, reference, notes,
      });
      toast.success("Payment recorded");
      setPaymentOpen(false);
      onSaved(r.data);
    } catch (e) { toast.error(e?.response?.data?.detail || "Failed"); }
  };

  const del = async () => {
    if (!isEdit) return;
    if (!window.confirm(`Delete ${form.number || "this " + kind}?`)) return;
    try {
      await api.delete(`${base}/${initial.id}`);
      toast.success("Deleted");
      onDeleted?.(initial);
      onOpenChange(false);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to delete");
    }
  };

  return (
    <>
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2" style={{ fontFamily: "Outfit" }}>
            {isInvoice ? "Invoice" : "Quotation"}
            {form.number && (
              <span className="text-primary font-semibold">· {form.number}</span>
            )}
            {form.status && (
              <span className={`text-[11px] uppercase font-semibold px-2 py-0.5 rounded-full ${STATUS_CHIP[form.status] || ""}`}>
                {form.status}
              </span>
            )}
          </DialogTitle>
        </DialogHeader>

        <div className="max-h-[68vh] overflow-y-auto pr-1 space-y-4">
          {/* Attach lead / project */}
          <div className="grid md:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Attach to lead (optional)</Label>
              <Select value={form.lead_id || "none"} onValueChange={attachLead}>
                <SelectTrigger><SelectValue placeholder="No lead" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">— none —</SelectItem>
                  {leads.map((l) => (
                    <SelectItem key={l.id} value={l.id}>
                      {l.name} {l.company ? `· ${l.company}` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Attach to project (optional)</Label>
              <Select value={form.project_id || "none"} onValueChange={attachProject}>
                <SelectTrigger><SelectValue placeholder="No project" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">— none —</SelectItem>
                  {projects.map((p) => (
                    <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Client */}
          <div className="grid md:grid-cols-2 gap-3">
            <div className="space-y-1.5"><Label>Client name</Label>
              <Input value={form.client_name} onChange={(e) => setForm({ ...form, client_name: e.target.value })} data-testid="bill-client-name" /></div>
            <div className="space-y-1.5"><Label>Company</Label>
              <Input value={form.client_company} onChange={(e) => setForm({ ...form, client_company: e.target.value })} /></div>
            <div className="space-y-1.5"><Label>Email</Label>
              <Input type="email" value={form.client_email} onChange={(e) => setForm({ ...form, client_email: e.target.value })} /></div>
            <div className="space-y-1.5"><Label>Phone</Label>
              <Input value={form.client_phone} onChange={(e) => setForm({ ...form, client_phone: e.target.value })} /></div>
            <div className="space-y-1.5 md:col-span-2"><Label>Address</Label>
              <Input value={form.client_address} onChange={(e) => setForm({ ...form, client_address: e.target.value })} /></div>
            <div className="space-y-1.5">
              <Label>{isInvoice ? "Due date" : "Valid till"}</Label>
              <Input type="date"
                     value={(isInvoice ? form.due_date : form.valid_till)?.slice(0, 10) || ""}
                     onChange={(e) => setForm({ ...form, [isInvoice ? "due_date" : "valid_till"]: e.target.value })}
                     data-testid="bill-date" />
            </div>
          </div>

          {/* Line items */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <Label className="text-sm font-semibold">Line items</Label>
              <Button size="sm" variant="outline" onClick={addItem} className="gap-1" data-testid="add-line-item">
                <Plus className="w-4 h-4" /> Add row
              </Button>
            </div>
            <div className="rounded-md border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-secondary/40 text-[11px] uppercase text-muted-foreground">
                  <tr>
                    <th className="text-left py-2 px-2">Description</th>
                    <th className="text-right py-2 px-2 w-20">Qty</th>
                    <th className="text-right py-2 px-2 w-32">Rate ₹</th>
                    <th className="text-right py-2 px-2 w-24">GST %</th>
                    <th className="text-right py-2 px-2 w-32">Line ₹</th>
                    <th className="w-8" />
                  </tr>
                </thead>
                <tbody>
                  {(form.items || []).map((it, idx) => {
                    const lt = (parseFloat(it.qty || 0) * parseFloat(it.rate || 0));
                    return (
                      <tr key={idx} className="border-t border-border" data-testid={`line-item-${idx}`}>
                        <td className="py-1.5 px-2">
                          <Input value={it.description}
                                 onChange={(e) => updateItem(idx, { description: e.target.value })}
                                 placeholder="Service / deliverable" />
                        </td>
                        <td className="py-1.5 px-2">
                          <Input className="text-right" type="number" value={it.qty}
                                 onChange={(e) => updateItem(idx, { qty: e.target.value })} />
                        </td>
                        <td className="py-1.5 px-2">
                          <Input className="text-right" type="number" value={it.rate}
                                 onChange={(e) => updateItem(idx, { rate: e.target.value })} />
                        </td>
                        <td className="py-1.5 px-2">
                          <Input className="text-right" type="number" value={it.gst_pct}
                                 onChange={(e) => updateItem(idx, { gst_pct: e.target.value })} />
                        </td>
                        <td className="py-1.5 px-2 text-right tabular-nums">{formatINR(lt)}</td>
                        <td className="py-1.5 pr-1">
                          <Button size="icon" variant="ghost"
                                  onClick={() => removeItem(idx)}
                                  className="h-7 w-7 text-red-600"><Trash2 className="w-4 h-4" /></Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="mt-3 grid grid-cols-2 md:grid-cols-3 gap-3">
              <div className="text-sm text-muted-foreground">
                Subtotal
                <div className="text-lg font-semibold text-foreground tabular-nums">{formatINR(subtotal)}</div>
              </div>
              <div className="text-sm text-muted-foreground">
                GST
                <div className="text-lg font-semibold text-foreground tabular-nums">{formatINR(gst)}</div>
              </div>
              <div className="text-sm text-muted-foreground">
                Total
                <div className="text-2xl font-bold text-primary tabular-nums flex items-center gap-1">
                  <IndianRupee className="w-5 h-5" /> {formatINR(total).replace("₹", "")}
                </div>
              </div>
            </div>
          </div>

          <div className="grid md:grid-cols-2 gap-3">
            <div className="space-y-1.5"><Label>Notes</Label>
              <Textarea rows={3} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} placeholder="Anything the client should know…" />
            </div>
            <div className="space-y-1.5"><Label>Terms</Label>
              <Textarea rows={3} value={form.terms} onChange={(e) => setForm({ ...form, terms: e.target.value })} placeholder="Payment terms, timelines, revisions…" />
            </div>
          </div>
        </div>

        <DialogFooter className="flex-wrap gap-2">
          {isEdit && (
            <Button variant="outline" className="gap-1.5" data-testid="bill-pdf-button"
                    onClick={() => downloadFromPath(`${base}/${initial.id}/pdf`, `${form.number || kind}.pdf`)}>
              <Download className="w-4 h-4" /> Download PDF
            </Button>
          )}
          {isEdit && form.status === "draft" && (
            <Button variant="outline" onClick={send} className="gap-1.5 mr-auto" data-testid="bill-send-button">
              <Send className="w-4 h-4" /> {isInvoice ? "Send invoice" : "Send quotation"}
            </Button>
          )}
          {isEdit && !isInvoice && (form.status === "sent" || form.status === "accepted") && (
            <Button variant="outline" onClick={convertToInvoice} className="gap-1.5" data-testid="convert-invoice-inline">
              <ArrowRightLeft className="w-4 h-4" /> Convert to invoice
            </Button>
          )}
          {isEdit && isInvoice && (
            <Button variant="outline" onClick={() => setRecurringOpen(true)} className="gap-1.5" data-testid="to-recurring-button">
              <Repeat className="w-4 h-4" /> Save as recurring
            </Button>
          )}
          {isEdit && isInvoice && form.status !== "paid" && (
            <Button variant="outline" onClick={() => setPaymentOpen(true)} className="gap-1.5 text-emerald-600" data-testid="record-payment-button">
              <Wallet className="w-4 h-4" /> Record payment
            </Button>
          )}
          {isEdit && !isInvoice && form.status === "sent" && (
            <>
              <Button variant="outline" onClick={() => setStatus("accepted")} className="gap-1.5 mr-auto text-emerald-600" data-testid="bill-accept-button">
                <CheckCircle2 className="w-4 h-4" /> Mark accepted
              </Button>
              <Button variant="outline" onClick={() => setStatus("rejected")} className="gap-1.5 text-red-600">
                <XCircle className="w-4 h-4" /> Mark rejected
              </Button>
            </>
          )}
          {isEdit && isInvoice && form.status === "sent" && (
            <Button variant="outline" onClick={() => setStatus("paid")} className="gap-1.5 mr-auto text-emerald-600" data-testid="bill-paid-button">
              <CheckCircle2 className="w-4 h-4" /> Mark paid
            </Button>
          )}
          {isEdit && (
            <Button variant="outline" className="text-red-600 gap-1.5" onClick={del}>
              <Trash2 className="w-4 h-4" /> Delete
            </Button>
          )}
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={save} disabled={busy} className="gap-1.5" data-testid="bill-save-button">
            <Save className="w-4 h-4" /> {busy ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <PaymentDialog
      open={paymentOpen}
      invoice={initial}
      onClose={() => setPaymentOpen(false)}
      onRecord={recordPayment}
    />
    <RecurringDayDialog
      open={recurringOpen}
      onClose={() => setRecurringOpen(false)}
      onSave={convertToRecurring}
    />
    </>
  );
}

function PaymentDialog({ open, invoice, onClose, onRecord }) {
  const [amount, setAmount] = useState("");
  const [mode, setMode] = useState("UPI");
  const [receivedOn, setReceivedOn] = useState(new Date().toISOString().slice(0, 10));
  const [reference, setReference] = useState("");
  const [notes, setNotes] = useState("");
  useEffect(() => {
    if (open) {
      const outstanding = Math.max(0, (invoice?.total || 0) - (invoice?.amount_paid || 0));
      setAmount(outstanding);
      setMode("UPI");
      setReceivedOn(new Date().toISOString().slice(0, 10));
      setReference(""); setNotes("");
    }
  }, [open, invoice]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[60] bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-card rounded-lg shadow-2xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <div className="px-5 py-4 border-b border-border">
          <div className="text-base font-semibold flex items-center gap-2" style={{ fontFamily: "Outfit" }}>
            <Wallet className="w-4 h-4 text-emerald-600" /> Record payment — {invoice?.number}
          </div>
          <div className="text-[11px] text-muted-foreground">
            Invoice total ₹{invoice?.total?.toLocaleString?.("en-IN")} · Paid ₹{(invoice?.amount_paid || 0).toLocaleString?.("en-IN")}
          </div>
        </div>
        <div className="px-5 py-4 space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1"><Label className="text-[11px]">Amount ₹</Label>
              <Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} data-testid="pay-amount" /></div>
            <div className="space-y-1"><Label className="text-[11px]">Mode</Label>
              <Select value={mode} onValueChange={setMode}>
                <SelectTrigger data-testid="pay-mode"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {["UPI","NEFT","RTGS","Cash","Cheque","Card","Other"].map((m) => (
                    <SelectItem key={m} value={m}>{m}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1"><Label className="text-[11px]">Received on</Label>
              <Input type="date" value={receivedOn} onChange={(e) => setReceivedOn(e.target.value)} data-testid="pay-date" /></div>
            <div className="space-y-1"><Label className="text-[11px]">Reference / UTR</Label>
              <Input value={reference} onChange={(e) => setReference(e.target.value)} /></div>
          </div>
          <div className="space-y-1"><Label className="text-[11px]">Notes</Label>
            <Textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional" /></div>
        </div>
        <div className="px-5 py-3 border-t border-border flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => onRecord({ amount, mode, received_on: receivedOn, reference, notes })} data-testid="pay-save">
            Save payment
          </Button>
        </div>
      </div>
    </div>
  );
}

function RecurringDayDialog({ open, onClose, onSave }) {
  const [day, setDay] = useState(1);
  useEffect(() => { if (open) setDay(1); }, [open]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[60] bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-card rounded-lg shadow-2xl w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
        <div className="px-5 py-4 border-b border-border">
          <div className="text-base font-semibold flex items-center gap-2" style={{ fontFamily: "Outfit" }}>
            <Repeat className="w-4 h-4 text-primary" /> Save as recurring
          </div>
          <div className="text-[11px] text-muted-foreground">A Draft invoice will be created on this day each month.</div>
        </div>
        <div className="px-5 py-4 space-y-2">
          <Label className="text-[11px]">Day of month (1–28)</Label>
          <Input type="number" min="1" max="28" value={day} onChange={(e) => setDay(parseInt(e.target.value || "1", 10))} />
        </div>
        <div className="px-5 py-3 border-t border-border flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={() => onSave(day)} data-testid="recurring-day-save">Create template</Button>
        </div>
      </div>
    </div>
  );
}

export { STATUS_CHIP };

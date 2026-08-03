import React, { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { formatINR } from "@/lib/format";
import {
  Plus, Search, Phone, Mail, Building2, CalendarClock, User as UserIcon,
  Rocket, Trash2, Save, Filter, X, StickyNote, FileText, AlertTriangle, ArrowUpDown, MessageSquarePlus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

const STAGE_COLORS = {
  New: "bg-slate-500/10 text-slate-600 dark:text-slate-300 border-slate-500/25",
  Contacted: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/25",
  Qualified: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-500/25",
  Proposal: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/25",
  Negotiation: "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/25",
  Onboarded: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/25",
  Lost: "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/25",
};

const SOURCES = ["Website", "Referral", "Cold Call", "Ad", "Instagram", "LinkedIn", "Other"];
const PRIORITIES = [
  { key: "Urgent", cls: "bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30" },
  { key: "High", cls: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/30" },
  { key: "Medium", cls: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30" },
  { key: "Low", cls: "bg-slate-500/10 text-slate-600 dark:text-slate-300 border-slate-500/30" },
];

function PriorityChip({ value }) {
  const p = PRIORITIES.find((x) => x.key === value) || PRIORITIES[2];
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${p.cls}`}>
      {p.key}
    </span>
  );
}

const emptyLead = {
  name: "",
  company: "",
  email: "",
  phone: "",
  source: "Website",
  stage: "New",
  priority: "Medium",
  next_step: "",
  follow_up_date: "",
  assigned_to_id: "",
  notes: "",
  value_estimate: 0,
};

function LeadCard({ lead, onOpen, onQuickLog }) {
  const overdue = lead.is_due;
  return (
    <div
      data-testid={`lead-card-${lead.id}`}
      className={`w-full text-left card-flat p-3 hover:shadow-md transition group ${overdue ? "border-l-4 border-l-red-500" : ""}`}
    >
      <div className="flex items-start justify-between gap-2">
        <button onClick={() => onOpen(lead)} className="text-left flex-1 min-w-0" data-testid={`lead-open-${lead.id}`}>
          <div className="font-semibold truncate flex items-center gap-1.5">
            {lead.name}
          </div>
          {lead.company && (
            <div className="text-[11px] text-muted-foreground flex items-center gap-1 mt-0.5">
              <Building2 className="w-3 h-3" /> {lead.company}
            </div>
          )}
        </button>
        <button
          onClick={(e) => { e.stopPropagation(); onQuickLog(lead); }}
          data-testid={`lead-quicklog-${lead.id}`}
          title="Log activity / update follow-up"
          className="shrink-0 rounded-full p-1.5 hover:bg-primary/10 text-primary opacity-0 group-hover:opacity-100 transition"
        >
          <MessageSquarePlus className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="flex items-center gap-1 mt-1.5 flex-wrap">
        <PriorityChip value={lead.priority || "Medium"} />
        {overdue && (
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-red-500/15 text-red-600 dark:text-red-400">
            <AlertTriangle className="w-3 h-3" /> Overdue
          </span>
        )}
        {lead.value_estimate > 0 && (
          <span className="text-[11px] font-semibold text-primary tabular-nums ml-auto">
            {formatINR(lead.value_estimate)}
          </span>
        )}
      </div>
      {lead.next_step && (
        <div className="text-[11px] text-muted-foreground mt-2 line-clamp-2">→ {lead.next_step}</div>
      )}
      <div className="flex items-center justify-between mt-2 text-[11px] text-muted-foreground">
        <span className="flex items-center gap-1">
          {lead.assigned_to_name && (<><UserIcon className="w-3 h-3" />{lead.assigned_to_name}</>)}
        </span>
        {lead.follow_up_date && (
          <span className={`flex items-center gap-1 ${overdue ? "text-red-600 font-semibold" : ""}`}>
            <CalendarClock className="w-3 h-3" />
            {new Date(lead.follow_up_date).toLocaleDateString()}
          </span>
        )}
      </div>
    </div>
  );
}

function LeadDialog({ open, onOpenChange, lead, teamMembers, stages, onSaved, onDelete, onOnboarded, onCreateQuotation }) {
  const [form, setForm] = useState(lead || emptyLead);
  const [saving, setSaving] = useState(false);
  const [newActivity, setNewActivity] = useState({ kind: "note", description: "", due_date: "" });
  const isEdit = !!lead?.id;

  useEffect(() => {
    setForm(lead || emptyLead);
  }, [lead]);

  const save = async () => {
    if (!form.name?.trim()) return toast.error("Lead name is required");
    setSaving(true);
    try {
      const payload = { ...form, value_estimate: parseFloat(form.value_estimate || 0) };
      // Convert empty strings to null-ish for optional foreign-keys
      if (payload.assigned_to_id === "" || payload.assigned_to_id === "none") payload.assigned_to_id = null;
      if (payload.follow_up_date === "") payload.follow_up_date = null;
      const r = isEdit
        ? await api.patch(`/leads/${lead.id}`, payload)
        : await api.post("/leads", payload);
      toast.success(isEdit ? "Lead updated" : "Lead created");
      onSaved(r.data);
      if (!isEdit) onOpenChange(false);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to save");
    } finally { setSaving(false); }
  };

  const addActivity = async () => {
    if (!newActivity.description.trim()) return toast.error("Add a description");
    try {
      const r = await api.post(`/leads/${lead.id}/activities`, {
        kind: newActivity.kind,
        description: newActivity.description,
        due_date: newActivity.due_date || null,
      });
      setForm((prev) => ({ ...prev, activities: [...(prev.activities || []), r.data] }));
      setNewActivity({ kind: "note", description: "", due_date: "" });
      onSaved({ ...form, activities: [...(form.activities || []), r.data] });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to add activity");
    }
  };

  const toggleActivity = async (a) => {
    try {
      const r = await api.patch(`/leads/${lead.id}/activities/${a.id}`, { done: !a.done });
      const acts = (form.activities || []).map((x) => (x.id === a.id ? r.data : x));
      setForm((prev) => ({ ...prev, activities: acts }));
      onSaved({ ...form, activities: acts });
    } catch (e) {
      toast.error("Failed to update");
    }
  };

  const doOnboard = async () => {
    if (!window.confirm(`Onboard "${form.name}" and create a project?`)) return;
    try {
      const r = await api.post(`/leads/${lead.id}/onboard`, {});
      toast.success("Lead onboarded — project created");
      onOnboarded(r.data);
      onOpenChange(false);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to onboard");
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle style={{ fontFamily: "Outfit" }}>
            {isEdit ? "Edit lead" : "New lead / inquiry"}
          </DialogTitle>
        </DialogHeader>
        <div className="grid md:grid-cols-2 gap-3 max-h-[65vh] overflow-y-auto pr-1">
          <div className="space-y-1.5"><Label>Client name *</Label>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="lead-name" />
          </div>
          <div className="space-y-1.5"><Label>Company</Label>
            <Input value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} data-testid="lead-company" />
          </div>
          <div className="space-y-1.5"><Label>Email</Label>
            <Input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <div className="space-y-1.5"><Label>Phone</Label>
            <Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </div>
          <div className="space-y-1.5"><Label>Source</Label>
            <Select value={form.source} onValueChange={(v) => setForm({ ...form, source: v })}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {SOURCES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5"><Label>Stage</Label>
            <Select value={form.stage} onValueChange={(v) => setForm({ ...form, stage: v })}>
              <SelectTrigger data-testid="lead-stage"><SelectValue /></SelectTrigger>
              <SelectContent>
                {stages.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Priority</Label>
            <div className="grid grid-cols-4 gap-1.5" data-testid="lead-priority-group">
              {PRIORITIES.map((p) => {
                const active = form.priority === p.key;
                return (
                  <button
                    key={p.key} type="button"
                    onClick={() => setForm({ ...form, priority: p.key })}
                    data-testid={`priority-${p.key}`}
                    className={`inline-flex items-center justify-center rounded-md border px-2 py-1.5 text-xs font-semibold transition ${
                      active ? p.cls + " ring-2 ring-primary/40" : "border-border text-muted-foreground hover:bg-secondary/40"
                    }`}
                  >
                    {p.key}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="space-y-1.5"><Label>Assign to (sales owner)</Label>
            <Select
              value={form.assigned_to_id || "none"}
              onValueChange={(v) => setForm({ ...form, assigned_to_id: v === "none" ? "" : v })}
            >
              <SelectTrigger data-testid="lead-assignee"><SelectValue placeholder="Unassigned" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Unassigned</SelectItem>
                {teamMembers.map((u) => (
                  <SelectItem key={u.id} value={u.id}>
                    {u.first_name} {u.last_name || ""} — {u.designation}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5"><Label>Follow-up date</Label>
            <Input
              type="datetime-local"
              value={form.follow_up_date ? form.follow_up_date.slice(0, 16) : ""}
              onChange={(e) => setForm({ ...form, follow_up_date: e.target.value })}
              data-testid="lead-followup"
            />
          </div>
          <div className="space-y-1.5"><Label>Value estimate (₹)</Label>
            <Input type="number" value={form.value_estimate}
                   onChange={(e) => setForm({ ...form, value_estimate: e.target.value })} />
          </div>
          <div className="space-y-1.5 md:col-span-2"><Label>Next step</Label>
            <Input value={form.next_step} onChange={(e) => setForm({ ...form, next_step: e.target.value })} placeholder="e.g. Send intro deck, schedule discovery call…" data-testid="lead-nextstep" />
          </div>
          <div className="space-y-1.5 md:col-span-2"><Label>Notes</Label>
            <Textarea rows={2} value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
          </div>

          {isEdit && (
            <div className="md:col-span-2 mt-2">
              <div className="text-overline mb-2 flex items-center gap-1.5">
                <StickyNote className="w-3 h-3" /> Activity timeline
              </div>
              <div className="space-y-2">
                {(form.activities || []).length === 0 && (
                  <div className="text-xs text-muted-foreground">No activity yet — log your first note or call.</div>
                )}
                {(form.activities || []).map((a) => (
                  <div key={a.id} className="flex items-start gap-2 text-sm p-2 rounded-md border border-border">
                    <input type="checkbox" className="mt-1 accent-primary" checked={!!a.done} onChange={() => toggleActivity(a)} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] uppercase tracking-wide font-semibold text-primary">{a.kind}</span>
                        <span className="text-[11px] text-muted-foreground">by {a.created_by_name} · {new Date(a.created_at).toLocaleDateString()}</span>
                        {a.due_date && (
                          <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                            <CalendarClock className="w-3 h-3" /> {new Date(a.due_date).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                      <div className={`text-sm mt-0.5 ${a.done ? "line-through text-muted-foreground" : ""}`}>{a.description}</div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-3 flex gap-2 flex-wrap items-end">
                <div className="w-32">
                  <Label className="text-[11px]">Type</Label>
                  <Select value={newActivity.kind} onValueChange={(v) => setNewActivity({ ...newActivity, kind: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="note">Note</SelectItem>
                      <SelectItem value="call">Call</SelectItem>
                      <SelectItem value="meeting">Meeting</SelectItem>
                      <SelectItem value="task">Task</SelectItem>
                      <SelectItem value="email">Email</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex-1 min-w-[180px]">
                  <Label className="text-[11px]">Description</Label>
                  <Input value={newActivity.description}
                         onChange={(e) => setNewActivity({ ...newActivity, description: e.target.value })}
                         placeholder="What happened?" data-testid="activity-description" />
                </div>
                <div className="w-52">
                  <Label className="text-[11px]">Due (optional)</Label>
                  <Input type="datetime-local" value={newActivity.due_date}
                         onChange={(e) => setNewActivity({ ...newActivity, due_date: e.target.value })} />
                </div>
                <Button onClick={addActivity} data-testid="add-activity-button">Add</Button>
              </div>
            </div>
          )}
        </div>
        <DialogFooter className="flex-wrap gap-2">
          {isEdit && (
            <Button variant="outline" className="gap-1.5" onClick={() => onCreateQuotation(lead)} data-testid="lead-create-quotation">
              <FileText className="w-4 h-4" /> Create quotation
            </Button>
          )}
          {isEdit && lead.stage !== "Onboarded" && (
            <Button variant="outline" className="mr-auto gap-1.5" onClick={doOnboard} data-testid="lead-onboard-button">
              <Rocket className="w-4 h-4" /> Onboard → Create project
            </Button>
          )}
          {isEdit && (
            <Button variant="outline" className="text-red-600 gap-1.5" onClick={() => onDelete(lead)}>
              <Trash2 className="w-4 h-4" /> Delete
            </Button>
          )}
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={save} disabled={saving} className="gap-1.5" data-testid="lead-save-button">
            <Save className="w-4 h-4" /> {saving ? "Saving…" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function CRMPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [stages, setStages] = useState(["New", "Contacted", "Qualified", "Proposal", "Negotiation", "Onboarded", "Lost"]);
  const [leads, setLeads] = useState([]);
  const [team, setTeam] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [assigneeFilter, setAssigneeFilter] = useState("all");
  const [dialogLead, setDialogLead] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [sortBy, setSortBy] = useState("follow_up");
  const [quickLog, setQuickLog] = useState({ open: false, lead: null });

  const load = async () => {
    setLoading(true);
    try {
      const params = { include_onboarded: false, sort: sortBy };
      if (search) params.q = search;
      if (assigneeFilter && assigneeFilter !== "all") params.assigned_to_id = assigneeFilter;
      const [ls, sts, tm] = await Promise.all([
        api.get("/leads", { params }),
        api.get("/leads/stages"),
        api.get("/leads/team"),
      ]);
      setLeads(ls.data || []);
      setStages(sts.data || stages);
      setTeam(tm.data || []);
    } catch (e) {
      // silent
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [assigneeFilter, sortBy]);

  // Debounced search
  useEffect(() => {
    const t = setTimeout(load, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line
  }, [search]);

  const visibleStages = useMemo(
    () => stages.filter((s) => s !== "Onboarded"),
    [stages]
  );

  const byStage = useMemo(() => {
    const out = {};
    visibleStages.forEach((s) => (out[s] = []));
    leads.forEach((l) => {
      if (out[l.stage]) out[l.stage].push(l);
    });
    return out;
  }, [visibleStages, leads]);

  const totals = useMemo(() => {
    const active = leads.filter((l) => l.stage !== "Lost" && l.stage !== "Onboarded");
    const pipeline = active.reduce((s, l) => s + (l.value_estimate || 0), 0);
    const won = leads.filter((l) => l.stage === "Onboarded")
      .reduce((s, l) => s + (l.value_estimate || 0), 0);
    return { count: leads.length, active: active.length, pipeline, won };
  }, [leads]);

  const openNew = () => { setDialogLead(null); setDialogOpen(true); };
  const openEdit = (l) => { setDialogLead(l); setDialogOpen(true); };

  const onSaved = (data) => {
    setLeads((prev) => {
      const idx = prev.findIndex((x) => x.id === data.id);
      if (idx === -1) return [data, ...prev];
      const next = [...prev];
      next[idx] = data;
      return next;
    });
    setDialogLead(data);
  };

  const onDelete = async (l) => {
    if (!window.confirm(`Delete lead "${l.name}"?`)) return;
    try {
      await api.delete(`/leads/${l.id}`);
      setLeads((prev) => prev.filter((x) => x.id !== l.id));
      setDialogOpen(false);
      toast.success("Lead deleted");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to delete");
    }
  };

  const onOnboarded = (payload) => {
    setLeads((prev) => prev.map((x) => (x.id === payload.lead.id ? payload.lead : x)));
    toast.success("Project created — opening project…");
    if (payload.project?.id) navigate(`/projects/${payload.project.id}`);
  };

  const onCreateQuotation = (lead) => {
    // Navigate to Billing page with a `?leadId=` hint (the page can use it later).
    // For MVP we simply jump to Billing; the user picks the lead in the dialog.
    setDialogOpen(false);
    navigate(`/billing?leadId=${lead.id}`);
  };

  return (
    <div className="space-y-6" data-testid="crm-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="text-overline">Sales pipeline</div>
          <h1 className="text-3xl sm:text-4xl font-semibold" style={{ fontFamily: "Outfit" }}>
            CRM · Leads & Inquiries
          </h1>
        </div>
        <Button onClick={openNew} className="gap-1.5 rounded-full" data-testid="new-lead-button">
          <Plus className="w-4 h-4" /> New lead
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Tile label="Total leads" value={totals.count} />
        <Tile label="Active pipeline" value={totals.active} />
        <Tile label="Pipeline value" value={formatINR(totals.pipeline)} />
        <Tile label="Won (Onboarded ₹)" value={formatINR(totals.won)} />
      </div>

      <div className="card-flat p-3 flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <Input placeholder="Search name, company, phone or email…" value={search}
                 onChange={(e) => setSearch(e.target.value)}
                 className="pl-9" data-testid="lead-search" />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-muted-foreground" />
          <Select value={assigneeFilter} onValueChange={setAssigneeFilter}>
            <SelectTrigger className="w-56" data-testid="lead-assignee-filter"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All owners</SelectItem>
              <SelectItem value={user?.id}>Assigned to me</SelectItem>
              {team.filter((t) => t.id !== user?.id).map((t) => (
                <SelectItem key={t.id} value={t.id}>{t.first_name} {t.last_name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={sortBy} onValueChange={setSortBy}>
            <SelectTrigger className="w-44" data-testid="lead-sort"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="follow_up">Follow-up date ↑</SelectItem>
              <SelectItem value="priority">Priority (High → Low)</SelectItem>
              <SelectItem value="updated">Recently updated</SelectItem>
            </SelectContent>
          </Select>
          {(search || assigneeFilter !== "all") && (
            <Button variant="ghost" size="sm" onClick={() => { setSearch(""); setAssigneeFilter("all"); setSortBy("follow_up"); }}
                    className="gap-1"><X className="w-3.5 h-3.5" /> Clear</Button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="text-sm text-muted-foreground">Loading…</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-3">
          {stages.map((s) => (
            <div key={s} className="space-y-2" data-testid={`stage-col-${s}`}>
              <div className={`text-xs font-semibold px-3 py-1.5 rounded-full inline-flex border ${STAGE_COLORS[s] || "bg-secondary"}`}>
                {s} · {byStage[s]?.length || 0}
              </div>
              <div className="space-y-2 min-h-[60px]">
                {(byStage[s] || []).map((l) => (
                  <LeadCard key={l.id} lead={l} onOpen={openEdit}
                            onQuickLog={(lead) => setQuickLog({ open: true, lead })} />
                ))}
                {(byStage[s] || []).length === 0 && (
                  <div className="text-[11px] text-muted-foreground italic px-2 py-3">No leads</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <LeadDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        lead={dialogLead}
        teamMembers={team}
        stages={stages}
        onSaved={onSaved}
        onDelete={onDelete}
        onOnboarded={onOnboarded}
        onCreateQuotation={onCreateQuotation}
      />

      <QuickLogDialog
        open={quickLog.open}
        lead={quickLog.lead}
        stages={stages}
        onClose={() => setQuickLog({ open: false, lead: null })}
        onSaved={(updated) => { onSaved(updated); setQuickLog({ open: false, lead: null }); }}
      />
    </div>
  );
}

function QuickLogDialog({ open, lead, stages, onClose, onSaved }) {
  const NEXT_STEP_OPTIONS = [
    "Send proposal",
    "Schedule discovery call",
    "Send quotation",
    "Follow-up call",
    "Send contract",
    "Payment reminder",
    "Onboard client",
    "Custom…",
  ];
  const [kind, setKind] = React.useState("call");
  const [description, setDescription] = React.useState("");
  const [stage, setStage] = React.useState("");
  const [followUp, setFollowUp] = React.useState("");
  const [nextStepChoice, setNextStepChoice] = React.useState("");
  const [nextStepCustom, setNextStepCustom] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    if (open && lead) {
      setKind("call");
      setDescription("");
      setStage(lead.stage || "");
      setFollowUp(lead.follow_up_date ? lead.follow_up_date.slice(0, 16) : "");
      setNextStepChoice("");
      setNextStepCustom(lead.next_step || "");
    }
  }, [open, lead]);

  if (!open || !lead) return null;

  const save = async () => {
    if (!description.trim()) { toast.error("Say what happened"); return; }
    setBusy(true);
    try {
      await api.post(`/leads/${lead.id}/activities`, { kind, description, done: false });
      const patch = {};
      if (stage && stage !== lead.stage) patch.stage = stage;
      if (followUp !== (lead.follow_up_date ? lead.follow_up_date.slice(0, 16) : "")) {
        patch.follow_up_date = followUp || null;
      }
      // Next step: dropdown OR custom text override
      const finalNextStep = nextStepChoice && nextStepChoice !== "Custom…"
        ? nextStepChoice
        : (nextStepCustom || "").trim();
      if (finalNextStep && finalNextStep !== (lead.next_step || "")) {
        patch.next_step = finalNextStep;
      }
      let updated = lead;
      if (Object.keys(patch).length) {
        const r = await api.patch(`/leads/${lead.id}`, patch);
        updated = r.data;
      } else {
        const r = await api.get(`/leads/${lead.id}`);
        updated = r.data;
      }
      toast.success("Activity logged");
      onSaved(updated);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-card rounded-lg shadow-2xl w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <div className="px-5 py-4 border-b border-border">
          <div className="text-base font-semibold flex items-center gap-2" style={{ fontFamily: "Outfit" }}>
            <MessageSquarePlus className="w-4 h-4 text-primary" /> Log activity — {lead.name}
          </div>
          {lead.company && <div className="text-[11px] text-muted-foreground mt-0.5">{lead.company}</div>}
        </div>
        <div className="px-5 py-4 space-y-3">
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label className="text-[11px]">Activity type</Label>
              <Select value={kind} onValueChange={setKind}>
                <SelectTrigger data-testid="quicklog-kind"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="call">Call</SelectItem>
                  <SelectItem value="meeting">Meeting</SelectItem>
                  <SelectItem value="email">Email</SelectItem>
                  <SelectItem value="note">Note</SelectItem>
                  <SelectItem value="task">Task</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1">
              <Label className="text-[11px]">Change stage</Label>
              <Select value={stage} onValueChange={setStage}>
                <SelectTrigger data-testid="quicklog-stage"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {stages.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">What happened?</Label>
            <Textarea rows={2} value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      data-testid="quicklog-desc"
                      placeholder="e.g. Client asked for quote by Friday, budget ₹1.5L" />
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Next step</Label>
            <Select value={nextStepChoice} onValueChange={setNextStepChoice}>
              <SelectTrigger data-testid="quicklog-nextstep"><SelectValue placeholder="Pick a next step (optional)" /></SelectTrigger>
              <SelectContent>
                {NEXT_STEP_OPTIONS.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
              </SelectContent>
            </Select>
            {(nextStepChoice === "Custom…" || !nextStepChoice) && (
              <Input value={nextStepCustom}
                     onChange={(e) => setNextStepCustom(e.target.value)}
                     placeholder={nextStepChoice === "Custom…" ? "Type your next step…" : "Or leave next step as: " + (lead.next_step || "—")}
                     className="mt-1"
                     data-testid="quicklog-nextstep-custom" />
            )}
          </div>
          <div className="space-y-1">
            <Label className="text-[11px]">Next follow-up date</Label>
            <Input type="datetime-local" value={followUp}
                   onChange={(e) => setFollowUp(e.target.value)}
                   data-testid="quicklog-followup" />
          </div>
        </div>
        <div className="px-5 py-3 border-t border-border flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={save} disabled={busy} data-testid="quicklog-save">
            {busy ? "Saving…" : "Log activity"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function Tile({ label, value }) {
  return (
    <div className="card-flat p-4">
      <div className="text-overline">{label}</div>
      <div className="text-2xl font-semibold text-primary tabular-nums mt-1" style={{ fontFamily: "Outfit" }}>
        {value}
      </div>
    </div>
  );
}

import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { UserAvatar } from "@/components/UserAvatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { formatDate, formatDateTime, formatINR } from "@/lib/format";
import { STAFF } from "@/constants/testIds";
import { UserCheck, UserX, Pencil, Key } from "lucide-react";

export default function StaffManagement() {
  const { isSuperAdmin } = useAuth();
  const [users, setUsers] = useState([]);
  const [settings, setSettings] = useState(null);
  const [tab, setTab] = useState("active");
  const [editUser, setEditUser] = useState(null);
  const [pwUser, setPwUser] = useState(null);
  const [newPw, setNewPw] = useState("");
  const [approveUser, setApproveUser] = useState(null);
  const [approveRole, setApproveRole] = useState("team_member");
  const [approveDesignation, setApproveDesignation] = useState("Other");

  const load = () => api.get("/users").then((r) => setUsers(r.data));
  useEffect(() => { load(); api.get("/settings").then((r) => setSettings(r.data)); }, []);

  const submitApprove = async () => {
    await api.post(`/users/${approveUser.id}/approve`, { role: approveRole, designation: approveDesignation });
    toast.success("User approved");
    setApproveUser(null);
    load();
  };
  const reject = async (u) => { await api.post(`/users/${u.id}/reject`); toast.success("Rejected"); load(); };
  const deactivate = async (u) => { await api.delete(`/users/${u.id}`); toast.success("Deactivated"); load(); };
  const activate = async (u) => { await api.patch(`/users/${u.id}`, { status: "active" }); toast.success("Activated"); load(); };
  const saveEdit = async () => {
    const payload = {
      first_name: editUser.first_name, last_name: editUser.last_name,
      designation: editUser.designation, role: editUser.role,
      monthly_salary: parseFloat(editUser.monthly_salary || 0),
      working_hours_per_day: parseFloat(editUser.working_hours_per_day || 8),
      working_days_per_month: parseInt(editUser.working_days_per_month || 25),
      avatar_url: editUser.avatar_url,
      crm_access: !!editUser.crm_access,
    };
    await api.patch(`/users/${editUser.id}`, payload);
    toast.success("Saved");
    setEditUser(null);
    load();
  };
  const savePassword = async () => {
    if (newPw.length < 6) { toast.error("Min 6 characters"); return; }
    await api.post(`/users/${pwUser.id}/reset-password`, { new_password: newPw });
    toast.success("Password reset");
    setPwUser(null); setNewPw("");
  };

  const filter = (list) => {
    if (tab === "pending") return list.filter((u) => u.status === "pending");
    if (tab === "active") return list.filter((u) => u.status === "active");
    return list.filter((u) => u.status === "deactivated" || u.status === "rejected");
  };

  return (
    <div className="space-y-6" data-testid="staff-page">
      <div className="flex items-end justify-between flex-wrap gap-4">
        <div>
          <div className="text-overline">People</div>
          <h1 className="text-3xl sm:text-4xl font-semibold" style={{ fontFamily: "Outfit" }}>Staff Management</h1>
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="pending" data-testid="tab-pending">
            Pending {users.filter((u) => u.status === "pending").length ? `(${users.filter((u) => u.status === "pending").length})` : ""}
          </TabsTrigger>
          <TabsTrigger value="active" data-testid="tab-active">Active</TabsTrigger>
          <TabsTrigger value="archived" data-testid="tab-archived">Archived</TabsTrigger>
        </TabsList>
      </Tabs>

      <div className="card-flat divide-y divide-border">
        {filter(users).map((u) => (
          <div key={u.id} className="p-4 flex items-center gap-4" data-testid={`user-row-${u.id}`}>
            <UserAvatar user={u} size={44} />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-semibold truncate">
                {u.first_name} {u.last_name} <span className="text-muted-foreground font-normal">— {u.designation}</span>
              </div>
              <div className="text-[11px] text-muted-foreground truncate">
                {u.email} · {u.role.replace("_", " ")} · Joined {formatDate(u.created_at)}{u.last_login ? ` · Last login ${formatDateTime(u.last_login)}` : ""}
              </div>
            </div>
            {isSuperAdmin && u.monthly_salary > 0 && (
              <div className="text-right hidden md:block">
                <div className="text-overline">Salary</div>
                <div className="text-sm font-semibold">{formatINR(u.monthly_salary)}</div>
              </div>
            )}
            <div className="flex items-center gap-1">
              {u.status === "pending" && (
                <>
                  <Button size="sm" onClick={() => { setApproveUser(u); setApproveDesignation(u.designation); }} className="gap-1" data-testid={STAFF.approveButton}>
                    <UserCheck className="w-4 h-4" /> Approve
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => reject(u)} data-testid={STAFF.rejectButton}>
                    <UserX className="w-4 h-4" />
                  </Button>
                </>
              )}
              {u.status === "active" && (
                <>
                  <Button size="sm" variant="outline" onClick={() => setEditUser({ ...u })} data-testid={STAFF.editButton} className="gap-1">
                    <Pencil className="w-3.5 h-3.5" /> Edit
                  </Button>
                  {isSuperAdmin && (
                    <>
                      <Button size="sm" variant="outline" onClick={() => setPwUser(u)} className="gap-1" data-testid={`reset-pw-${u.id}`}>
                        <Key className="w-3.5 h-3.5" />
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => deactivate(u)} data-testid={`deactivate-${u.id}`}>
                        Deactivate
                      </Button>
                    </>
                  )}
                </>
              )}
              {(u.status === "deactivated" || u.status === "rejected") && isSuperAdmin && (
                <Button size="sm" onClick={() => activate(u)}>Activate</Button>
              )}
            </div>
          </div>
        ))}
        {filter(users).length === 0 && (
          <div className="p-8 text-center text-sm text-muted-foreground">No users in this list.</div>
        )}
      </div>

      {/* Approve dialog */}
      <Dialog open={!!approveUser} onOpenChange={(o) => !o && setApproveUser(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle style={{ fontFamily: "Outfit" }}>Approve {approveUser?.first_name}</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label>Role</Label>
              <Select value={approveRole} onValueChange={setApproveRole}>
                <SelectTrigger data-testid="approve-role-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="team_member">Team Member</SelectItem>
                  <SelectItem value="manager">Manager</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="super_admin">Super Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label>Designation</Label>
              <Select value={approveDesignation} onValueChange={setApproveDesignation}>
                <SelectTrigger data-testid="approve-designation-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(settings?.designations || []).map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setApproveUser(null)}>Cancel</Button>
            <Button onClick={submitApprove} data-testid="approve-submit">Approve</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit dialog */}
      <Dialog open={!!editUser} onOpenChange={(o) => !o && setEditUser(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle style={{ fontFamily: "Outfit" }}>Edit staff</DialogTitle></DialogHeader>
          {editUser && (
            <div className="space-y-3 max-h-[70vh] overflow-y-auto pr-1">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5"><Label>First name</Label><Input value={editUser.first_name} onChange={(e) => setEditUser({ ...editUser, first_name: e.target.value })} /></div>
                <div className="space-y-1.5"><Label>Last name</Label><Input value={editUser.last_name} onChange={(e) => setEditUser({ ...editUser, last_name: e.target.value })} /></div>
                <div className="space-y-1.5">
                  <Label>Designation</Label>
                  <Select value={editUser.designation} onValueChange={(v) => setEditUser({ ...editUser, designation: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>{(settings?.designations || []).map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Role</Label>
                  <Select value={editUser.role} onValueChange={(v) => setEditUser({ ...editUser, role: v })} disabled={!isSuperAdmin}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="team_member">Team Member</SelectItem>
                      <SelectItem value="manager">Manager</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                      <SelectItem value="super_admin">Super Admin</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {isSuperAdmin && (
                  <div className="space-y-1.5 col-span-2"><Label>Monthly salary (₹)</Label><Input type="number" value={editUser.monthly_salary || 0} onChange={(e) => setEditUser({ ...editUser, monthly_salary: e.target.value })} /></div>
                )}
                <div className="space-y-1.5"><Label>Hours / day</Label><Input type="number" value={editUser.working_hours_per_day} onChange={(e) => setEditUser({ ...editUser, working_hours_per_day: e.target.value })} /></div>
                <div className="space-y-1.5"><Label>Days / month</Label><Input type="number" value={editUser.working_days_per_month} onChange={(e) => setEditUser({ ...editUser, working_days_per_month: e.target.value })} /></div>
                <div className="space-y-1.5 col-span-2"><Label>Avatar URL</Label><Input value={editUser.avatar_url || ""} onChange={(e) => setEditUser({ ...editUser, avatar_url: e.target.value })} /></div>
                <div className="col-span-2 flex items-center justify-between rounded-md border border-border p-3 mt-1">
                  <div>
                    <div className="text-sm font-semibold">CRM Access</div>
                    <div className="text-[11px] text-muted-foreground">
                      Grants this teammate access to the CRM (Leads, Inquiries, Quotations, Invoices).
                      Super Admins & Admins always have access.
                    </div>
                  </div>
                  <input
                    type="checkbox"
                    className="h-5 w-5 accent-primary"
                    checked={!!editUser.crm_access}
                    onChange={(e) => setEditUser({ ...editUser, crm_access: e.target.checked })}
                    data-testid="edit-crm-access-toggle"
                    disabled={editUser.role === "super_admin" || editUser.role === "admin"}
                  />
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditUser(null)}>Cancel</Button>
            <Button onClick={saveEdit} data-testid="edit-submit">Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset password */}
      <Dialog open={!!pwUser} onOpenChange={(o) => !o && setPwUser(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle style={{ fontFamily: "Outfit" }}>Reset password</DialogTitle></DialogHeader>
          <Input type="text" placeholder="New password" value={newPw} onChange={(e) => setNewPw(e.target.value)} />
          <DialogFooter>
            <Button variant="outline" onClick={() => setPwUser(null)}>Cancel</Button>
            <Button onClick={savePassword}>Reset</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

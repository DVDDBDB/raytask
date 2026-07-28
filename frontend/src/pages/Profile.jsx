import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
import { UserAvatar } from "@/components/UserAvatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Sun, Moon, Monitor } from "lucide-react";

export default function Profile() {
  const { user, setUser } = useAuth();
  const { theme, setTheme } = useTheme();
  const [form, setForm] = useState({ first_name: "", last_name: "", avatar_url: "" });
  const [passwords, setPasswords] = useState({ current_password: "", new_password: "" });

  useEffect(() => {
    if (user) setForm({ first_name: user.first_name, last_name: user.last_name || "", avatar_url: user.avatar_url || "" });
  }, [user]);

  const save = async () => {
    const r = await api.patch("/auth/profile", { ...form, theme });
    setUser(r.data);
    localStorage.setItem("raybotix_user", JSON.stringify(r.data));
    toast.success("Profile updated");
  };

  const changePw = async () => {
    if (!passwords.new_password) return;
    try {
      await api.post("/auth/change-password", passwords);
      toast.success("Password changed");
      setPasswords({ current_password: "", new_password: "" });
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed");
    }
  };

  const themes = [
    { key: "light", label: "Light", Icon: Sun },
    { key: "dark", label: "Dark", Icon: Moon },
    { key: "system", label: "System", Icon: Monitor },
  ];

  return (
    <div className="space-y-6 max-w-3xl" data-testid="profile-page">
      <div>
        <div className="text-overline">Your account</div>
        <h1 className="text-3xl sm:text-4xl font-semibold" style={{ fontFamily: "Outfit" }}>My profile</h1>
      </div>
      <div className="card-flat p-6 space-y-4">
        <div className="flex items-center gap-4">
          <UserAvatar user={user} size={64} />
          <div>
            <div className="text-lg font-semibold">{user?.first_name} {user?.last_name}</div>
            <div className="text-[12px] text-muted-foreground">{user?.email} · {user?.designation}</div>
          </div>
        </div>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-1.5"><Label>First name</Label><Input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} /></div>
          <div className="space-y-1.5"><Label>Last name</Label><Input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} /></div>
          <div className="space-y-1.5 md:col-span-2"><Label>Avatar URL</Label><Input value={form.avatar_url} onChange={(e) => setForm({ ...form, avatar_url: e.target.value })} placeholder="https://…" /></div>
        </div>
        <div className="space-y-2">
          <Label>Theme</Label>
          <div className="flex flex-wrap gap-2">
            {themes.map(({ key, label, Icon }) => (
              <button
                key={key}
                onClick={() => setTheme(key)}
                data-testid={`theme-${key}`}
                className={`px-4 py-2 rounded-full border text-sm inline-flex items-center gap-2 transition-colors ${
                  theme === key ? "border-primary bg-primary/10 text-primary" : "border-border hover:bg-muted"
                }`}
              >
                <Icon className="w-4 h-4" /> {label}
              </button>
            ))}
          </div>
        </div>
        <Button onClick={save} className="rounded-full" data-testid="profile-save">Save changes</Button>
      </div>

      <div className="card-flat p-6 space-y-4">
        <h3 className="text-lg font-semibold" style={{ fontFamily: "Outfit" }}>Change password</h3>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="space-y-1.5"><Label>Current password</Label><Input type="password" value={passwords.current_password} onChange={(e) => setPasswords({ ...passwords, current_password: e.target.value })} /></div>
          <div className="space-y-1.5"><Label>New password</Label><Input type="password" value={passwords.new_password} onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })} /></div>
        </div>
        <Button onClick={changePw} className="rounded-full">Update password</Button>
      </div>
    </div>
  );
}

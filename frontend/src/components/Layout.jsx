import React, { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { useTheme } from "@/contexts/ThemeContext";
import { NAV } from "@/constants/testIds";
import { UserAvatar } from "@/components/UserAvatar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  LayoutDashboard, ListTodo, FolderKanban, Calendar, MessagesSquare,
  Bell, BarChart3, Wallet, Users, Settings as SettingsIcon,
  History, LogOut, Sun, Moon, Monitor, Menu, Download, X,
} from "lucide-react";
import api from "@/lib/api";
import { toast } from "sonner";

const navByRole = {
  team_member: [
    { to: "/", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/tasks", icon: ListTodo, label: "My Tasks" },
    { to: "/projects", icon: FolderKanban, label: "Projects" },
    { to: "/calendar", icon: Calendar, label: "Calendar" },
    { to: "/messages", icon: MessagesSquare, label: "Messages" },
    { to: "/notifications", icon: Bell, label: "Notifications" },
    { to: "/analytics", icon: BarChart3, label: "My Analytics" },
  ],
  manager: [
    { to: "/", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/tasks", icon: ListTodo, label: "Tasks" },
    { to: "/projects", icon: FolderKanban, label: "Projects" },
    { to: "/calendar", icon: Calendar, label: "Calendar" },
    { to: "/messages", icon: MessagesSquare, label: "Messages" },
    { to: "/notifications", icon: Bell, label: "Notifications" },
    { to: "/analytics", icon: BarChart3, label: "Analytics" },
  ],
  admin: [
    { to: "/", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/tasks", icon: ListTodo, label: "All Tasks" },
    { to: "/projects", icon: FolderKanban, label: "Projects" },
    { to: "/calendar", icon: Calendar, label: "Calendar" },
    { to: "/messages", icon: MessagesSquare, label: "Messages" },
    { to: "/notifications", icon: Bell, label: "Notifications" },
    { to: "/analytics", icon: BarChart3, label: "Analytics" },
    { to: "/cost-analytics", icon: Wallet, label: "Cost Analytics" },
    { to: "/staff", icon: Users, label: "Staff" },
    { to: "/activity", icon: History, label: "Activity Log" },
  ],
  super_admin: [
    { to: "/", icon: LayoutDashboard, label: "Dashboard" },
    { to: "/tasks", icon: ListTodo, label: "All Tasks" },
    { to: "/projects", icon: FolderKanban, label: "Projects" },
    { to: "/calendar", icon: Calendar, label: "Calendar" },
    { to: "/messages", icon: MessagesSquare, label: "Messages" },
    { to: "/notifications", icon: Bell, label: "Notifications" },
    { to: "/analytics", icon: BarChart3, label: "Analytics" },
    { to: "/cost-analytics", icon: Wallet, label: "Cost Analytics" },
    { to: "/staff", icon: Users, label: "Staff Management" },
    { to: "/activity", icon: History, label: "Activity Logs" },
    { to: "/settings", icon: SettingsIcon, label: "Settings" },
  ],
};

function RaybotixLogo({ collapsed }) {
  return (
    <Link to="/" className="flex items-center gap-2.5 px-4 py-5 select-none">
      <div className="w-9 h-9 rounded-lg bg-[#110F0F] dark:bg-primary/10 border border-primary/40 flex items-center justify-center">
        <span className="text-primary text-lg font-bold" style={{ fontFamily: "Outfit" }}>R</span>
      </div>
      {!collapsed && (
        <div className="leading-tight">
          <div className="text-sm font-semibold tracking-tight" style={{ fontFamily: "Outfit" }}>
            Raybotix
          </div>
          <div className="text-[10px] uppercase tracking-[0.24em] text-muted-foreground">Digital</div>
        </div>
      )}
    </Link>
  );
}

function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const cycle = () => setTheme(theme === "light" ? "dark" : theme === "dark" ? "system" : "light");
  const Icon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={cycle}
      data-testid={NAV.themeToggle}
      title={`Theme: ${theme}`}
    >
      <Icon className="w-4 h-4" />
    </Button>
  );
}

function InstallPWAButton() {
  const [deferred, setDeferred] = useState(null);
  useEffect(() => {
    const handler = (e) => { e.preventDefault(); setDeferred(e); };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);
  if (!deferred) return null;
  return (
    <Button
      size="sm"
      variant="outline"
      className="gap-2"
      data-testid={NAV.installPwaButton}
      onClick={async () => {
        deferred.prompt();
        await deferred.userChoice;
        setDeferred(null);
      }}
    >
      <Download className="w-4 h-4" /> Install App
    </Button>
  );
}

function NotificationBell() {
  const [unread, setUnread] = useState(0);
  const navigate = useNavigate();
  useEffect(() => {
    let stop = false;
    const load = async () => {
      try {
        const r = await api.get("/notifications");
        if (!stop) setUnread(r.data.unread || 0);
      } catch {}
    };
    load();
    const iv = setInterval(load, 15000);
    return () => { stop = true; clearInterval(iv); };
  }, []);
  return (
    <Button
      variant="ghost"
      size="icon"
      className="relative"
      data-testid={NAV.notificationBell}
      onClick={() => navigate("/notifications")}
    >
      <Bell className="w-4 h-4" />
      {unread > 0 && (
        <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-primary text-[10px] leading-4 text-primary-foreground font-semibold text-center">
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </Button>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const items = navByRole[user?.role] || navByRole.team_member;
  const [mobileOpen, setMobileOpen] = useState(false);

  const roleTag = {
    super_admin: { label: "Super Admin", cls: "bg-slate-900 text-slate-50 dark:bg-slate-100 dark:text-slate-900" },
    admin: { label: "Admin", cls: "bg-primary/10 text-primary border border-primary/25" },
    manager: { label: "Manager", cls: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/25" },
    team_member: { label: "Team", cls: "bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/25" },
  }[user?.role] || { label: "Team", cls: "bg-muted" };

  return (
    <div className="min-h-screen flex bg-background">
      {/* Sidebar */}
      <aside
        data-testid={NAV.sidebar}
        className={`${mobileOpen ? "translate-x-0" : "-translate-x-full"} lg:translate-x-0 fixed lg:sticky top-0 left-0 z-40 h-screen w-64 border-r border-border bg-card flex flex-col transition-transform`}
      >
        <div className="flex items-center justify-between">
          <RaybotixLogo />
          <button
            className="lg:hidden p-3 text-muted-foreground"
            onClick={() => setMobileOpen(false)}
            aria-label="Close menu"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <nav className="flex-1 overflow-y-auto px-3 py-2 space-y-0.5">
          {items.map((it) => (
            <NavLink
              key={it.to}
              to={it.to}
              end={it.to === "/"}
              onClick={() => setMobileOpen(false)}
              data-testid={`nav-${it.label.toLowerCase().replace(/\s+/g, "-")}`}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                  isActive
                    ? "bg-primary/10 text-primary font-semibold"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`
              }
            >
              <it.icon className="w-4 h-4" />
              {it.label}
            </NavLink>
          ))}
          <NavLink
            to="/profile"
            onClick={() => setMobileOpen(false)}
            data-testid="nav-my-profile"
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                isActive
                  ? "bg-primary/10 text-primary font-semibold"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              }`
            }
          >
            <UserAvatar user={user} size={16} />
            My Profile
          </NavLink>
        </nav>
        <div className="p-3 border-t border-border">
          <div className="flex items-center gap-3">
            <UserAvatar user={user} size={36} />
            <div className="min-w-0 flex-1">
              <div className="text-sm font-semibold truncate">{user?.first_name} {user?.last_name}</div>
              <div className="text-[11px] text-muted-foreground truncate">{user?.designation}</div>
            </div>
            <button
              onClick={() => { logout(); toast.success("Signed out"); navigate("/login"); }}
              className="text-muted-foreground hover:text-primary p-1.5 rounded-md hover:bg-muted"
              data-testid="logout-button"
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span className={`text-[10px] uppercase tracking-widest font-semibold px-2 h-5 inline-flex items-center rounded ${roleTag.cls}`}>
              {roleTag.label}
            </span>
          </div>
        </div>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 bg-black/40 z-30 lg:hidden" onClick={() => setMobileOpen(false)} />
      )}

      {/* Main */}
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="glass-header sticky top-0 z-20 h-14 flex items-center justify-between px-4 lg:px-8">
          <div className="flex items-center gap-3">
            <button
              className="lg:hidden p-1.5 rounded-md hover:bg-muted"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
              data-testid="mobile-menu-button"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="text-[11px] uppercase tracking-[0.24em] text-muted-foreground">
              Raybotix / Workspace
            </div>
          </div>
          <div className="flex items-center gap-1">
            <InstallPWAButton />
            <NotificationBell />
            <ThemeToggle />
          </div>
        </header>
        <main className="flex-1 px-4 lg:px-8 py-6 lg:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

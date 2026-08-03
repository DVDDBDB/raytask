// App root: routes, providers, and route guarding.
import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { ThemeProvider } from "@/contexts/ThemeContext";
import Layout from "@/components/Layout";
import Login from "@/pages/Login";
import Signup from "@/pages/Signup";
import Dashboard from "@/pages/Dashboard";
import Tasks from "@/pages/Tasks";
import TaskDetail from "@/pages/TaskDetail";
import Projects from "@/pages/Projects";
import ProjectDetail from "@/pages/ProjectDetail";
import CalendarPage from "@/pages/CalendarPage";
import Messages from "@/pages/Messages";
import NotificationsPage from "@/pages/NotificationsPage";
import Analytics from "@/pages/Analytics";
import CostAnalytics from "@/pages/CostAnalytics";
import StaffManagement from "@/pages/StaffManagement";
import Settings from "@/pages/Settings";
import Profile from "@/pages/Profile";
import ActivityLog from "@/pages/ActivityLog";
import CRMPage from "@/pages/CRMPage";
import BillingPage from "@/pages/BillingPage";

function Private({ children, roles }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return null;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

function PrivateCRM({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return null;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  const allowed = user.role === "super_admin" || user.role === "admin" || !!user.crm_access;
  if (!allowed) return <Navigate to="/" replace />;
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route element={<Private><Layout /></Private>}>
        <Route index element={<Dashboard />} />
        <Route path="tasks" element={<Tasks />} />
        <Route path="tasks/:id" element={<TaskDetail />} />
        <Route path="projects" element={<Projects />} />
        <Route path="projects/:id" element={<ProjectDetail />} />
        <Route path="calendar" element={<CalendarPage />} />
        <Route path="messages" element={<Messages />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="cost-analytics"
               element={<Private roles={["super_admin", "admin"]}><CostAnalytics /></Private>} />
        <Route path="crm"
               element={<PrivateCRM><CRMPage /></PrivateCRM>} />
        <Route path="billing"
               element={<PrivateCRM><BillingPage /></PrivateCRM>} />
        <Route path="staff"
               element={<Private roles={["super_admin", "admin"]}><StaffManagement /></Private>} />
        <Route path="settings"
               element={<Private roles={["super_admin"]}><Settings /></Private>} />
        <Route path="activity"
               element={<Private roles={["super_admin", "admin"]}><ActivityLog /></Private>} />
        <Route path="profile" element={<Profile />} />
      </Route>
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}

export default function App() {
  return (
    <div className="App">
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <AppRoutes />
            <Toaster richColors position="top-right" />
          </BrowserRouter>
        </AuthProvider>
      </ThemeProvider>
    </div>
  );
}

// Auth context: persistent JWT, user, login/logout, permissions helpers.
import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem("raybotix_user") || "null"); }
    catch { return null; }
  });
  const [token, setToken] = useState(() => localStorage.getItem("raybotix_token") || null);
  const [loading, setLoading] = useState(true);

  const refreshMe = useCallback(async () => {
    if (!token) { setLoading(false); return; }
    try {
      const r = await api.get("/auth/me");
      setUser(r.data);
      localStorage.setItem("raybotix_user", JSON.stringify(r.data));
    } catch {
      setUser(null); setToken(null);
      localStorage.removeItem("raybotix_token");
      localStorage.removeItem("raybotix_user");
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { refreshMe(); }, [refreshMe]);

  const login = async (email, password) => {
    const r = await api.post("/auth/login", { email, password });
    localStorage.setItem("raybotix_token", r.data.token);
    localStorage.setItem("raybotix_user", JSON.stringify(r.data.user));
    setToken(r.data.token); setUser(r.data.user);
    return r.data.user;
  };

  const signup = async (payload) => {
    const r = await api.post("/auth/signup", payload);
    return r.data;
  };

  const logout = () => {
    localStorage.removeItem("raybotix_token");
    localStorage.removeItem("raybotix_user");
    setUser(null); setToken(null);
  };

  const isAdmin = user?.role === "super_admin" || user?.role === "admin";
  const isSuperAdmin = user?.role === "super_admin";
  const canManageTasks = ["super_admin", "admin", "manager"].includes(user?.role);
  const canSeeCosts = isAdmin;

  return (
    <AuthContext.Provider value={{
      user, token, loading, login, logout, signup, refreshMe, setUser,
      isAdmin, isSuperAdmin, canManageTasks, canSeeCosts,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);

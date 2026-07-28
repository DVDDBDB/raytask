// Indian Rupee & time formatting helpers.
export const formatINR = (amount) => {
  if (amount === null || amount === undefined || isNaN(amount)) return "₹0";
  const n = Math.round(Number(amount));
  return "₹" + n.toLocaleString("en-IN");
};

export const formatINRPrecise = (amount) => {
  if (amount === null || amount === undefined || isNaN(amount)) return "₹0";
  return "₹" + Number(amount).toLocaleString("en-IN", { maximumFractionDigits: 2 });
};

export const formatDuration = (seconds) => {
  if (!seconds || seconds < 0) return "0m";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
};

export const formatTimer = (seconds) => {
  if (!seconds || seconds < 0) seconds = 0;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(h)}:${pad(m)}:${pad(s)}`;
};

export const formatDate = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
};

export const formatDateTime = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-IN", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit", hour12: true,
  });
};

export const relativeDate = (iso) => {
  if (!iso) return "";
  const now = new Date();
  const d = new Date(iso);
  const diff = (d - now) / 1000;
  const abs = Math.abs(diff);
  const sign = diff >= 0 ? "in " : "";
  const suffix = diff >= 0 ? "" : " ago";
  if (abs < 60) return `${sign}${Math.round(abs)}s${suffix}`;
  if (abs < 3600) return `${sign}${Math.round(abs / 60)}m${suffix}`;
  if (abs < 86400) return `${sign}${Math.round(abs / 3600)}h${suffix}`;
  return `${sign}${Math.round(abs / 86400)}d${suffix}`;
};

export const userLabel = (u, opts = {}) => {
  if (!u) return "Unassigned";
  const base = `${u.first_name || ""} — ${u.designation || "Other"}`;
  if (opts.showWorkload && typeof u.active_tasks_count === "number") {
    return `${base} — ${u.active_tasks_count} Active`;
  }
  return base;
};

export const initials = (name = "") => {
  return name.split(" ").filter(Boolean).slice(0, 2).map((s) => s[0]?.toUpperCase()).join("") || "?";
};

// Upload/download helpers backed by /api/files
import api, { API_URL } from "@/lib/api";

export async function uploadFile(file) {
  const fd = new FormData();
  fd.append("file", file);
  const r = await api.post("/files/upload", fd, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return r.data; // {id, filename, content_type, size, url}
}

/** Build an <img src> URL that carries the JWT as a query param. */
export function fileImgSrc(fileId) {
  if (!fileId) return "";
  const token = localStorage.getItem("raybotix_token") || "";
  return `${API_URL}/files/${fileId}?auth=${encodeURIComponent(token)}`;
}

/** Trigger a browser download for a file id (auth-injected). */
export async function downloadFile(fileId, filename) {
  const r = await api.get(`/files/${fileId}`, { responseType: "blob" });
  const url = URL.createObjectURL(r.data);
  const a = document.createElement("a");
  a.href = url; a.download = filename || "file";
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** Trigger download for any API path (used by /exports/*.xlsx). */
export async function downloadFromPath(path, filename) {
  const r = await api.get(path, { responseType: "blob" });
  const url = URL.createObjectURL(r.data);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export function humanSize(bytes = 0) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

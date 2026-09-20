export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

function authHeaders() {
  const token = sessionStorage.getItem("srisocials_admin_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function handle(res) {
  if (res.status === 401) {
    sessionStorage.removeItem("srisocials_admin_token");
    window.location.href = "/login";
    throw new Error("Session expired");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Request failed");
  }
  return res.json();
}

export async function login(username, password) {
  const res = await fetch(`${API_BASE}/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await handle(res);
  sessionStorage.setItem("srisocials_admin_token", data.token);
  return data;
}

export function logout() {
  sessionStorage.removeItem("srisocials_admin_token");
}

export function isLoggedIn() {
  return Boolean(sessionStorage.getItem("srisocials_admin_token"));
}

export async function listVideos(status) {
  const qs = status ? `?status=${status}` : "";
  const res = await fetch(`${API_BASE}/admin/videos${qs}`, { headers: authHeaders() });
  return handle(res);
}

export async function approveVideo(id, made_for_kids) {
  const res = await fetch(`${API_BASE}/admin/videos/${id}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ made_for_kids }),
  });
  return handle(res);
}

export async function rejectVideo(id, notes) {
  const res = await fetch(`${API_BASE}/admin/videos/${id}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ notes }),
  });
  return handle(res);
}

export async function publishVideo(id, privacy_status = "private") {
  const res = await fetch(`${API_BASE}/admin/videos/${id}/publish`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ privacy_status }),
  });
  return handle(res);
}

export async function previewUrl(id) {
  const res = await fetch(`${API_BASE}/admin/videos/${id}/preview-url`, {headers: authHeaders()});
  return (await handle(res)).url;
}

export async function listChannels() {
  const res = await fetch(`${API_BASE}/admin/channels`, { headers: authHeaders() });
  return handle(res);
}

export async function channelStats(id) {
  const res = await fetch(`${API_BASE}/admin/channels/${id}/stats`, { headers: authHeaders() });
  return handle(res);
}

export async function channelAnalytics(id, start, end) {
  const qs = new URLSearchParams({start_date:start, end_date:end});
  return handle(await fetch(`${API_BASE}/admin/channels/${id}/analytics?${qs}`, {headers:authHeaders()}));
}

export async function startGoogleConnect() {
  const res = await fetch(`${API_BASE}/auth/google/login`, { headers: authHeaders() });
  const data = await handle(res);
  window.location.href = data.authorization_url;
}

export async function startMetaConnect() {
  const data = await handle(await fetch(`${API_BASE}/auth/meta/login`, {headers: authHeaders()}));
  window.location.href = data.authorization_url;
}

export async function deleteVideo(id) {
  return handle(await fetch(`${API_BASE}/admin/videos/${id}`, {method: "DELETE", headers: authHeaders()}));
}

export async function disconnectChannel(id) {
  return handle(await fetch(`${API_BASE}/admin/channels/${id}`, {method: "DELETE", headers: authHeaders()}));
}

export async function resetPublish(id) {
  return handle(await fetch(`${API_BASE}/admin/videos/${id}/reset-publish`, {method:"POST", headers:{...authHeaders(), "Content-Type":"application/json"}, body:JSON.stringify({confirmed_not_published:true})}));
}


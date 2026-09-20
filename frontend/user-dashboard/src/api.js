export const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
const headers = () => ({ Authorization: `Bearer ${sessionStorage.getItem("team_token") || ""}` });

function checkSession(res) {
  if(res.status === 401) {
    sessionStorage.removeItem("team_token");
    sessionStorage.removeItem("team_name");
    location.reload();
    throw new Error("Session expired; sign in again");
  }
}

export async function login(username, password) {
  const res = await fetch(`${API_BASE}/team/login`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({username, password})});
  if (!res.ok) throw new Error("Invalid credentials or server unavailable");
  const data = await res.json();
  sessionStorage.setItem("team_token", data.token);
  sessionStorage.setItem("team_name", data.display_name);
  return data;
}

export async function getChannels() {
  const res = await fetch(`${API_BASE}/public/channels`, {headers: headers()});
  checkSession(res);
  if (!res.ok) throw new Error("Could not load channels");
  return res.json();
}

export async function submitVideo(formData) {
  const res = await fetch(`${API_BASE}/public/uploads`, {
    method: "POST",
    headers: headers(),
    body: formData,
  });
  checkSession(res);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || "Upload failed");
  }
  return res.json();
}

export async function getMyUploads(name) {
  const res = await fetch(`${API_BASE}/public/uploads/mine`, {headers: headers()});
  checkSession(res);
  if (!res.ok) throw new Error("Could not load your submissions");
  return res.json();
}

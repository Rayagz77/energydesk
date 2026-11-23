// Acces a l'API EnergyDesk. Le jeton JWT est garde dans sessionStorage :
// il disparait a la fermeture de l'onglet. La CSP du serveur Nginx limite le risque XSS.
const TOKEN_KEY = "energydesk_token";
const USER_KEY = "energydesk_user";

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.removeItem(USER_KEY);
}

export function logout() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
  window.location.href = "index.html";
}

function formatDetail(detail) {
  if (!detail) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((e) => `${(e.loc || []).slice(1).join(".")} : ${e.msg}`).join(" ; ");
  }
  return JSON.stringify(detail);
}

export async function api(path, { method = "GET", json, form, body, raw = false } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload = body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(json);
  } else if (form) {
    payload = new URLSearchParams(form);
  }

  const response = await fetch(`/api/v1${path}`, { method, headers, body: payload });
  if (response.status === 401 && token) {
    logout();
    throw new ApiError(401, "Session expirée, reconnectez-vous.");
  }
  if (!response.ok) {
    let message = `Erreur ${response.status}`;
    try {
      const data = await response.json();
      message = formatDetail(data.detail) || message;
    } catch {
      /* reponse sans JSON */
    }
    throw new ApiError(response.status, message);
  }
  if (raw) return response;
  return response.status === 204 ? null : response.json();
}

export async function currentUser() {
  const cached = sessionStorage.getItem(USER_KEY);
  if (cached) return JSON.parse(cached);
  const user = await api("/auth/me");
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  return user;
}

// A appeler en haut de chaque page protegee.
export async function requireAuth() {
  if (!getToken()) {
    window.location.href = "index.html";
    return new Promise(() => {});
  }
  return currentUser();
}

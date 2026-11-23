// Fonctions d'affichage communes. Tout texte est insere avec textContent (jamais innerHTML)
// pour empecher l'injection de code (XSS) via un titre ou un commentaire.
import { logout } from "./api.js";

export const STATUS_LABELS = {
  nouveau: "Nouveau",
  en_cours: "En cours",
  resolu: "Résolu",
  ferme: "Fermé",
};
export const PRIORITY_LABELS = { basse: "Basse", moyenne: "Moyenne", haute: "Haute", critique: "Critique" };
export const CATEGORY_LABELS = {
  transmission: "Compteur ne transmettant plus",
  index: "Anomalie de relevé ou d'index",
  equipement: "Dysfonctionnement d'équipement",
  intervention: "Demande de vérification ou d'intervention",
};
// Doit rester identique aux transitions autorisees par l'API (app/models).
export const NEXT_STATUSES = {
  nouveau: ["en_cours"],
  en_cours: ["resolu"],
  resolu: ["ferme", "en_cours"],
  ferme: [],
};

export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

export function badge(kind, value) {
  const labels = kind === "status" ? STATUS_LABELS : PRIORITY_LABELS;
  return el("span", { class: `badge ${value}` }, labels[value] || value);
}

export function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}

export function formatSize(bytes) {
  return bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} Ko` : `${(bytes / 1048576).toFixed(1)} Mo`;
}

export function showMessage(container, text, type = "error") {
  container.textContent = text;
  container.className = `message ${type}`;
}

export function hideMessage(container) {
  container.className = "message hidden";
}

export function renderHeader(user, active) {
  const links = [
    ["dashboard.html", "Tableau de bord"],
    ["tickets.html", "Tickets"],
    ["new-ticket.html", "Nouveau ticket"],
  ];
  const nav = el(
    "nav",
    { class: "nav" },
    links.map(([href, label]) => el("a", { href, class: href === active ? "active" : null }, label)),
    el("span", { class: "who" }, `${user.full_name} (${user.role === "agent" ? "agent support" : "utilisateur"})`),
    el("button", { class: "btn small secondary", type: "button", onclick: logout }, "Déconnexion"),
  );
  const header = el(
    "header",
    { class: "topbar" },
    el("a", { class: "brand", href: "dashboard.html" }, "Energy", el("span", {}, "Desk")),
    nav,
  );
  document.body.prepend(header);
}

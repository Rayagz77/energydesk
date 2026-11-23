import { api, requireAuth } from "./api.js";
import {
  CATEGORY_LABELS,
  NEXT_STATUSES,
  STATUS_LABELS,
  badge,
  el,
  formatDate,
  formatSize,
  hideMessage,
  renderHeader,
  showMessage,
} from "./ui.js";

const user = await requireAuth();
renderHeader(user, "tickets.html");

const params = new URLSearchParams(window.location.search);
const ticketId = params.get("id");
const message = document.getElementById("message");
const isAgent = user.role === "agent";

function render(ticket) {
  document.title = `EnergyDesk — ${ticket.title}`;
  document.getElementById("title").textContent = ticket.title;
  document.getElementById("description").textContent = ticket.description;

  const rows = [
    ["Statut", badge("status", ticket.status)],
    ["Priorité", badge("priority", ticket.priority)],
    ["Type", CATEGORY_LABELS[ticket.category] || ticket.category],
    ["Équipement", ticket.equipment_id],
    ["Demandeur", ticket.created_by.full_name],
    ["Agent", ticket.assigned_to ? ticket.assigned_to.full_name : "Non attribué"],
    ["Créé le", formatDate(ticket.created_at)],
    ["Mis à jour", formatDate(ticket.updated_at)],
    ["Notification", ticket.notified_at ? `Envoyée le ${formatDate(ticket.notified_at)}` : "En attente"],
  ];
  document.getElementById("meta").replaceChildren(...rows.flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]));

  const comments = document.getElementById("comments");
  comments.replaceChildren(
    ...(ticket.comments.length
      ? ticket.comments.map((c) =>
          el(
            "div",
            { class: "comment" },
            el("div", { class: "head" }, `${c.author.full_name} — ${formatDate(c.created_at)}`),
            el("p", {}, c.content),
          ),
        )
      : [el("p", { class: "notice" }, "Aucun commentaire.")]),
  );

  const files = document.getElementById("files");
  files.replaceChildren(
    ...(ticket.attachments.length
      ? ticket.attachments.map((a) =>
          el(
            "li",
            {},
            el("span", {}, `${a.original_filename} (${formatSize(a.size_bytes)})`),
            el("button", { class: "btn small secondary", type: "button", onclick: () => download(a) }, "Télécharger"),
          ),
        )
      : [el("li", { class: "notice" }, "Aucune pièce jointe.")]),
  );

  if (isAgent) {
    document.getElementById("agent-panel").classList.remove("hidden");
    const select = document.getElementById("status");
    const next = NEXT_STATUSES[ticket.status] || [];
    select.replaceChildren(...next.map((s) => el("option", { value: s }, STATUS_LABELS[s])));
    select.disabled = next.length === 0;
    document.querySelector("#status-form button").disabled = next.length === 0;
  }
}

async function load() {
  try {
    render(await api(`/tickets/${encodeURIComponent(ticketId)}`));
  } catch (error) {
    showMessage(message, error.status === 404 ? "Ticket introuvable." : error.message);
  }
}

// Le telechargement passe par l'API (controle d'acces), puis le navigateur enregistre le fichier.
async function download(attachment) {
  try {
    const response = await api(`/attachments/${attachment.id}/download`, { raw: true });
    const url = URL.createObjectURL(await response.blob());
    const link = el("a", { href: url, download: attachment.original_filename });
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (error) {
    showMessage(message, error.message);
  }
}

document.getElementById("comment-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    await api(`/tickets/${ticketId}/comments`, { method: "POST", json: { content: form.content.value } });
    form.reset();
    hideMessage(message);
    load();
  } catch (error) {
    showMessage(message, error.message);
  }
});

document.getElementById("upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const file = form.file.files[0];
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) {
    showMessage(message, "Fichier trop volumineux (5 Mo maximum).");
    return;
  }
  const body = new FormData();
  body.append("file", file);
  try {
    await api(`/tickets/${ticketId}/attachments`, { method: "POST", body });
    form.reset();
    showMessage(message, "Fichier ajouté.", "success");
    load();
  } catch (error) {
    showMessage(message, error.message);
  }
});

if (isAgent) {
  document.getElementById("status-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api(`/tickets/${ticketId}/status`, { method: "PATCH", json: { status: event.currentTarget.status.value } });
      showMessage(message, "Statut mis à jour.", "success");
      load();
    } catch (error) {
      showMessage(message, error.message);
    }
  });
  document.getElementById("assign-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await api(`/tickets/${ticketId}/assign`, { method: "PATCH", json: { agent_id: event.currentTarget.agent_id.value } });
      showMessage(message, "Ticket attribué.", "success");
      load();
    } catch (error) {
      showMessage(message, error.message);
    }
  });
  api("/users/agents")
    .then((agents) => {
      document.getElementById("agent").replaceChildren(...agents.map((a) => el("option", { value: a.id }, a.full_name)));
    })
    .catch((error) => showMessage(message, error.message));
}

if (!ticketId) showMessage(message, "Identifiant de ticket manquant.");
else {
  if (params.get("created")) showMessage(message, "Ticket créé. La notification est traitée en arrière-plan.", "success");
  load();
}

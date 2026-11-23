import { api, requireAuth } from "./api.js";
import { renderHeader, showMessage } from "./ui.js";

const user = await requireAuth();
renderHeader(user, "new-ticket.html");

const form = document.getElementById("ticket-form");
const message = document.getElementById("message");
const submit = document.getElementById("submit");
const MAX_BYTES = 5 * 1024 * 1024;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const file = data.get("file");
  const payload = Object.fromEntries([...data].filter(([key]) => key !== "file"));

  if (!/^CPT-FICTIF-\d{6}$/.test(payload.equipment_id)) {
    showMessage(message, "Identifiant d'équipement attendu au format CPT-FICTIF-000123.");
    return;
  }
  if (file && file.size > MAX_BYTES) {
    showMessage(message, "Pièce jointe trop volumineuse (5 Mo maximum).");
    return;
  }

  submit.disabled = true;
  try {
    const ticket = await api("/tickets", { method: "POST", json: payload });
    if (file && file.size > 0) {
      const body = new FormData();
      body.append("file", file);
      await api(`/tickets/${ticket.id}/attachments`, { method: "POST", body });
    }
    window.location.href = `ticket.html?id=${encodeURIComponent(ticket.id)}&created=1`;
  } catch (error) {
    showMessage(message, error.message);
    submit.disabled = false;
  }
});

import { api, requireAuth } from "./api.js";
import { badge, el, formatDate, renderHeader, showMessage } from "./ui.js";

const user = await requireAuth();
renderHeader(user, "dashboard.html");
document.getElementById("scope").textContent =
  user.role === "agent" ? "Vue globale : tous les tickets." : "Vue personnelle : vos tickets uniquement.";

const message = document.getElementById("message");

function kpi(label, value, extraClass = "") {
  return el("div", { class: `card kpi ${extraClass}` }, el("div", { class: "value" }, value), el("div", { class: "label" }, label));
}

try {
  const [stats, page] = await Promise.all([api("/stats"), api("/tickets?limit=5")]);
  document.getElementById("kpis").append(
    kpi("Ouverts (nouveaux)", stats.ouverts),
    kpi("En cours", stats.en_cours),
    kpi("Résolus", stats.resolus),
    kpi("Critiques non fermés", stats.critiques, "critical"),
  );
  const tbody = document.getElementById("recent");
  if (page.items.length === 0) {
    tbody.append(el("tr", {}, el("td", { colspan: "5" }, "Aucun ticket pour le moment.")));
  }
  for (const t of page.items) {
    tbody.append(
      el(
        "tr",
        {},
        el("td", {}, el("a", { href: `ticket.html?id=${encodeURIComponent(t.id)}` }, t.title)),
        el("td", {}, t.equipment_id),
        el("td", {}, badge("priority", t.priority)),
        el("td", {}, badge("status", t.status)),
        el("td", {}, formatDate(t.created_at)),
      ),
    );
  }
} catch (error) {
  showMessage(message, error.message);
}

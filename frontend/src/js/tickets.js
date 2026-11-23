import { api, requireAuth } from "./api.js";
import { badge, el, formatDate, renderHeader, showMessage } from "./ui.js";

const user = await requireAuth();
renderHeader(user, "tickets.html");

const LIMIT = 20;
let offset = 0;
const message = document.getElementById("message");
const filters = document.getElementById("filters");

async function load() {
  const params = new URLSearchParams({ limit: LIMIT, offset });
  for (const [key, value] of new FormData(filters)) if (value) params.set(key, value);
  try {
    const page = await api(`/tickets?${params}`);
    const tbody = document.getElementById("rows");
    tbody.replaceChildren();
    if (page.items.length === 0) {
      tbody.append(el("tr", {}, el("td", { colspan: "7" }, "Aucun ticket.")));
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
          el("td", {}, t.created_by.full_name),
          el("td", {}, t.assigned_to ? t.assigned_to.full_name : "—"),
          el("td", {}, formatDate(t.created_at)),
        ),
      );
    }
    const end = Math.min(offset + LIMIT, page.total);
    document.getElementById("count").textContent = page.total
      ? `Tickets ${offset + 1} à ${end} sur ${page.total}`
      : "";
    document.getElementById("prev").disabled = offset === 0;
    document.getElementById("next").disabled = end >= page.total;
  } catch (error) {
    showMessage(message, error.message);
  }
}

filters.addEventListener("submit", (event) => {
  event.preventDefault();
  offset = 0;
  load();
});
document.getElementById("prev").addEventListener("click", () => {
  offset = Math.max(0, offset - LIMIT);
  load();
});
document.getElementById("next").addEventListener("click", () => {
  offset += LIMIT;
  load();
});
load();

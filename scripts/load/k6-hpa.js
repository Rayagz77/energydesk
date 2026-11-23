// Test de charge pour la demonstration du HPA (charge MESUREE par k6).
// La connexion (hachage Argon2) consomme beaucoup de CPU : c'est elle qui fait monter l'autoscaling.
//
// Dans Codespaces, avec l'application accessible sur http://localhost:8080 :
//   docker run --rm -i --network host -e BASE_URL=http://localhost:8080 \
//     -e EMAIL=charge@exemple.fr -e PASSWORD=Charge-Test-2026 grafana/k6 run - < scripts/load/k6-hpa.js
// Le resume final (requetes/s, latence p95, taux d'erreur) est la mesure a mettre dans le rapport.
import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE_URL || "http://localhost:8080";
const EMAIL = __ENV.EMAIL || "charge@exemple.fr";
const PASSWORD = __ENV.PASSWORD || "Charge-Test-2026";

export const options = {
  stages: [
    { duration: "1m", target: 10 },
    { duration: "3m", target: 30 },
    { duration: "2m", target: 30 },
    { duration: "1m", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<2000"],
  },
};

export function setup() {
  http.post(`${BASE}/api/v1/auth/register`, JSON.stringify({ email: EMAIL, full_name: "Test de charge", password: PASSWORD }), {
    headers: { "Content-Type": "application/json" },
  });
  const res = http.post(`${BASE}/api/v1/auth/login`, { username: EMAIL, password: PASSWORD });
  return { token: res.json("access_token") };
}

export default function (data) {
  const headers = { Authorization: `Bearer ${data.token}` };
  if (Math.random() < 0.3) {
    const login = http.post(`${BASE}/api/v1/auth/login`, { username: EMAIL, password: PASSWORD });
    check(login, { "connexion 200": (r) => r.status === 200 });
  }
  check(http.get(`${BASE}/api/v1/tickets?limit=20`, { headers }), { "liste 200": (r) => r.status === 200 });
  check(http.get(`${BASE}/api/v1/stats`, { headers }), { "stats 200": (r) => r.status === 200 });
  sleep(0.5);
}

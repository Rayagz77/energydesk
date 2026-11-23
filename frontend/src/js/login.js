import { api, getToken, setToken } from "./api.js";
import { hideMessage, showMessage } from "./ui.js";

if (getToken()) window.location.href = "dashboard.html";

const message = document.getElementById("message");
const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const tabLogin = document.getElementById("tab-login");
const tabRegister = document.getElementById("tab-register");

function switchTab(showLogin) {
  loginForm.classList.toggle("hidden", !showLogin);
  registerForm.classList.toggle("hidden", showLogin);
  tabLogin.classList.toggle("secondary", !showLogin);
  tabRegister.classList.toggle("secondary", showLogin);
  hideMessage(message);
}
tabLogin.addEventListener("click", () => switchTab(true));
tabRegister.addEventListener("click", () => switchTab(false));

async function login(email, password) {
  const token = await api("/auth/login", { method: "POST", form: { username: email, password } });
  setToken(token.access_token);
  window.location.href = "dashboard.html";
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(loginForm);
  try {
    await login(data.get("username"), data.get("password"));
  } catch (error) {
    showMessage(message, error.message);
  }
});

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(registerForm));
  if (data.password.length < 12) {
    showMessage(message, "Le mot de passe doit contenir au moins 12 caractères.");
    return;
  }
  try {
    await api("/auth/register", { method: "POST", json: data });
    await login(data.email, data.password);
  } catch (error) {
    showMessage(message, error.message);
  }
});

const $ = (id) => document.getElementById(id);
let pollTimer = null;

function toast(msg, isError = false) {
  const t = $("toast");
  t.textContent = msg;
  t.className = "show" + (isError ? " error" : "");
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (t.className = ""), 3000);
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (res.status === 401 && path !== "/api/login") {
    showLogin();
    throw new Error("Session expirée");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Erreur ${res.status}`);
  return data;
}

function showLogin() {
  clearInterval(pollTimer);
  $("app-view").hidden = true;
  $("login-view").hidden = false;
  $("password").focus();
}

function showApp() {
  $("login-view").hidden = true;
  $("app-view").hidden = false;
  refreshStatus();
  clearInterval(pollTimer);
  pollTimer = setInterval(refreshStatus, 5000);
}

const fmt = (v, unit, digits = 1) => (v == null ? "N/A" : `${Number(v).toFixed(digits)}${unit}`);

async function refreshStatus() {
  try {
    const s = await api("/api/status");
    $("s-cpu").textContent = fmt(s.cpu, " °C");
    $("s-temp").textContent = fmt(s.temp, " °C");
    $("s-humi").textContent = fmt(s.humi, " %", 0);
    $("s-fan").textContent = s.fan ? "ON" : "OFF";
    $("s-updated").textContent = "Mis à jour à " + new Date().toLocaleTimeString("fr-FR");
    $("live-dot").classList.add("on");
  } catch {
    $("live-dot").classList.remove("on");
  }
}

$("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/api/login", { method: "POST", body: JSON.stringify({ password: $("password").value }) });
    $("password").value = "";
    showApp();
  } catch (err) {
    toast(err.message, true);
  }
});

$("logout").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" }).catch(() => {});
  showLogin();
});

document.querySelectorAll("[data-action]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    const msg = btn.dataset.confirm;
    if (msg && !confirm(msg)) return;
    btn.disabled = true;
    try {
      const data = await api(`/api/action/${btn.dataset.action}`, { method: "POST" });
      toast(data.message || "OK");
      if (btn.dataset.action === "picture") {
        const img = $("photo");
        img.src = `/api/picture?t=${Date.now()}`;
        img.hidden = false;
      }
    } catch (err) {
      toast(err.message, true);
    } finally {
      btn.disabled = false;
    }
  });
});

// Au chargement : on tente directement, sinon écran de connexion
api("/api/status").then(showApp).catch(showLogin);

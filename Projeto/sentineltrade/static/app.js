"use strict";

/* ===================== Utilidades ===================== */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const state = {
  token: sessionStorage.getItem("st_token"),
  user: null,
  challengeId: null,
  assets: [],
  side: "BUY",
  idemKey: null,
  activeTab: null,
};

const ROLE_LABEL = {
  INVESTOR: "Investidor",
  ADMIN: "Administrador",
  AUDITOR: "Auditor",
  RISK_ANALYST: "Analista de Risco",
};
const STATUS_LABEL = {
  CREATED: "Criada", VALIDATED: "Validada", SENT: "Enviada",
  PARTIALLY_FILLED: "Parcial", FILLED: "Executada", REJECTED: "Rejeitada", CANCELLED: "Cancelada",
};
const CANCELLABLE = ["CREATED", "VALIDATED", "SENT", "PARTIALLY_FILLED"];

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const money = (v) => brl.format(Number(v));

// O servidor devolve datas em UTC, mas o SQLite as serializa sem fuso: assume UTC quando faltar.
function fmtDate(value) {
  if (!value) return "—";
  const iso = /(Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : value + "Z";
  const d = new Date(iso);
  return isNaN(d) ? String(value) : d.toLocaleString("pt-BR");
}

// Cria elementos sem usar innerHTML: todo texto vindo da API é inserido como texto (anti-XSS).
function h(tag, props = {}, ...children) {
  const el = document.createElement(tag);
  for (const [key, val] of Object.entries(props)) {
    if (val == null || val === false) continue;
    if (key === "class") el.className = val;
    else if (key === "text") el.textContent = val;
    else if (key.startsWith("on")) el.addEventListener(key.slice(2), val);
    else el.setAttribute(key, val === true ? "" : val);
  }
  for (const child of children.flat()) {
    if (child == null || child === false) continue;
    el.append(child.nodeType ? child : document.createTextNode(String(child)));
  }
  return el;
}

function renderTable(table, columns, rows, emptyMessage) {
  table.replaceChildren();
  if (!rows.length) {
    table.append(h("caption", { class: "empty", text: emptyMessage }));
    return;
  }
  table.append(
    h("thead", {}, h("tr", {}, columns.map((c) => h("th", { class: c.num ? "num" : "", text: c.label })))),
    h("tbody", {}, rows.map((row) =>
      h("tr", {}, columns.map((c) => {
        const content = c.render ? c.render(row) : row[c.key];
        return h("td", { class: [c.num ? "num" : "", c.wrap ? "wrap" : ""].join(" ").trim() }, content ?? "—");
      })))),
  );
}

let toastTimer;
function toast(message, isError = false) {
  const el = $("#toast");
  el.textContent = message;
  el.className = isError ? "error" : "";
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 4500);
}

function errorMessage(data, status) {
  const detail = data && data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => {
      const field = (d.loc || []).slice(1).join(".");
      return field ? `${field}: ${d.msg}` : d.msg;
    }).join(" · ");
  }
  return `Erro inesperado (HTTP ${status}).`;
}

async function api(path, { method = "GET", body, auth = true } = {}) {
  const headers = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (auth && state.token) headers["Authorization"] = "Bearer " + state.token;

  let res;
  try {
    res = await fetch(path, { method, headers, body: body !== undefined ? JSON.stringify(body) : undefined });
  } catch {
    const err = new Error("Sem conexão com o servidor.");
    err.network = true;
    throw err;
  }
  let data = null;
  try { data = await res.json(); } catch { /* resposta sem corpo */ }

  if (!res.ok) {
    if (res.status === 401 && auth && state.token) logout("Sessão expirada. Entre novamente.");
    const err = new Error(errorMessage(data, res.status));
    err.status = res.status;
    throw err;
  }
  return data;
}

// Desabilita o botão de envio durante a requisição e mostra erros em toast.
async function submitting(form, action) {
  const btn = $("button[type=submit]", form);
  if (btn) btn.disabled = true;
  try {
    await action();
  } catch (err) {
    toast(err.message, true);
  } finally {
    if (btn) btn.disabled = false;
  }
}

const formData = (form) => Object.fromEntries(new FormData(form).entries());
const num = (s) => String(s).replace(",", ".").trim();

/* ===================== Autenticação ===================== */
function showAuthError(message) {
  const el = $("#auth-error");
  el.textContent = message || "";
  el.hidden = !message;
}

function setAuthMode(mode) {
  $$("#auth-tabs button").forEach((b) => b.classList.toggle("active", b.dataset.auth === mode));
  $("#form-login").hidden = mode !== "login";
  $("#form-register").hidden = mode !== "register";
  $("#form-mfa").hidden = true;
  showAuthError("");
}

$$("#auth-tabs button").forEach((b) => b.addEventListener("click", () => setAuthMode(b.dataset.auth)));

$("#form-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  showAuthError("");
  const f = e.currentTarget;
  const { email, password } = formData(f);
  const btn = $("button[type=submit]", f);
  btn.disabled = true;
  try {
    const res = await api("/api/auth/login", { method: "POST", auth: false, body: { email, password } });
    state.challengeId = res.challenge_id;
    f.reset();
    f.hidden = true;
    $("#auth-tabs").hidden = true;
    $("#form-mfa").hidden = false;
    const dbg = $("#mfa-debug");
    const codeInput = $("#form-mfa input[name=code]");
    if (res.debug_code) {
      // Só vem preenchido quando APP_ENV=development.
      dbg.textContent = "Modo desenvolvimento — código MFA: " + res.debug_code;
      dbg.hidden = false;
      codeInput.value = res.debug_code;
    } else {
      dbg.hidden = true;
      codeInput.value = "";
    }
    codeInput.focus();
  } catch (err) {
    showAuthError(err.message);
  } finally {
    btn.disabled = false;
  }
});

$("#mfa-back").addEventListener("click", () => {
  state.challengeId = null;
  $("#auth-tabs").hidden = false;
  setAuthMode("login");
});

$("#form-mfa").addEventListener("submit", async (e) => {
  e.preventDefault();
  showAuthError("");
  const f = e.currentTarget;
  const btn = $("button[type=submit]", f);
  btn.disabled = true;
  try {
    const res = await api("/api/auth/verify-mfa", {
      method: "POST", auth: false,
      body: { challenge_id: state.challengeId, code: formData(f).code.trim() },
    });
    state.token = res.access_token;
    sessionStorage.setItem("st_token", state.token);
    f.reset();
    await enterApp();
  } catch (err) {
    showAuthError(err.message);
  } finally {
    btn.disabled = false;
  }
});

$("#form-register").addEventListener("submit", async (e) => {
  e.preventDefault();
  showAuthError("");
  const f = e.currentTarget;
  const btn = $("button[type=submit]", f);
  btn.disabled = true;
  try {
    await api("/api/investors", { method: "POST", auth: false, body: formData(f) });
    f.reset();
    setAuthMode("login");
    toast("Conta criada! Entre com seu e-mail e senha.");
  } catch (err) {
    showAuthError(err.message);
  } finally {
    btn.disabled = false;
  }
});

function logout(message) {
  state.token = null;
  state.user = null;
  state.challengeId = null;
  sessionStorage.removeItem("st_token");
  $("#view-app").hidden = true;
  $("#view-auth").hidden = false;
  $("#auth-tabs").hidden = false;
  setAuthMode("login");
  if (message) showAuthError(message);
}
$("#btn-logout").addEventListener("click", () => logout());

/* ===================== Navegação por abas ===================== */
const TABS = [
  { id: "resumo", label: "Resumo", roles: "*", load: loadResumo },
  { id: "ordem", label: "Nova ordem", roles: ["INVESTOR"], load: loadOrderForm },
  { id: "ordens", label: "Minhas ordens", roles: ["INVESTOR"], load: loadOrders },
  { id: "notif", label: "Notificações", roles: "*", load: loadNotifications },
  { id: "corretora", label: "Corretora", roles: ["ADMIN", "RISK_ANALYST"], load: null },
  { id: "admin", label: "Administração", roles: ["ADMIN"], load: null },
  { id: "auditoria", label: "Auditoria", roles: ["ADMIN", "AUDITOR"], load: loadAudit },
];

const allowedTabs = () => TABS.filter((t) => t.roles === "*" || t.roles.includes(state.user.role));

function buildTabs() {
  const nav = $("#tabs");
  nav.replaceChildren(...allowedTabs().map((t) =>
    h("button", { type: "button", "data-tab": t.id, text: t.label, onclick: () => openTab(t.id) })));
}

async function openTab(id) {
  const tab = TABS.find((t) => t.id === id);
  if (!tab) return;
  state.activeTab = id;
  $$("#tabs button").forEach((b) => b.classList.toggle("active", b.dataset.tab === id));
  $$(".panel").forEach((p) => { p.hidden = p.id !== "panel-" + id; });
  if (tab.load) {
    try { await tab.load(); } catch (err) { toast(err.message, true); }
  }
}

$$("[data-refresh]").forEach((b) => b.addEventListener("click", () => openTab(b.dataset.refresh)));

async function enterApp() {
  try {
    state.user = await api("/api/investors/me");
  } catch {
    logout();
    return;
  }
  $("#view-auth").hidden = true;
  $("#view-app").hidden = false;
  $("#user-name").textContent = state.user.name;
  $("#user-role").textContent = ROLE_LABEL[state.user.role] || state.user.role;
  buildTabs();
  await openTab("resumo");
}

/* ===================== Resumo ===================== */
async function fetchAssets() {
  state.assets = await api("/api/assets");
  return state.assets;
}

async function loadResumo() {
  const [pf, assets] = await Promise.all([api("/api/portfolio"), fetchAssets()]);
  $("#balance").textContent = money(pf.balance);
  $("#pos-count").textContent = String(pf.positions.length);

  renderTable($("#tbl-positions"), [
    { label: "Ativo", key: "symbol" },
    { label: "Quantidade", key: "quantity", num: true },
    { label: "Reservada", key: "reserved_quantity", num: true },
    { label: "Disponível", key: "available", num: true },
  ], pf.positions, "Você ainda não possui posições.");

  const cols = [
    { label: "Ativo", key: "symbol" },
    { label: "Nome", key: "name" },
    { label: "Preço", num: true, render: (a) => money(a.price) },
    { label: "Cotação em", render: (a) => fmtDate(a.quote_at) },
  ];
  if (state.user.role === "ADMIN") cols.unshift({ label: "ID", key: "id", num: true });
  renderTable($("#tbl-assets"), cols, assets, "Nenhum ativo disponível.");
}

/* ===================== Nova ordem ===================== */
const newIdemKey = () =>
  (crypto.randomUUID ? crypto.randomUUID() : Date.now() + "-" + Math.random().toString(16).slice(2));

function currentAsset() {
  return state.assets.find((a) => a.symbol === $("#order-symbol").value);
}

function updateOrderHints() {
  const asset = currentAsset();
  const form = $("#form-order");
  const qty = parseInt(form.quantity.value, 10) || 0;
  const isLimit = $("#order-type").value === "LIMIT";
  $("#limit-wrap").hidden = !isLimit;
  form.limit_price.required = isLimit;

  $("#order-quote").textContent = asset ? `Cotação atual: ${money(asset.price)}` : "";
  const price = isLimit ? parseFloat(num(form.limit_price.value)) : asset ? Number(asset.price) : NaN;
  $("#order-total").textContent = price > 0 && qty > 0 ? `Valor estimado: ${money(price * qty)}` : "";
}

async function loadOrderForm() {
  const assets = await fetchAssets();
  const select = $("#order-symbol");
  const previous = select.value;
  select.replaceChildren(...assets.map((a) => h("option", { value: a.symbol, text: `${a.symbol} — ${a.name}` })));
  if (assets.some((a) => a.symbol === previous)) select.value = previous;
  if (!state.idemKey) state.idemKey = newIdemKey();
  updateOrderHints();
}

$("#side-seg").addEventListener("click", (e) => {
  const btn = e.target.closest("button[data-side]");
  if (!btn) return;
  state.side = btn.dataset.side;
  $$("#side-seg button").forEach((b) => b.classList.toggle("active", b === btn));
});
["#order-symbol", "#order-type"].forEach((s) => $(s).addEventListener("change", updateOrderHints));
["quantity", "limit_price"].forEach((n) => $("#form-order")[n].addEventListener("input", updateOrderHints));

$("#form-order").addEventListener("submit", (e) => {
  e.preventDefault();
  const f = e.currentTarget;
  submitting(f, async () => {
    const d = formData(f);
    const body = {
      symbol: d.symbol,
      side: state.side,
      quantity: parseInt(d.quantity, 10),
      order_type: d.order_type,
      limit_price: d.order_type === "LIMIT" ? num(d.limit_price) : null,
      idempotency_key: state.idemKey,
      pin: d.pin,
    };
    try {
      const order = await api("/api/orders", { method: "POST", body });
      toast(`Ordem #${order.id} enviada (${STATUS_LABEL[order.status] || order.status}).`);
      f.pin.value = "";
      state.idemKey = newIdemKey();
      await openTab("ordens");
    } catch (err) {
      // Falha de rede: mantém a mesma chave para um reenvio seguro (idempotência).
      // Qualquer resposta do servidor (inclusive erro): nova chave, pois a anterior pode já estar gravada.
      if (!err.network) state.idemKey = newIdemKey();
      f.pin.value = "";
      throw err;
    }
  });
});

/* ===================== Ordens ===================== */
function orderRows(order) {
  const rows = [];
  const detailRow = h("tr", { class: "detail", hidden: true },
    h("td", { colspan: "10" },
      order.rejection_reason ? h("p", { class: "error", text: "Motivo: " + order.rejection_reason }) : null,
      h("strong", { text: "Histórico" }),
      h("ul", { class: "timeline" }, order.events.map((ev) =>
        h("li", { text: `${fmtDate(ev.at)} — ${ev.from ? STATUS_LABEL[ev.from] + " → " : ""}${STATUS_LABEL[ev.to] || ev.to}${ev.message ? " · " + ev.message : ""}` })))));

  const actions = h("td", {},
    h("button", {
      class: "ghost small", type: "button", text: "Detalhes",
      onclick: () => { detailRow.hidden = !detailRow.hidden; },
    }),
    " ",
    CANCELLABLE.includes(order.status)
      ? h("button", { class: "danger small", type: "button", text: "Cancelar", onclick: (e) => cancelOrder(order.id, e.currentTarget) })
      : null);

  rows.push(h("tr", {},
    h("td", { class: "num", text: order.id }),
    h("td", { text: order.symbol }),
    h("td", { class: "side-" + order.side, text: order.side === "BUY" ? "Compra" : "Venda" }),
    h("td", { text: order.type === "LIMIT" ? "Limitada" : "Mercado" }),
    h("td", { class: "num", text: order.quantity }),
    h("td", { class: "num", text: order.filled_quantity }),
    h("td", { class: "num", text: money(order.price) }),
    h("td", {}, h("span", { class: "status " + order.status, text: STATUS_LABEL[order.status] || order.status })),
    h("td", { text: fmtDate(order.created_at) }),
    actions));
  rows.push(detailRow);
  return rows;
}

async function loadOrders() {
  const orders = await api("/api/orders?limit=100");
  const table = $("#tbl-orders");
  table.replaceChildren();
  if (!orders.length) {
    table.append(h("caption", { class: "empty", text: "Você ainda não enviou ordens." }));
    return;
  }
  const heads = ["ID", "Ativo", "Lado", "Tipo", "Qtd", "Executada", "Preço ref.", "Status", "Criada em", ""];
  table.append(
    h("thead", {}, h("tr", {}, heads.map((t, i) => h("th", { class: [4, 5, 6].includes(i) ? "num" : "", text: t })))),
    h("tbody", {}, orders.flatMap(orderRows)));
}

async function cancelOrder(id, button) {
  if (!confirm(`Cancelar a ordem #${id}?`)) return;
  button.disabled = true;
  try {
    await api(`/api/orders/${id}/cancel`, { method: "POST" });
    toast(`Ordem #${id} cancelada.`);
    await loadOrders();
  } catch (err) {
    toast(err.message, true);
    button.disabled = false;
  }
}

/* ===================== Notificações ===================== */
async function loadNotifications() {
  const items = await api("/api/notifications?limit=100");
  const list = $("#list-notif");
  list.replaceChildren(...(items.length
    ? items.map((n) => h("li", {}, h("span", { text: n.message }), h("time", { text: fmtDate(n.created_at) })))
    : [h("li", { class: "empty", text: "Nenhuma notificação." })]));
}

/* ===================== Corretora (Admin / Risco) ===================== */
$("#form-broker").addEventListener("submit", (e) => {
  e.preventDefault();
  const f = e.currentTarget;
  submitting(f, async () => {
    const d = formData(f);
    const order = await api(`/api/orders/${parseInt(d.order_id, 10)}/broker-update`, {
      method: "POST",
      body: { status: d.status, filled_quantity: parseInt(d.filled_quantity, 10) || 0, message: d.message },
    });
    const out = $("#broker-result");
    out.textContent = `Ordem #${order.id} (${order.symbol}) → ${order.status}\nExecutado: ${order.filled_quantity}/${order.quantity}`;
    out.hidden = false;
    toast(`Retorno aplicado à ordem #${order.id}.`);
  });
});

/* ===================== Administração ===================== */
const boolOrUndef = (v) => (v === "" ? undefined : v === "true");
const clean = (obj) => Object.fromEntries(Object.entries(obj).filter(([, v]) => v !== undefined && v !== ""));

$("#form-asset-new").addEventListener("submit", (e) => {
  e.preventDefault();
  const f = e.currentTarget;
  submitting(f, async () => {
    const d = formData(f);
    const res = await api("/api/assets", {
      method: "POST",
      body: { symbol: d.symbol.trim().toUpperCase(), name: d.name.trim(), price: num(d.price) },
    });
    toast(`Ativo ${res.symbol} cadastrado (ID ${res.id}).`);
    f.reset();
  });
});

$("#form-asset-edit").addEventListener("submit", (e) => {
  e.preventDefault();
  const f = e.currentTarget;
  submitting(f, async () => {
    const d = formData(f);
    const body = clean({ name: d.name.trim(), price: d.price ? num(d.price) : "", active: boolOrUndef(d.active) });
    if (!Object.keys(body).length) throw new Error("Informe ao menos um campo para alterar.");
    const res = await api(`/api/assets/${parseInt(d.asset_id, 10)}`, { method: "PATCH", body });
    toast(`Ativo ${res.symbol} atualizado.`);
    f.reset();
  });
});

$("#form-investor").addEventListener("submit", (e) => {
  e.preventDefault();
  const f = e.currentTarget;
  submitting(f, async () => {
    const d = formData(f);
    const body = clean({ name: d.name.trim(), active: boolOrUndef(d.active) });
    if (!Object.keys(body).length) throw new Error("Informe ao menos um campo para alterar.");
    const res = await api(`/api/investors/${parseInt(d.investor_id, 10)}`, { method: "PATCH", body });
    toast(`Investidor #${res.id} atualizado.`);
    f.reset();
  });
});

$("#form-risk").addEventListener("submit", (e) => {
  e.preventDefault();
  const f = e.currentTarget;
  submitting(f, async () => {
    const d = formData(f);
    const res = await api(`/api/admin/investors/${parseInt(d.investor_id, 10)}/risk-limits`, {
      method: "PATCH",
      body: { daily_order_limit: num(d.daily_order_limit), daily_exposure_limit: num(d.daily_exposure_limit) },
    });
    toast(`Limites do investidor #${res.investor_id} atualizados.`);
    f.reset();
  });
});

/* ===================== Auditoria ===================== */
async function loadAudit() {
  const d = formData($("#form-audit"));
  const params = new URLSearchParams();
  if (d.investor_id) params.set("investor_id", d.investor_id);
  if (d.event_type && d.event_type.trim()) params.set("event_type", d.event_type.trim());
  params.set("limit", d.limit || "100");
  const rows = await api("/api/audit?" + params.toString());
  renderTable($("#tbl-audit"), [
    { label: "ID", key: "id", num: true },
    { label: "Data", render: (r) => fmtDate(r.created_at) },
    { label: "Evento", key: "event_type" },
    { label: "Investidor", render: (r) => r.investor_id ?? "—", num: true },
    { label: "Ordem", render: (r) => r.order_id ?? "—", num: true },
    { label: "Detalhes", key: "details", wrap: true },
  ], rows, "Nenhum registro encontrado.");
}

$("#form-audit").addEventListener("submit", (e) => {
  e.preventDefault();
  submitting(e.currentTarget, loadAudit);
});

/* ===================== Início ===================== */
(async function boot() {
  if (state.token) await enterApp();
})();

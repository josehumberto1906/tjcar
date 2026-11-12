"use strict";

/* =====================================================================
   TJ Car - interface da oficina (site que funciona no PC e no celular)
   ===================================================================== */

const $ = (seletor, raiz = document) => raiz.querySelector(seletor);
const tela = $("#tela");
const modal = $("#modal");
const modalForm = $("#modal-form");

const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
));
const moeda = (v) => Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const dataBr = (iso) => (iso ? new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "");
const numeroBr = (v) => Number(v || 0).toLocaleString("pt-BR");

const STATUS = {
  aberta: "Aberta",
  em_andamento: "Em andamento",
  concluida: "Concluída",
  cancelada: "Cancelada",
};
const seloStatus = (s) => `<span class="selo ${esc(s)}">${esc(STATUS[s] || s)}</span>`;

/* ---------- API ---------- */
async function api(metodo, url, corpo) {
  const resp = await fetch(url, {
    method: metodo,
    headers: corpo ? { "Content-Type": "application/json" } : {},
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  if (resp.status === 204) return null;
  let dados = null;
  try { dados = await resp.json(); } catch { /* resposta sem corpo */ }
  if (!resp.ok) throw new Error((dados && dados.erro) || "Algo deu errado. Tente novamente.");
  return dados;
}

/* ---------- avisos ---------- */
let temporizadorAviso;
function aviso(mensagem, erro = false) {
  const el = $("#aviso");
  el.textContent = mensagem;
  el.className = "aviso" + (erro ? " erro" : "");
  el.hidden = false;
  clearTimeout(temporizadorAviso);
  temporizadorAviso = setTimeout(() => { el.hidden = true; }, 3500);
}

/* ---------- menu ---------- */
const ICONES = {
  painel: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
  ordens: '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1"/><line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="16" x2="15" y2="16"/>',
  clientes: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  veiculos: '<path d="M5 17H3v-5l2-5h12l3 5v5h-2"/><circle cx="7.5" cy="17" r="2"/><circle cx="16.5" cy="17" r="2"/><path d="M9.5 17h5"/>',
  estoque: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
  servicos: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
};
const ITENS_MENU = [
  ["painel", "Painel"],
  ["ordens", "Ordens"],
  ["clientes", "Clientes"],
  ["veiculos", "Veículos"],
  ["estoque", "Estoque"],
  ["servicos", "Serviços"],
];

function montarMenu() {
  $("#menu").innerHTML =
    `<div class="marca"><img src="/static/icon.svg" alt=""><div>TJ Car<small>Gestão da oficina</small></div></div>` +
    ITENS_MENU.map(([id, nome]) =>
      `<a href="#/${id}" data-rota="${id}"><svg viewBox="0 0 24 24" aria-hidden="true">${ICONES[id]}</svg><span>${nome}</span></a>`
    ).join("");
}

function marcarMenu(rota) {
  document.querySelectorAll("#menu a").forEach((a) => {
    a.classList.toggle("ativo", a.dataset.rota === rota);
    if (a.dataset.rota === rota) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
}

function definirTopo(titulo, acoesHtml = "") {
  $("#titulo-pagina").textContent = titulo;
  document.title = `${titulo} · TJ Car`;
  $("#topo-acoes").innerHTML = acoesHtml;
}

/* ---------- formulários e modal ---------- */
function campoHtml(c, valores = {}) {
  const valor = valores[c.nome] ?? c.padrao ?? "";
  const req = c.obrig ? "required" : "";
  let entrada;
  if (c.tipo === "select") {
    entrada = `<select name="${c.nome}" ${req}><option value="">Selecione…</option>` +
      c.opcoes.map((o) =>
        `<option value="${esc(o.valor)}" ${String(o.valor) === String(valor) ? "selected" : ""}>${esc(o.texto)}</option>`
      ).join("") + "</select>";
  } else if (c.tipo === "textarea") {
    entrada = `<textarea name="${c.nome}" ${req}>${esc(valor)}</textarea>`;
  } else {
    entrada = `<input name="${c.nome}" type="${c.tipo || "text"}" value="${esc(valor)}" ${req} ${c.attrs || ""}>`;
  }
  return `<label class="campo ${c.larga ? "larga" : ""}"><span>${esc(c.rotulo)}${c.obrig ? " *" : ""}</span>${entrada}</label>`;
}

const camposHtml = (campos, valores) => `<div class="campos">${campos.map((c) => campoHtml(c, valores)).join("")}</div>`;

function coletar(form) {
  const dados = {};
  for (const el of form.elements) {
    if (el.name) dados[el.name] = el.value;
  }
  return dados;
}

function abrirModal(titulo, corpoHtml, aoEnviar, textoBotao = "Salvar") {
  $("#modal-titulo").textContent = titulo;
  $("#modal-corpo").innerHTML =
    `<div id="modal-erro" class="erro-caixa" hidden></div>${corpoHtml}` +
    `<footer class="modal-rodape"><button type="button" class="btn" id="modal-cancelar">Cancelar</button>` +
    `<button type="submit" class="btn primario" id="modal-salvar">${esc(textoBotao)}</button></footer>`;
  const mostrarErro = (msg) => {
    const caixa = $("#modal-erro");
    caixa.textContent = msg;
    caixa.hidden = false;
  };
  modalForm.onsubmit = async (ev) => {
    ev.preventDefault();
    const botao = $("#modal-salvar");
    botao.disabled = true;
    try {
      await aoEnviar(coletar(modalForm));
      modal.close();
    } catch (e) {
      mostrarErro(e.message);
    } finally {
      botao.disabled = false;
    }
  };
  $("#modal-cancelar").onclick = () => modal.close();
  modal.showModal();
  const primeiro = $("#modal-corpo input, #modal-corpo select, #modal-corpo textarea");
  if (primeiro) primeiro.focus();
}

$("#modal-fechar").onclick = () => modal.close();
modal.addEventListener("click", (ev) => { if (ev.target === modal) modal.close(); });

/* ---------- lista de cadastros (clientes, veículos, estoque, serviços) ---------- */
async function paginaCadastro(cfg) {
  definirTopo(cfg.titulo, `<button class="btn primario" id="novo">+ ${esc(cfg.novo)}</button>`);
  tela.innerHTML =
    `<div class="barra"><input type="search" id="busca" placeholder="Buscar…" aria-label="Buscar"></div>` +
    `<div class="cartao tabela-cartao" id="lista"></div>`;

  let registros = [];

  async function carregar() {
    const busca = $("#busca").value.trim();
    registros = await api("GET", `/api/${cfg.recurso}?busca=${encodeURIComponent(busca)}`);
    desenhar();
  }

  function desenhar() {
    const lista = $("#lista");
    if (!registros.length) {
      lista.innerHTML = `<div class="vazio">${esc(cfg.vazio)}</div>`;
      return;
    }
    const cab = cfg.colunas.map((c) => `<th class="${c.num ? "num" : ""}">${esc(c.titulo)}</th>`).join("") + `<th class="acoes"></th>`;
    const linhas = registros.map((r) =>
      `<tr>` +
      cfg.colunas.map((c, i) =>
        `<td data-rotulo="${esc(c.titulo)}" ${i === 0 ? "data-principal" : ""} class="${c.num ? "num" : ""}">${c.valor(r)}</td>`
      ).join("") +
      `<td class="acoes"><button class="btn pequeno" data-editar="${r.id}">Editar</button>` +
      `<button class="btn pequeno perigo" data-excluir="${r.id}">Excluir</button></td></tr>`
    ).join("");
    lista.innerHTML = `<table><thead><tr>${cab}</tr></thead><tbody>${linhas}</tbody></table>`;
  }

  async function formulario(registro) {
    const campos = await cfg.campos();
    abrirModal(
      registro ? `Editar ${cfg.singular}` : cfg.novo,
      camposHtml(campos, registro || {}),
      async (dados) => {
        if (registro) await api("PUT", `/api/${cfg.recurso}/${registro.id}`, dados);
        else await api("POST", `/api/${cfg.recurso}`, dados);
        aviso("Salvo com sucesso.");
        await carregar();
      }
    );
  }

  $("#novo").onclick = () => formulario(null).catch((e) => aviso(e.message, true));

  let espera;
  $("#busca").oninput = () => {
    clearTimeout(espera);
    espera = setTimeout(() => carregar().catch((e) => aviso(e.message, true)), 250);
  };

  $("#lista").onclick = async (ev) => {
    const editar = ev.target.closest("[data-editar]");
    const excluir = ev.target.closest("[data-excluir]");
    try {
      if (editar) {
        await formulario(registros.find((r) => r.id === Number(editar.dataset.editar)));
      } else if (excluir) {
        const r = registros.find((x) => x.id === Number(excluir.dataset.excluir));
        if (!confirm(`Excluir ${cfg.singular} "${cfg.rotulo(r)}"?`)) return;
        await api("DELETE", `/api/${cfg.recurso}/${r.id}`);
        aviso("Excluído.");
        await carregar();
      }
    } catch (e) {
      aviso(e.message, true);
    }
  };

  await carregar();
}

const CADASTROS = {
  clientes: {
    titulo: "Clientes", singular: "cliente", novo: "Novo cliente", recurso: "clientes",
    vazio: "Nenhum cliente cadastrado ainda.",
    rotulo: (r) => r.nome,
    colunas: [
      { titulo: "Nome", valor: (r) => esc(r.nome) },
      { titulo: "Telefone", valor: (r) => esc(r.telefone) || "—" },
      { titulo: "E-mail", valor: (r) => esc(r.email) || "—" },
      { titulo: "Veículos", num: true, valor: (r) => numeroBr(r.total_veiculos) },
    ],
    campos: async () => [
      { nome: "nome", rotulo: "Nome", obrig: true, larga: true, attrs: 'autocomplete="off"' },
      { nome: "telefone", rotulo: "Telefone / WhatsApp", tipo: "tel" },
      { nome: "email", rotulo: "E-mail", tipo: "email" },
    ],
  },
  veiculos: {
    titulo: "Veículos", singular: "veículo", novo: "Novo veículo", recurso: "veiculos",
    vazio: "Nenhum veículo cadastrado ainda.",
    rotulo: (r) => r.placa,
    colunas: [
      { titulo: "Placa", valor: (r) => `<strong>${esc(r.placa)}</strong>` },
      { titulo: "Veículo", valor: (r) => esc(`${r.marca} ${r.modelo}`.trim()) },
      { titulo: "Ano", valor: (r) => esc(r.ano || "—") },
      { titulo: "Km", num: true, valor: (r) => numeroBr(r.km) },
      { titulo: "Cliente", valor: (r) => esc(r.cliente_nome) },
    ],
    campos: async () => {
      const clientes = await api("GET", "/api/clientes");
      if (!clientes.length) throw new Error("Cadastre um cliente antes de cadastrar um veículo.");
      return [
        { nome: "cliente_id", rotulo: "Cliente", tipo: "select", obrig: true, larga: true,
          opcoes: clientes.map((c) => ({ valor: c.id, texto: c.nome })) },
        { nome: "placa", rotulo: "Placa", obrig: true, attrs: 'maxlength="10" style="text-transform:uppercase" autocomplete="off"' },
        { nome: "marca", rotulo: "Marca" },
        { nome: "modelo", rotulo: "Modelo", obrig: true },
        { nome: "ano", rotulo: "Ano", tipo: "number", attrs: 'min="1900" max="2100" inputmode="numeric"' },
        { nome: "km", rotulo: "Quilometragem", tipo: "number", attrs: 'min="0" inputmode="numeric"' },
      ];
    },
  },
  estoque: {
    titulo: "Estoque de peças", singular: "peça", novo: "Nova peça", recurso: "pecas",
    vazio: "Nenhuma peça cadastrada ainda.",
    rotulo: (r) => r.nome,
    colunas: [
      { titulo: "Peça", valor: (r) => `${esc(r.nome)} <small style="color:var(--suave)">${esc(r.codigo)}</small>` },
      { titulo: "Preço", num: true, valor: (r) => moeda(r.preco) },
      { titulo: "Em estoque", num: true, valor: (r) => numeroBr(r.quantidade) },
      { titulo: "Mínimo", num: true, valor: (r) => numeroBr(r.minimo) },
      { titulo: "Situação", valor: (r) => (r.quantidade <= r.minimo
        ? '<span class="selo baixo">Repor</span>' : '<span class="selo normal">Ok</span>') },
    ],
    campos: async () => [
      { nome: "codigo", rotulo: "Código", obrig: true, attrs: 'autocomplete="off"' },
      { nome: "nome", rotulo: "Nome da peça", obrig: true },
      { nome: "preco", rotulo: "Preço de venda (R$)", tipo: "number", attrs: 'min="0" step="0.01" inputmode="decimal"' },
      { nome: "quantidade", rotulo: "Quantidade em estoque", tipo: "number", attrs: 'min="0" inputmode="numeric"', padrao: 0 },
      { nome: "minimo", rotulo: "Estoque mínimo (alerta)", tipo: "number", attrs: 'min="0" inputmode="numeric"', padrao: 0 },
    ],
  },
  servicos: {
    titulo: "Catálogo de serviços", singular: "serviço", novo: "Novo serviço", recurso: "servicos",
    vazio: "Nenhum serviço no catálogo. Cadastre os mais comuns (troca de óleo, alinhamento…) para agilizar as ordens.",
    rotulo: (r) => r.descricao,
    colunas: [
      { titulo: "Serviço", valor: (r) => esc(r.descricao) },
      { titulo: "Preço padrão", num: true, valor: (r) => moeda(r.preco) },
    ],
    campos: async () => [
      { nome: "descricao", rotulo: "Descrição do serviço", obrig: true, larga: true },
      { nome: "preco", rotulo: "Preço padrão (R$)", tipo: "number", attrs: 'min="0" step="0.01" inputmode="decimal"' },
    ],
  },
};

/* ---------- painel ---------- */
async function paginaPainel() {
  definirTopo("Painel", `<a class="btn primario" href="#/ordens?nova=1" style="text-decoration:none;display:inline-flex;align-items:center">+ Nova ordem</a>`);
  const [p, ordens] = await Promise.all([api("GET", "/api/painel"), api("GET", "/api/ordens")]);
  const ativas = ordens.filter((o) => o.status === "aberta" || o.status === "em_andamento").slice(0, 6);

  tela.innerHTML =
    `<div class="grade-indicadores">
      <div class="indicador destaque"><span>Faturamento do mês</span><strong>${moeda(p.faturamento_mes)}</strong></div>
      <div class="indicador"><span>Ordens abertas</span><strong>${numeroBr(p.ordens_abertas)}</strong></div>
      <div class="indicador"><span>Em andamento</span><strong>${numeroBr(p.ordens_andamento)}</strong></div>
      <div class="indicador"><span>Concluídas no mês</span><strong>${numeroBr(p.concluidas_mes)}</strong></div>
      <div class="indicador"><span>Clientes</span><strong>${numeroBr(p.clientes)}</strong></div>
      <div class="indicador"><span>Veículos</span><strong>${numeroBr(p.veiculos)}</strong></div>
    </div>
    <div class="cartao tabela-cartao">
      <h2 style="padding:18px 18px 0">Serviços em aberto</h2>
      ${ativas.length ? tabelaOrdens(ativas) : '<div class="vazio">Nenhuma ordem em aberto. Tudo em dia!</div>'}
    </div>
    <div class="cartao">
      <h2>Peças para repor</h2>
      ${p.estoque_baixo.length
        ? `<table><thead><tr><th>Peça</th><th class="num">Em estoque</th><th class="num">Mínimo</th></tr></thead><tbody>` +
          p.estoque_baixo.map((x) =>
            `<tr><td data-rotulo="Peça" data-principal>${esc(x.nome)} <small style="color:var(--suave)">${esc(x.codigo)}</small></td>` +
            `<td class="num" data-rotulo="Em estoque"><span class="selo baixo">${numeroBr(x.quantidade)}</span></td>` +
            `<td class="num" data-rotulo="Mínimo">${numeroBr(x.minimo)}</td></tr>`
          ).join("") + `</tbody></table>`
        : '<div class="vazio">Estoque sem alertas.</div>'}
    </div>`;
  ligarLinhasOrdens();
}

/* ---------- ordens de serviço ---------- */
function tabelaOrdens(ordens) {
  return `<table><thead><tr><th>Nº</th><th>Veículo</th><th>Cliente</th><th>Status</th><th>Abertura</th><th class="num">Total</th></tr></thead><tbody>` +
    ordens.map((o) =>
      `<tr class="clicavel" data-ordem="${o.id}">` +
      `<td data-rotulo="Nº" data-principal>#${o.id} · ${esc(o.placa)}</td>` +
      `<td data-rotulo="Veículo">${esc(`${o.marca} ${o.modelo}`.trim())}</td>` +
      `<td data-rotulo="Cliente">${esc(o.cliente_nome)}</td>` +
      `<td data-rotulo="Status">${seloStatus(o.status)}</td>` +
      `<td data-rotulo="Abertura">${dataBr(o.criado_em)}</td>` +
      `<td class="num" data-rotulo="Total">${moeda(o.total)}</td></tr>`
    ).join("") + `</tbody></table>`;
}

function ligarLinhasOrdens() {
  tela.querySelectorAll("tr[data-ordem]").forEach((tr) => {
    tr.onclick = () => { location.hash = `#/ordens/${tr.dataset.ordem}`; };
  });
}

async function novaOrdem() {
  const veiculos = await api("GET", "/api/veiculos");
  if (!veiculos.length) {
    aviso("Cadastre um veículo antes de abrir uma ordem.", true);
    return;
  }
  const campos = [
    { nome: "veiculo_id", rotulo: "Veículo", tipo: "select", obrig: true, larga: true,
      opcoes: veiculos.map((v) => ({ valor: v.id, texto: `${v.placa} · ${`${v.marca} ${v.modelo}`.trim()} · ${v.cliente_nome}` })) },
    { nome: "km_entrada", rotulo: "Quilometragem atual", tipo: "number", attrs: 'min="0" inputmode="numeric"' },
    { nome: "defeito", rotulo: "Defeito relatado / o que o cliente pediu", tipo: "textarea", larga: true },
  ];
  abrirModal("Nova ordem de serviço", camposHtml(campos), async (dados) => {
    const o = await api("POST", "/api/ordens", dados);
    aviso(`Ordem #${o.id} aberta.`);
    location.hash = `#/ordens/${o.id}`;
  }, "Abrir ordem");
}

async function paginaOrdens(params) {
  definirTopo("Ordens de serviço", `<button class="btn primario" id="nova-ordem">+ Nova ordem</button>`);
  tela.innerHTML =
    `<div class="filtros" id="filtros"></div>
     <div class="barra"><input type="search" id="busca" placeholder="Buscar por placa, cliente, modelo ou defeito…" aria-label="Buscar"></div>
     <div class="cartao tabela-cartao" id="lista"></div>`;

  let filtro = "";
  const opcoes = [["", "Todas"], ...Object.entries(STATUS)];
  $("#filtros").innerHTML = opcoes.map(([v, t]) =>
    `<button class="filtro ${v === filtro ? "ativo" : ""}" data-status="${v}">${t}</button>`).join("");

  async function carregar() {
    const busca = $("#busca").value.trim();
    const ordens = await api("GET", `/api/ordens?status=${filtro}&busca=${encodeURIComponent(busca)}`);
    $("#lista").innerHTML = ordens.length ? tabelaOrdens(ordens) : '<div class="vazio">Nenhuma ordem encontrada.</div>';
    ligarLinhasOrdens();
  }

  $("#filtros").onclick = (ev) => {
    const b = ev.target.closest("[data-status]");
    if (!b) return;
    filtro = b.dataset.status;
    document.querySelectorAll(".filtro").forEach((x) => x.classList.toggle("ativo", x === b));
    carregar().catch((e) => aviso(e.message, true));
  };
  let espera;
  $("#busca").oninput = () => {
    clearTimeout(espera);
    espera = setTimeout(() => carregar().catch((e) => aviso(e.message, true)), 250);
  };
  $("#nova-ordem").onclick = () => novaOrdem().catch((e) => aviso(e.message, true));

  await carregar();
  if (params.get("nova")) {
    history.replaceState(null, "", "#/ordens");
    await novaOrdem();
  }
}

async function paginaOrdem(id) {
  const [o, catalogo, pecas] = await Promise.all([
    api("GET", `/api/ordens/${id}`), api("GET", "/api/servicos"), api("GET", "/api/pecas"),
  ]);
  definirTopo(`Ordem #${o.id}`,
    `<a class="btn" href="#/ordens" style="text-decoration:none;display:inline-flex;align-items:center">← Voltar</a>` +
    `<button class="btn" id="imprimir">Imprimir</button>`);

  const editavel = o.editavel;
  const rotuloStatus = { em_andamento: "Iniciar serviço", concluida: "Concluir", cancelada: "Cancelar ordem" };

  const linhasServicos = o.servicos.map((s) =>
    `<tr><td data-rotulo="Serviço" data-principal>${esc(s.descricao)}</td>` +
    `<td class="num" data-rotulo="Valor">${moeda(s.preco)}</td>` +
    `<td class="acoes">${editavel ? `<button class="btn pequeno perigo" data-del-servico="${s.id}">Remover</button>` : ""}</td></tr>`
  ).join("");

  const linhasPecas = o.pecas.map((p) =>
    `<tr><td data-rotulo="Peça" data-principal>${esc(p.nome)} <small style="color:var(--suave)">${esc(p.codigo)}</small></td>` +
    `<td class="num" data-rotulo="Qtd">${numeroBr(p.quantidade)}</td>` +
    `<td class="num" data-rotulo="Unitário">${moeda(p.preco_unitario)}</td>` +
    `<td class="num" data-rotulo="Subtotal">${moeda(p.quantidade * p.preco_unitario)}</td>` +
    `<td class="acoes">${editavel ? `<button class="btn pequeno perigo" data-del-peca="${p.id}">Remover</button>` : ""}</td></tr>`
  ).join("");

  tela.innerHTML =
    `<div class="somente-impressao"><h2>TJ Car · Ordem de serviço #${o.id}</h2></div>
    <div class="cartao">
      <div class="ordem-cab">
        <div>
          <h2>${esc(o.placa)} · ${esc(`${o.marca} ${o.modelo}`.trim())}</h2>
          <p>Cliente: <b>${esc(o.cliente_nome)}</b>${o.cliente_telefone ? ` · ${esc(o.cliente_telefone)}` : ""}</p>
          <p>Aberta em <b>${dataBr(o.criado_em)}</b> · Km na entrada: <b>${numeroBr(o.km_entrada)}</b></p>
          ${o.concluido_em ? `<p>Concluída em <b>${dataBr(o.concluido_em)}</b></p>` : ""}
        </div>
        <div>${seloStatus(o.status)}</div>
      </div>
      ${o.proximos_status.length
        ? `<div class="acoes-status">` + ["em_andamento", "concluida", "cancelada"].filter((s) => o.proximos_status.includes(s)).map((s) =>
            `<button class="btn ${s === "concluida" ? "primario" : s === "cancelada" ? "perigo" : ""}" data-status="${s}">${rotuloStatus[s]}</button>`
          ).join("") + `</div>`
        : ""}
    </div>

    <div class="cartao">
      <h2>Defeito relatado</h2>
      ${editavel
        ? `<textarea id="defeito" placeholder="Descreva o problema ou o que o cliente pediu">${esc(o.defeito)}</textarea>
           <div style="margin-top:10px"><button class="btn pequeno" id="salvar-defeito">Salvar descrição</button></div>`
        : `<p style="margin:0">${esc(o.defeito) || "—"}</p>`}
    </div>

    <div class="cartao tabela-cartao">
      <h2 style="padding:18px 18px 0">Serviços a executar</h2>
      ${o.servicos.length
        ? `<table><thead><tr><th>Serviço</th><th class="num">Valor</th><th class="acoes"></th></tr></thead><tbody>${linhasServicos}</tbody></table>`
        : '<div class="vazio">Nenhum serviço lançado.</div>'}
      ${editavel ? `<form class="form-linha nao-imprimir" id="form-servico" style="padding:0 18px 18px">
          <label class="campo"><span>Serviço</span>
            <input name="descricao" list="catalogo" placeholder="Digite ou escolha do catálogo" required autocomplete="off">
            <datalist id="catalogo">${catalogo.map((s) => `<option value="${esc(s.descricao)}"></option>`).join("")}</datalist></label>
          <label class="campo"><span>Valor (R$)</span><input name="preco" type="number" min="0" step="0.01" inputmode="decimal" placeholder="0,00"></label>
          <button class="btn primario" type="submit">Adicionar</button></form>` : ""}
    </div>

    <div class="cartao tabela-cartao">
      <h2 style="padding:18px 18px 0">Peças utilizadas</h2>
      ${o.pecas.length
        ? `<table><thead><tr><th>Peça</th><th class="num">Qtd</th><th class="num">Unitário</th><th class="num">Subtotal</th><th class="acoes"></th></tr></thead><tbody>${linhasPecas}</tbody></table>`
        : '<div class="vazio">Nenhuma peça lançada.</div>'}
      ${editavel ? `<form class="form-linha peca nao-imprimir" id="form-peca" style="padding:0 18px 18px">
          <label class="campo"><span>Peça (sai do estoque)</span>
            <select name="peca_id" required><option value="">Selecione…</option>
            ${pecas.map((p) => `<option value="${p.id}" ${p.quantidade < 1 ? "disabled" : ""}>${esc(p.nome)} (${esc(p.codigo)}) · ${moeda(p.preco)} · estoque: ${p.quantidade}</option>`).join("")}
            </select></label>
          <label class="campo"><span>Quantidade</span><input name="quantidade" type="number" min="1" value="1" inputmode="numeric" required></label>
          <button class="btn primario" type="submit">Adicionar</button></form>` : ""}
    </div>

    <div class="cartao">
      <div class="totais">
        <div><span>Serviços</span><span>${moeda(o.total_servicos)}</span></div>
        <div><span>Peças</span><span>${moeda(o.total_pecas)}</span></div>
        <div class="geral"><span>Total</span><span>${moeda(o.total)}</span></div>
      </div>
    </div>
    ${o.status === "aberta" || o.status === "cancelada"
      ? `<div style="margin-top:16px" class="nao-imprimir"><button class="btn perigo pequeno" id="excluir-ordem">Excluir esta ordem</button></div>` : ""}`;

  const recarregar = () => paginaOrdem(id).catch((e) => aviso(e.message, true));
  const tentar = (fn) => async (...args) => {
    try { await fn(...args); } catch (e) { aviso(e.message, true); }
  };

  $("#imprimir").onclick = () => window.print();

  tela.querySelectorAll("[data-status]").forEach((b) => {
    b.onclick = tentar(async () => {
      if (b.dataset.status === "cancelada" && !confirm("Cancelar esta ordem? As peças voltam para o estoque.")) return;
      await api("PATCH", `/api/ordens/${id}/status`, { status: b.dataset.status });
      aviso("Status atualizado.");
      await recarregar();
    });
  });

  const salvarDefeito = $("#salvar-defeito");
  if (salvarDefeito) {
    salvarDefeito.onclick = tentar(async () => {
      await api("PUT", `/api/ordens/${id}`, { defeito: $("#defeito").value });
      aviso("Descrição salva.");
    });
  }

  const formServico = $("#form-servico");
  if (formServico) {
    const entradaServico = formServico.elements.descricao;
    entradaServico.addEventListener("input", () => {
      const achado = catalogo.find((s) => s.descricao.toLowerCase() === entradaServico.value.trim().toLowerCase());
      if (achado && !formServico.elements.preco.value) formServico.elements.preco.value = achado.preco;
    });
    formServico.onsubmit = tentar(async (ev) => {
      ev.preventDefault();
      await api("POST", `/api/ordens/${id}/servicos`, coletar(formServico));
      await recarregar();
    });
  }

  const formPeca = $("#form-peca");
  if (formPeca) {
    formPeca.onsubmit = tentar(async (ev) => {
      ev.preventDefault();
      await api("POST", `/api/ordens/${id}/pecas`, coletar(formPeca));
      await recarregar();
    });
  }

  tela.querySelectorAll("[data-del-servico]").forEach((b) => {
    b.onclick = tentar(async () => {
      await api("DELETE", `/api/ordens/${id}/servicos/${b.dataset.delServico}`);
      await recarregar();
    });
  });
  tela.querySelectorAll("[data-del-peca]").forEach((b) => {
    b.onclick = tentar(async () => {
      await api("DELETE", `/api/ordens/${id}/pecas/${b.dataset.delPeca}`);
      aviso("Peça devolvida ao estoque.");
      await recarregar();
    });
  });

  const excluir = $("#excluir-ordem");
  if (excluir) {
    excluir.onclick = tentar(async () => {
      if (!confirm("Excluir esta ordem definitivamente?")) return;
      await api("DELETE", `/api/ordens/${id}`);
      aviso("Ordem excluída.");
      location.hash = "#/ordens";
    });
  }
}

/* ---------- rotas ---------- */
async function rotear() {
  const hash = location.hash || "#/painel";
  const [caminho, consulta = ""] = hash.slice(2).split("?");
  const params = new URLSearchParams(consulta);
  const [base, id] = caminho.split("/");
  marcarMenu(base);
  if (modal.open) modal.close();

  try {
    if (base === "painel") await paginaPainel();
    else if (base === "ordens" && id) await paginaOrdem(Number(id));
    else if (base === "ordens") await paginaOrdens(params);
    else if (CADASTROS[base]) await paginaCadastro(CADASTROS[base]);
    else { location.hash = "#/painel"; return; }
    window.scrollTo(0, 0);
  } catch (e) {
    definirTopo("Ops");
    tela.innerHTML = `<div class="cartao"><div class="erro-caixa">${esc(e.message)}</div><a class="btn" href="#/painel">Ir para o painel</a></div>`;
  }
}

montarMenu();
window.addEventListener("hashchange", rotear);
rotear();

"use strict";

const form = document.getElementById("form-login");
const caixaErro = document.getElementById("login-erro");
const botao = document.getElementById("entrar");

form.addEventListener("submit", async (ev) => {
  ev.preventDefault();
  caixaErro.hidden = true;
  botao.disabled = true;
  botao.textContent = "Entrando…";
  try {
    const resp = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usuario: form.usuario.value, senha: form.senha.value }),
    });
    let dados = {};
    try { dados = await resp.json(); } catch { /* sem corpo */ }
    if (!resp.ok) throw new Error(dados.erro || "Não foi possível entrar. Tente novamente.");
    location.href = "/";
  } catch (e) {
    caixaErro.textContent = e.message;
    caixaErro.hidden = false;
    form.senha.value = "";
    form.senha.focus();
    botao.disabled = false;
    botao.textContent = "Entrar";
  }
});

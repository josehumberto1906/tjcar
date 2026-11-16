"""TJ Car - sistema de gestão para oficina mecânica (API + site)."""
import os
import secrets
from datetime import timedelta
from pathlib import Path

from flask import Flask, g, jsonify, redirect, request, send_from_directory, session

from auth import UsuarioRepositorio
from database import Database, caminho_padrao
from models import ErroBloqueado, ErroNegocio, ErroValidacao, NaoEncontrado
from repositorios import (
    ClienteRepositorio, OrdemRepositorio, PainelRepositorio,
    PecaRepositorio, ServicoRepositorio, VeiculoRepositorio,
)

BASE = Path(__file__).parent

# Rotas que podem ser abertas sem estar logado
ROTAS_PUBLICAS = {"static", "pagina_login", "api_login"}


def chave_secreta(db: Database) -> str:
    """Chave que assina o cookie de sessão. Fica num arquivo .key ao lado do banco."""
    da_variavel = os.environ.get("TJCAR_SECRET")
    if da_variavel:
        return da_variavel
    arquivo = Path(db.caminho).with_suffix(".key")
    if arquivo.exists():
        return arquivo.read_text().strip()
    chave = secrets.token_hex(32)
    arquivo.write_text(chave)
    try:
        arquivo.chmod(0o600)
    except OSError:
        pass
    return chave


def criar_app(caminho_banco: str | None = None) -> Flask:
    app = Flask(__name__, static_folder=str(BASE / "static"), static_url_path="/static")
    db = Database(caminho_banco or caminho_padrao())

    app.config.update(
        SECRET_KEY=chave_secreta(db),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Em produção com https, defina TJCAR_HTTPS=1 para o cookie só viajar criptografado
        SESSION_COOKIE_SECURE=os.environ.get("TJCAR_HTTPS") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
        MAX_CONTENT_LENGTH=1024 * 1024,
    )

    usuarios = UsuarioRepositorio(db)
    painel = PainelRepositorio(db)
    ordens = OrdemRepositorio(db)
    cadastros = {
        "clientes": ClienteRepositorio(db),
        "veiculos": VeiculoRepositorio(db),
        "pecas": PecaRepositorio(db),
        "servicos": ServicoRepositorio(db),
    }

    # ---------- erros ----------
    @app.errorhandler(ErroValidacao)
    def _validacao(e):
        return jsonify(erro=str(e)), 400

    @app.errorhandler(NaoEncontrado)
    def _nao_encontrado(e):
        return jsonify(erro=str(e)), 404

    @app.errorhandler(ErroNegocio)
    def _negocio(e):
        return jsonify(erro=str(e)), 409

    @app.errorhandler(ErroBloqueado)
    def _bloqueado(e):
        return jsonify(erro=str(e)), 429

    # ---------- login obrigatório ----------
    def usuario_logado():
        uid = session.get("u")
        if not uid:
            return None
        u = usuarios.obter(uid)
        # trocar a senha ou excluir o usuário derruba as sessões abertas
        if not u or session.get("v") != usuarios.selo(u["senha_hash"]):
            session.clear()
            return None
        return u

    @app.before_request
    def exigir_login():
        if request.endpoint is None or request.endpoint in ROTAS_PUBLICAS:
            return None
        g.usuario = usuario_logado()
        if g.usuario:
            return None
        if request.path.startswith("/api/"):
            return jsonify(erro="Faça login para continuar."), 401
        return redirect("/login")

    @app.after_request
    def cabecalhos(resp):
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["Referrer-Policy"] = "same-origin"
        if request.path.startswith("/api/") or request.path in ("/", "/login"):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    def corpo() -> dict:
        dados = request.get_json(silent=True)
        if not isinstance(dados, dict):
            raise ErroValidacao("Envie os dados em formato JSON.")
        return dados

    # ---------- login / logout ----------
    @app.get("/login")
    def pagina_login():
        if usuario_logado():
            return redirect("/")
        return send_from_directory(app.static_folder, "login.html")

    @app.post("/api/login")
    def api_login():
        dados = corpo()
        if usuarios.total() == 0:
            raise ErroNegocio("Nenhum usuário cadastrado. No computador do sistema, rode: python criar_usuario.py")
        usuario = str(dados.get("usuario", "")).strip()
        senha = str(dados.get("senha", ""))
        u = usuarios.autenticar(usuario, senha)
        if not u:
            return jsonify(erro="Usuário ou senha incorretos."), 401
        session.clear()
        session.permanent = True
        session["u"] = u["id"]
        session["v"] = usuarios.selo(u["senha_hash"])
        return jsonify(usuario=u["usuario"])

    @app.post("/api/logout")
    def api_logout():
        session.clear()
        return "", 204

    @app.get("/api/eu")
    def api_eu():
        return jsonify(usuario=g.usuario["usuario"])

    # ---------- site ----------
    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    # ---------- painel ----------
    @app.get("/api/painel")
    def api_painel():
        return jsonify(painel.resumo())

    # ---------- cadastros (clientes, veículos, peças, serviços) ----------
    def repo(nome: str):
        if nome not in cadastros:
            raise NaoEncontrado("Recurso não encontrado.")
        return cadastros[nome]

    @app.get("/api/<recurso>")
    def listar(recurso):
        if recurso == "ordens":
            return jsonify(ordens.listar(request.args.get("status", ""), request.args.get("busca", "")))
        return jsonify(repo(recurso).listar(request.args.get("busca", "").strip()))

    @app.post("/api/<recurso>")
    def criar(recurso):
        if recurso == "ordens":
            return jsonify(ordens.criar(corpo())), 201
        return jsonify(repo(recurso).criar(corpo())), 201

    @app.get("/api/<recurso>/<int:id>")
    def obter(recurso, id):
        if recurso == "ordens":
            return jsonify(ordens.obter(id))
        return jsonify(repo(recurso).obter(id))

    @app.put("/api/<recurso>/<int:id>")
    def atualizar(recurso, id):
        if recurso == "ordens":
            return jsonify(ordens.atualizar_defeito(id, corpo()))
        return jsonify(repo(recurso).atualizar(id, corpo()))

    @app.delete("/api/<recurso>/<int:id>")
    def excluir(recurso, id):
        if recurso == "ordens":
            ordens.excluir(id)
        else:
            repo(recurso).excluir(id)
        return "", 204

    # ---------- itens da ordem de serviço ----------
    @app.patch("/api/ordens/<int:id>/status")
    def ordem_status(id):
        return jsonify(ordens.mudar_status(id, corpo()))

    @app.post("/api/ordens/<int:id>/servicos")
    def ordem_add_servico(id):
        return jsonify(ordens.adicionar_servico(id, corpo())), 201

    @app.delete("/api/ordens/<int:id>/servicos/<int:item>")
    def ordem_del_servico(id, item):
        return jsonify(ordens.remover_servico(id, item))

    @app.post("/api/ordens/<int:id>/pecas")
    def ordem_add_peca(id):
        return jsonify(ordens.adicionar_peca(id, corpo())), 201

    @app.delete("/api/ordens/<int:id>/pecas/<int:item>")
    def ordem_del_peca(id, item):
        return jsonify(ordens.remover_peca(id, item))

    return app


app = criar_app()

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 5000))
    # host 0.0.0.0 permite abrir pelo celular na mesma rede Wi-Fi
    app.run(host="0.0.0.0", port=porta, debug=False)

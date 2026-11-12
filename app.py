"""TJ Car - sistema de gestão para oficina mecânica (API + site)."""
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from database import Database
from models import ErroNegocio, ErroValidacao, NaoEncontrado
from repositorios import (
    ClienteRepositorio, OrdemRepositorio, PainelRepositorio,
    PecaRepositorio, ServicoRepositorio, VeiculoRepositorio,
)

BASE = Path(__file__).parent


def criar_app(caminho_banco: str | None = None) -> Flask:
    app = Flask(__name__, static_folder=str(BASE / "static"), static_url_path="/static")
    db = Database(caminho_banco or os.environ.get("TJCAR_DB", BASE / "tjcar.db"))

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

    # ---------- site ----------
    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    # ---------- painel ----------
    @app.get("/api/painel")
    def api_painel():
        return jsonify(painel.resumo())

    # ---------- cadastros (clientes, veículos, peças, serviços) ----------
    def corpo() -> dict:
        dados = request.get_json(silent=True)
        if not isinstance(dados, dict):
            raise ErroValidacao("Envie os dados em formato JSON.")
        return dados

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

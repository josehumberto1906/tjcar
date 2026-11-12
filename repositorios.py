"""Camada de persistência: cada repositório conversa com o SQLite."""
from __future__ import annotations

import sqlite3
from datetime import datetime

from database import Database
from models import (
    Cliente, Entidade, ErroNegocio, ErroValidacao, NaoEncontrado,
    OrdemDeServico, Peca, Servico, Veiculo, _dinheiro, _inteiro, _texto,
)


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _traduzir(erro: sqlite3.IntegrityError) -> ErroNegocio:
    msg = str(erro)
    if "UNIQUE" in msg:
        return ErroNegocio("Já existe um registro com esse valor (placa ou código repetido).")
    if "FOREIGN KEY" in msg:
        return ErroNegocio("Este registro está em uso por outro cadastro e não pode ser excluído.")
    return ErroNegocio("Não foi possível salvar: dados inconsistentes.")


class Repositorio:
    """CRUD genérico para as entidades simples."""

    def __init__(self, db: Database, entidade: type[Entidade]):
        self.db = db
        self.entidade = entidade

    # consultas -----------------------------------------------------
    def _select(self) -> str:
        return f"SELECT * FROM {self.entidade.TABELA}"

    def _prefixo(self) -> str:
        return ""

    def listar(self, busca: str = "") -> list[dict]:
        sql = self._select()
        params: list = []
        if busca:
            colunas = self.entidade.BUSCA
            sql += " WHERE " + " OR ".join(f"{self._prefixo()}{c} LIKE ?" for c in colunas)
            params = [f"%{busca}%"] * len(colunas)
        sql += f" ORDER BY {self.entidade.ORDEM}"
        with self.db.conexao() as conn:
            return [dict(r) for r in conn.execute(sql, params)]

    def obter(self, id: int) -> dict:
        with self.db.conexao() as conn:
            linha = conn.execute(self._select() + f" WHERE {self._prefixo()}id = ?", (id,)).fetchone()
        if not linha:
            raise NaoEncontrado("Registro não encontrado.")
        return dict(linha)

    # escrita -------------------------------------------------------
    def _antes_de_salvar(self, obj: Entidade):
        """Gancho para validações que dependem do banco."""

    def criar(self, dados: dict) -> dict:
        obj = self.entidade.validar(dados)
        self._antes_de_salvar(obj)
        valores = obj.valores()
        colunas = ", ".join(valores)
        marcas = ", ".join("?" for _ in valores)
        try:
            with self.db.conexao() as conn:
                cur = conn.execute(
                    f"INSERT INTO {self.entidade.TABELA} ({colunas}) VALUES ({marcas})",
                    list(valores.values()),
                )
                novo_id = cur.lastrowid
        except sqlite3.IntegrityError as e:
            raise _traduzir(e)
        return self.obter(novo_id)

    def atualizar(self, id: int, dados: dict) -> dict:
        self.obter(id)
        obj = self.entidade.validar(dados)
        self._antes_de_salvar(obj)
        valores = obj.valores()
        atribuicoes = ", ".join(f"{c} = ?" for c in valores)
        try:
            with self.db.conexao() as conn:
                conn.execute(
                    f"UPDATE {self.entidade.TABELA} SET {atribuicoes} WHERE id = ?",
                    [*valores.values(), id],
                )
        except sqlite3.IntegrityError as e:
            raise _traduzir(e)
        return self.obter(id)

    def excluir(self, id: int):
        self.obter(id)
        try:
            with self.db.conexao() as conn:
                conn.execute(f"DELETE FROM {self.entidade.TABELA} WHERE id = ?", (id,))
        except sqlite3.IntegrityError as e:
            raise _traduzir(e)


class ClienteRepositorio(Repositorio):
    def __init__(self, db: Database):
        super().__init__(db, Cliente)

    def _select(self) -> str:
        return (
            "SELECT c.*, (SELECT COUNT(*) FROM veiculos v WHERE v.cliente_id = c.id) AS total_veiculos "
            "FROM clientes c"
        )

    def _prefixo(self) -> str:
        return "c."


class VeiculoRepositorio(Repositorio):
    def __init__(self, db: Database):
        super().__init__(db, Veiculo)

    def _select(self) -> str:
        return (
            "SELECT v.*, c.nome AS cliente_nome FROM veiculos v "
            "JOIN clientes c ON c.id = v.cliente_id"
        )

    def _prefixo(self) -> str:
        return "v."

    def _antes_de_salvar(self, obj: Veiculo):
        with self.db.conexao() as conn:
            existe = conn.execute("SELECT 1 FROM clientes WHERE id = ?", (obj.cliente_id,)).fetchone()
        if not existe:
            raise ErroValidacao("Cliente não encontrado.")


class PecaRepositorio(Repositorio):
    def __init__(self, db: Database):
        super().__init__(db, Peca)


class ServicoRepositorio(Repositorio):
    def __init__(self, db: Database):
        super().__init__(db, Servico)


class OrdemRepositorio:
    """Ordens de serviço: itens, estoque e status."""

    def __init__(self, db: Database):
        self.db = db

    # leitura -------------------------------------------------------
    def listar(self, status: str = "", busca: str = "") -> list[dict]:
        sql = """
            SELECT o.*, v.placa, v.marca, v.modelo, c.nome AS cliente_nome,
                   COALESCE((SELECT SUM(preco) FROM ordem_servicos WHERE ordem_id = o.id), 0)
                 + COALESCE((SELECT SUM(quantidade * preco_unitario) FROM ordem_pecas WHERE ordem_id = o.id), 0)
                   AS total
            FROM ordens o
            JOIN veiculos v ON v.id = o.veiculo_id
            JOIN clientes c ON c.id = v.cliente_id
        """
        condicoes, params = [], []
        if status:
            condicoes.append("o.status = ?")
            params.append(status)
        if busca:
            condicoes.append("(v.placa LIKE ? OR v.modelo LIKE ? OR c.nome LIKE ? OR o.defeito LIKE ?)")
            params += [f"%{busca}%"] * 4
        if condicoes:
            sql += " WHERE " + " AND ".join(condicoes)
        sql += " ORDER BY o.id DESC"
        with self.db.conexao() as conn:
            return [dict(r) for r in conn.execute(sql, params)]

    def _carregar(self, id: int) -> OrdemDeServico:
        with self.db.conexao() as conn:
            cab = conn.execute(
                """
                SELECT o.*, v.placa, v.marca, v.modelo, v.ano, v.km AS km_atual,
                       c.id AS cliente_id, c.nome AS cliente_nome, c.telefone AS cliente_telefone
                FROM ordens o
                JOIN veiculos v ON v.id = o.veiculo_id
                JOIN clientes c ON c.id = v.cliente_id
                WHERE o.id = ?
                """,
                (id,),
            ).fetchone()
            if not cab:
                raise NaoEncontrado("Ordem de serviço não encontrada.")
            servicos = [dict(r) for r in conn.execute(
                "SELECT * FROM ordem_servicos WHERE ordem_id = ? ORDER BY id", (id,))]
            pecas = [dict(r) for r in conn.execute(
                """
                SELECT op.*, p.nome, p.codigo FROM ordem_pecas op
                JOIN pecas p ON p.id = op.peca_id
                WHERE op.ordem_id = ? ORDER BY op.id
                """,
                (id,),
            )]
        return OrdemDeServico(dict(cab), servicos, pecas)

    def obter(self, id: int) -> dict:
        return self._carregar(id).to_dict()

    # escrita -------------------------------------------------------
    def criar(self, dados: dict) -> dict:
        veiculo_id = _inteiro(dados, "veiculo_id", "Veículo", minimo=1, padrao=0)
        if not veiculo_id:
            raise ErroValidacao("Veículo é obrigatório.")
        defeito = _texto(dados, "defeito", "Defeito relatado", maximo=500)
        with self.db.conexao() as conn:
            veic = conn.execute("SELECT km FROM veiculos WHERE id = ?", (veiculo_id,)).fetchone()
            if not veic:
                raise ErroValidacao("Veículo não encontrado.")
            km = _inteiro(dados, "km_entrada", "Quilometragem de entrada", padrao=veic["km"])
            cur = conn.execute(
                "INSERT INTO ordens (veiculo_id, defeito, km_entrada, criado_em) VALUES (?, ?, ?, ?)",
                (veiculo_id, defeito, km, _agora()),
            )
            novo_id = cur.lastrowid
            if km > veic["km"]:
                conn.execute("UPDATE veiculos SET km = ? WHERE id = ?", (km, veiculo_id))
        return self.obter(novo_id)

    def atualizar_defeito(self, id: int, dados: dict) -> dict:
        ordem = self._carregar(id)
        ordem.exigir_edicao()
        defeito = _texto(dados, "defeito", "Defeito relatado", maximo=500)
        with self.db.conexao() as conn:
            conn.execute("UPDATE ordens SET defeito = ? WHERE id = ?", (defeito, id))
        return self.obter(id)

    def adicionar_servico(self, id: int, dados: dict) -> dict:
        self._carregar(id).exigir_edicao()
        descricao = _texto(dados, "descricao", "Descrição do serviço", obrigatorio=True, maximo=200)
        preco = _dinheiro(dados, "preco", "Preço")
        with self.db.conexao() as conn:
            conn.execute(
                "INSERT INTO ordem_servicos (ordem_id, descricao, preco) VALUES (?, ?, ?)",
                (id, descricao, preco),
            )
        return self.obter(id)

    def remover_servico(self, id: int, item_id: int) -> dict:
        self._carregar(id).exigir_edicao()
        with self.db.conexao() as conn:
            conn.execute("DELETE FROM ordem_servicos WHERE id = ? AND ordem_id = ?", (item_id, id))
        return self.obter(id)

    def adicionar_peca(self, id: int, dados: dict) -> dict:
        self._carregar(id).exigir_edicao()
        peca_id = _inteiro(dados, "peca_id", "Peça", minimo=1, padrao=0)
        qtd = _inteiro(dados, "quantidade", "Quantidade", minimo=1, padrao=1)
        if not peca_id:
            raise ErroValidacao("Peça é obrigatória.")
        with self.db.conexao() as conn:
            peca = conn.execute("SELECT * FROM pecas WHERE id = ?", (peca_id,)).fetchone()
            if not peca:
                raise ErroValidacao("Peça não encontrada.")
            if peca["quantidade"] < qtd:
                raise ErroNegocio(
                    f"Estoque insuficiente de '{peca['nome']}': restam {peca['quantidade']}."
                )
            preco = _dinheiro(dados, "preco_unitario", "Preço unitário") if dados.get("preco_unitario") not in (None, "") else peca["preco"]
            conn.execute("UPDATE pecas SET quantidade = quantidade - ? WHERE id = ?", (qtd, peca_id))
            conn.execute(
                "INSERT INTO ordem_pecas (ordem_id, peca_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
                (id, peca_id, qtd, preco),
            )
        return self.obter(id)

    def remover_peca(self, id: int, item_id: int) -> dict:
        self._carregar(id).exigir_edicao()
        with self.db.conexao() as conn:
            item = conn.execute(
                "SELECT * FROM ordem_pecas WHERE id = ? AND ordem_id = ?", (item_id, id)
            ).fetchone()
            if item:
                conn.execute(
                    "UPDATE pecas SET quantidade = quantidade + ? WHERE id = ?",
                    (item["quantidade"], item["peca_id"]),
                )
                conn.execute("DELETE FROM ordem_pecas WHERE id = ?", (item_id,))
        return self.obter(id)

    def mudar_status(self, id: int, dados: dict) -> dict:
        ordem = self._carregar(id)
        novo = _texto(dados, "status", "Status", obrigatorio=True)
        ordem.validar_transicao(novo)
        with self.db.conexao() as conn:
            if novo == "cancelada":  # devolve as peças ao estoque
                for p in ordem.pecas:
                    conn.execute(
                        "UPDATE pecas SET quantidade = quantidade + ? WHERE id = ?",
                        (p["quantidade"], p["peca_id"]),
                    )
            concluido = _agora() if novo == "concluida" else None
            conn.execute(
                "UPDATE ordens SET status = ?, concluido_em = ? WHERE id = ?", (novo, concluido, id)
            )
        return self.obter(id)

    def excluir(self, id: int):
        ordem = self._carregar(id)
        if ordem.status not in ("aberta", "cancelada"):
            raise ErroNegocio("Só é possível excluir ordens abertas ou canceladas.")
        with self.db.conexao() as conn:
            if ordem.status == "aberta":
                for p in ordem.pecas:
                    conn.execute(
                        "UPDATE pecas SET quantidade = quantidade + ? WHERE id = ?",
                        (p["quantidade"], p["peca_id"]),
                    )
            conn.execute("DELETE FROM ordens WHERE id = ?", (id,))


class PainelRepositorio:
    """Números da tela inicial."""

    def __init__(self, db: Database):
        self.db = db

    def resumo(self) -> dict:
        mes = datetime.now().strftime("%Y-%m")
        with self.db.conexao() as conn:
            def um(sql, params=()):
                return conn.execute(sql, params).fetchone()[0]

            faturamento = um(
                """
                SELECT COALESCE(SUM(
                    COALESCE((SELECT SUM(preco) FROM ordem_servicos WHERE ordem_id = o.id), 0)
                  + COALESCE((SELECT SUM(quantidade * preco_unitario) FROM ordem_pecas WHERE ordem_id = o.id), 0)
                ), 0)
                FROM ordens o WHERE o.status = 'concluida' AND substr(o.concluido_em, 1, 7) = ?
                """,
                (mes,),
            )
            baixo = [dict(r) for r in conn.execute(
                "SELECT id, codigo, nome, quantidade, minimo FROM pecas "
                "WHERE quantidade <= minimo ORDER BY quantidade, nome LIMIT 20"
            )]
            return {
                "clientes": um("SELECT COUNT(*) FROM clientes"),
                "veiculos": um("SELECT COUNT(*) FROM veiculos"),
                "ordens_abertas": um("SELECT COUNT(*) FROM ordens WHERE status = 'aberta'"),
                "ordens_andamento": um("SELECT COUNT(*) FROM ordens WHERE status = 'em_andamento'"),
                "concluidas_mes": um(
                    "SELECT COUNT(*) FROM ordens WHERE status = 'concluida' AND substr(concluido_em, 1, 7) = ?",
                    (mes,),
                ),
                "faturamento_mes": round(faturamento, 2),
                "estoque_baixo": baixo,
            }

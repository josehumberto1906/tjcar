"""Entidades e regras de negócio da oficina (orientação a objetos)."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import ClassVar, Optional


class ErroValidacao(ValueError):
    """Dado inválido enviado pelo usuário."""


class NaoEncontrado(LookupError):
    """Registro não existe."""


class ErroNegocio(Exception):
    """Operação não permitida pelas regras da oficina."""


# ---------- helpers de validação ----------

def _texto(d: dict, campo: str, rotulo: str, obrigatorio=False, maximo=120) -> str:
    valor = d.get(campo)
    valor = "" if valor is None else str(valor).strip()
    if obrigatorio and not valor:
        raise ErroValidacao(f"{rotulo} é obrigatório.")
    if len(valor) > maximo:
        raise ErroValidacao(f"{rotulo} deve ter no máximo {maximo} caracteres.")
    return valor


def _inteiro(d: dict, campo: str, rotulo: str, minimo=0, maximo=10**9, padrao=0) -> int:
    bruto = d.get(campo)
    if bruto is None or bruto == "":
        return padrao
    try:
        valor = int(float(bruto))
    except (TypeError, ValueError):
        raise ErroValidacao(f"{rotulo} deve ser um número inteiro.")
    if valor < minimo or valor > maximo:
        raise ErroValidacao(f"{rotulo} deve estar entre {minimo} e {maximo}.")
    return valor


def _dinheiro(d: dict, campo: str, rotulo: str) -> float:
    bruto = d.get(campo)
    if bruto is None or bruto == "":
        return 0.0
    try:
        valor = float(str(bruto).replace(",", "."))
    except (TypeError, ValueError):
        raise ErroValidacao(f"{rotulo} deve ser um valor numérico.")
    if valor < 0:
        raise ErroValidacao(f"{rotulo} não pode ser negativo.")
    return round(valor, 2)


# ---------- entidades simples ----------

class Entidade:
    """Base das entidades persistidas por Repositorio."""

    TABELA: ClassVar[str]
    BUSCA: ClassVar[tuple] = ()
    ORDEM: ClassVar[str] = "id DESC"

    @classmethod
    def validar(cls, dados: dict) -> "Entidade":
        raise NotImplementedError

    def valores(self) -> dict:
        d = asdict(self)
        d.pop("id", None)
        return d


@dataclass
class Cliente(Entidade):
    TABELA: ClassVar[str] = "clientes"
    BUSCA: ClassVar[tuple] = ("nome", "telefone", "email")
    ORDEM: ClassVar[str] = "nome COLLATE NOCASE"

    nome: str = ""
    telefone: str = ""
    email: str = ""
    id: Optional[int] = None

    @classmethod
    def validar(cls, d: dict) -> "Cliente":
        return cls(
            nome=_texto(d, "nome", "Nome", obrigatorio=True),
            telefone=_texto(d, "telefone", "Telefone", maximo=30),
            email=_texto(d, "email", "E-mail"),
        )


@dataclass
class Veiculo(Entidade):
    TABELA: ClassVar[str] = "veiculos"
    BUSCA: ClassVar[tuple] = ("placa", "marca", "modelo")
    ORDEM: ClassVar[str] = "modelo COLLATE NOCASE"

    cliente_id: int = 0
    placa: str = ""
    marca: str = ""
    modelo: str = ""
    ano: int = 0
    km: int = 0
    id: Optional[int] = None

    @classmethod
    def validar(cls, d: dict) -> "Veiculo":
        placa = _texto(d, "placa", "Placa", obrigatorio=True, maximo=10)
        placa = placa.upper().replace(" ", "").replace("-", "")
        return cls(
            cliente_id=_inteiro(d, "cliente_id", "Cliente", minimo=1, padrao=0)
            or _erro("Cliente é obrigatório."),
            placa=placa,
            marca=_texto(d, "marca", "Marca", maximo=60),
            modelo=_texto(d, "modelo", "Modelo", obrigatorio=True, maximo=60),
            ano=_inteiro(d, "ano", "Ano", minimo=1900, maximo=2100, padrao=0),
            km=_inteiro(d, "km", "Quilometragem"),
        )


@dataclass
class Peca(Entidade):
    TABELA: ClassVar[str] = "pecas"
    BUSCA: ClassVar[tuple] = ("codigo", "nome")
    ORDEM: ClassVar[str] = "nome COLLATE NOCASE"

    codigo: str = ""
    nome: str = ""
    preco: float = 0.0
    quantidade: int = 0
    minimo: int = 0
    id: Optional[int] = None

    @classmethod
    def validar(cls, d: dict) -> "Peca":
        return cls(
            codigo=_texto(d, "codigo", "Código", obrigatorio=True, maximo=40),
            nome=_texto(d, "nome", "Nome", obrigatorio=True),
            preco=_dinheiro(d, "preco", "Preço"),
            quantidade=_inteiro(d, "quantidade", "Quantidade"),
            minimo=_inteiro(d, "minimo", "Estoque mínimo"),
        )


@dataclass
class Servico(Entidade):
    """Serviço do catálogo (atalho para preencher a ordem de serviço)."""

    TABELA: ClassVar[str] = "servicos"
    BUSCA: ClassVar[tuple] = ("descricao",)
    ORDEM: ClassVar[str] = "descricao COLLATE NOCASE"

    descricao: str = ""
    preco: float = 0.0
    id: Optional[int] = None

    @classmethod
    def validar(cls, d: dict) -> "Servico":
        return cls(
            descricao=_texto(d, "descricao", "Descrição", obrigatorio=True),
            preco=_dinheiro(d, "preco", "Preço"),
        )


def _erro(mensagem: str):
    raise ErroValidacao(mensagem)


# ---------- ordem de serviço ----------

class OrdemDeServico:
    """Ordem de serviço com seus itens, total e regras de status."""

    STATUS = ("aberta", "em_andamento", "concluida", "cancelada")
    TRANSICOES = {
        "aberta": {"em_andamento", "concluida", "cancelada"},
        "em_andamento": {"concluida", "cancelada"},
        "concluida": set(),
        "cancelada": set(),
    }

    def __init__(self, dados: dict, servicos: list[dict], pecas: list[dict]):
        self.dados = dados
        self.servicos = servicos
        self.pecas = pecas

    @property
    def status(self) -> str:
        return self.dados["status"]

    def pode_editar(self) -> bool:
        return bool(self.TRANSICOES[self.status])

    def exigir_edicao(self):
        if not self.pode_editar():
            raise ErroNegocio("Esta ordem já foi encerrada e não pode ser alterada.")

    def validar_transicao(self, novo: str):
        if novo not in self.STATUS:
            raise ErroValidacao("Status inválido.")
        if novo not in self.TRANSICOES[self.status]:
            raise ErroNegocio(f"Não é possível mudar de '{self.status}' para '{novo}'.")

    def total_servicos(self) -> float:
        return round(sum(s["preco"] for s in self.servicos), 2)

    def total_pecas(self) -> float:
        return round(sum(p["quantidade"] * p["preco_unitario"] for p in self.pecas), 2)

    def total(self) -> float:
        return round(self.total_servicos() + self.total_pecas(), 2)

    def to_dict(self) -> dict:
        return {
            **self.dados,
            "servicos": self.servicos,
            "pecas": self.pecas,
            "total_servicos": self.total_servicos(),
            "total_pecas": self.total_pecas(),
            "total": self.total(),
            "editavel": self.pode_editar(),
            "proximos_status": sorted(self.TRANSICOES[self.status]),
        }

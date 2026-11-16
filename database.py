"""Acesso ao banco SQLite do TJ Car."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def caminho_padrao() -> Path:
    """Arquivo do banco: variável TJCAR_DB ou tjcar.db ao lado do código."""
    return Path(os.environ.get("TJCAR_DB") or Path(__file__).parent / "tjcar.db")


ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT NOT NULL UNIQUE COLLATE NOCASE,
    senha_hash TEXT NOT NULL,
    criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS login_falhas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave TEXT NOT NULL,
    momento REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_login_falhas ON login_falhas (chave, momento);

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    telefone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS veiculos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE RESTRICT,
    placa TEXT NOT NULL UNIQUE,
    marca TEXT NOT NULL DEFAULT '',
    modelo TEXT NOT NULL,
    ano INTEGER NOT NULL DEFAULT 0,
    km INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pecas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    preco REAL NOT NULL DEFAULT 0,
    quantidade INTEGER NOT NULL DEFAULT 0,
    minimo INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS servicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao TEXT NOT NULL,
    preco REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ordens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    veiculo_id INTEGER NOT NULL REFERENCES veiculos(id) ON DELETE RESTRICT,
    defeito TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'aberta',
    km_entrada INTEGER NOT NULL DEFAULT 0,
    criado_em TEXT NOT NULL,
    concluido_em TEXT
);

CREATE TABLE IF NOT EXISTS ordem_servicos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ordem_id INTEGER NOT NULL REFERENCES ordens(id) ON DELETE CASCADE,
    descricao TEXT NOT NULL,
    preco REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ordem_pecas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ordem_id INTEGER NOT NULL REFERENCES ordens(id) ON DELETE CASCADE,
    peca_id INTEGER NOT NULL REFERENCES pecas(id) ON DELETE RESTRICT,
    quantidade INTEGER NOT NULL,
    preco_unitario REAL NOT NULL
);
"""


class Database:
    """Abre conexões e cria as tabelas na primeira execução."""

    def __init__(self, caminho: str | Path):
        self.caminho = str(caminho)
        self.criar_tabelas()

    @contextmanager
    def conexao(self):
        conn = sqlite3.connect(self.caminho)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def criar_tabelas(self):
        with self.conexao() as conn:
            conn.executescript(ESQUEMA)

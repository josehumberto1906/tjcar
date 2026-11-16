"""Usuários, senhas e proteção contra tentativas de login em massa."""
from __future__ import annotations

import hashlib
import re
import sqlite3
import time
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from database import Database
from models import ErroBloqueado, ErroNegocio, ErroValidacao, NaoEncontrado

MAX_FALHAS = 5            # tentativas erradas permitidas...
JANELA_SEGUNDOS = 10 * 60  # ...dentro desta janela (10 minutos)
METODO_HASH = "pbkdf2:sha256"
# Hash falso: usado quando o usuário não existe, para o tempo de resposta
# ser igual e não revelar quais nomes de usuário existem.
_HASH_FALSO = generate_password_hash("senha-falsa-para-igualar-o-tempo", method=METODO_HASH)


class UsuarioRepositorio:
    def __init__(self, db: Database):
        self.db = db

    # ---------- validação ----------
    @staticmethod
    def validar_usuario(usuario: str) -> str:
        usuario = (usuario or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9._-]{3,30}", usuario):
            raise ErroValidacao("Usuário deve ter de 3 a 30 caracteres: letras, números, ponto, hífen ou sublinhado.")
        return usuario

    @staticmethod
    def validar_senha(senha: str) -> str:
        if not senha or len(senha) < 8:
            raise ErroValidacao("A senha deve ter pelo menos 8 caracteres.")
        if len(senha) > 128:
            raise ErroValidacao("A senha deve ter no máximo 128 caracteres.")
        return senha

    @staticmethod
    def selo(senha_hash: str) -> str:
        """Identifica a senha atual; trocar a senha invalida as sessões abertas."""
        return hashlib.sha256(senha_hash.encode()).hexdigest()[:16]

    # ---------- cadastro ----------
    def total(self) -> int:
        with self.db.conexao() as conn:
            return conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]

    def listar(self) -> list[dict]:
        with self.db.conexao() as conn:
            return [dict(r) for r in conn.execute(
                "SELECT id, usuario, criado_em FROM usuarios ORDER BY usuario")]

    def obter(self, id: int) -> dict | None:
        with self.db.conexao() as conn:
            linha = conn.execute("SELECT * FROM usuarios WHERE id = ?", (id,)).fetchone()
        return dict(linha) if linha else None

    def _por_nome(self, usuario: str) -> dict | None:
        with self.db.conexao() as conn:
            linha = conn.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario,)).fetchone()
        return dict(linha) if linha else None

    def criar(self, usuario: str, senha: str) -> dict:
        usuario = self.validar_usuario(usuario)
        senha = self.validar_senha(senha)
        try:
            with self.db.conexao() as conn:
                conn.execute(
                    "INSERT INTO usuarios (usuario, senha_hash, criado_em) VALUES (?, ?, ?)",
                    (usuario, generate_password_hash(senha, method=METODO_HASH),
                     datetime.now().isoformat(timespec="seconds")),
                )
        except sqlite3.IntegrityError:
            raise ErroNegocio("Já existe um usuário com esse nome.")
        return self._por_nome(usuario)

    def definir_senha(self, usuario: str, senha: str):
        senha = self.validar_senha(senha)
        existente = self._por_nome((usuario or "").strip())
        if not existente:
            raise NaoEncontrado("Usuário não encontrado.")
        with self.db.conexao() as conn:
            conn.execute(
                "UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                (generate_password_hash(senha, method=METODO_HASH), existente["id"]),
            )
            conn.execute("DELETE FROM login_falhas WHERE chave = ?", (existente["usuario"].lower(),))

    def excluir(self, usuario: str):
        existente = self._por_nome((usuario or "").strip())
        if not existente:
            raise NaoEncontrado("Usuário não encontrado.")
        if self.total() <= 1:
            raise ErroNegocio("Não é possível excluir o único usuário.")
        with self.db.conexao() as conn:
            conn.execute("DELETE FROM usuarios WHERE id = ?", (existente["id"],))

    # ---------- login ----------
    def _falhas_recentes(self, conn, chave: str) -> int:
        limite = time.time() - JANELA_SEGUNDOS
        return conn.execute(
            "SELECT COUNT(*) FROM login_falhas WHERE chave = ? AND momento > ?", (chave, limite)
        ).fetchone()[0]

    def autenticar(self, usuario: str, senha: str) -> dict | None:
        """Devolve o usuário se a senha estiver certa; None se errada.

        Levanta ErroBloqueado depois de muitas tentativas erradas seguidas.
        """
        chave = (usuario or "").strip().lower()[:60]
        with self.db.conexao() as conn:
            if self._falhas_recentes(conn, chave) >= MAX_FALHAS:
                raise ErroBloqueado(
                    f"Muitas tentativas erradas. Aguarde {JANELA_SEGUNDOS // 60} minutos e tente de novo."
                )

        registro = self._por_nome(usuario.strip()) if usuario else None
        senha_ok = check_password_hash(registro["senha_hash"] if registro else _HASH_FALSO, senha or "")

        with self.db.conexao() as conn:
            if registro and senha_ok:
                conn.execute("DELETE FROM login_falhas WHERE chave = ?", (chave,))
                return registro
            agora = time.time()
            conn.execute("DELETE FROM login_falhas WHERE momento < ?", (agora - JANELA_SEGUNDOS,))
            conn.execute("INSERT INTO login_falhas (chave, momento) VALUES (?, ?)", (chave, agora))
        return None

"""Gerencia os usuários do TJ Car pelo terminal.

Exemplos:
    python criar_usuario.py                      cria um usuário (pergunta nome e senha)
    python criar_usuario.py --usuario ana        cria o usuário "ana" (pergunta a senha)
    python criar_usuario.py --trocar-senha ana   troca a senha de "ana"
    python criar_usuario.py --listar             lista os usuários
    python criar_usuario.py --excluir ana        exclui o usuário "ana"
"""
import argparse
import getpass
import sys

from auth import UsuarioRepositorio
from database import Database, caminho_padrao
from models import ErroNegocio, ErroValidacao, NaoEncontrado


def pedir_senha() -> str:
    senha = getpass.getpass("Senha (mín. 8 caracteres): ")
    if senha != getpass.getpass("Repita a senha: "):
        raise ErroValidacao("As senhas não são iguais.")
    return senha


def main() -> int:
    ap = argparse.ArgumentParser(description="Gerencia os usuários do TJ Car.")
    ap.add_argument("--usuario", help="nome do novo usuário")
    ap.add_argument("--trocar-senha", metavar="USUARIO", help="troca a senha deste usuário")
    ap.add_argument("--excluir", metavar="USUARIO", help="exclui este usuário")
    ap.add_argument("--listar", action="store_true", help="lista os usuários")
    args = ap.parse_args()

    usuarios = UsuarioRepositorio(Database(caminho_padrao()))
    try:
        if args.listar:
            lista = usuarios.listar()
            if not lista:
                print("Nenhum usuário cadastrado.")
            for u in lista:
                print(f"- {u['usuario']} (criado em {u['criado_em']})")
        elif args.trocar_senha:
            usuarios.definir_senha(args.trocar_senha, pedir_senha())
            print("Senha alterada. Quem estava conectado com a senha antiga será desconectado.")
        elif args.excluir:
            usuarios.excluir(args.excluir)
            print("Usuário excluído.")
        else:
            nome = args.usuario or input("Nome do usuário: ")
            usuarios.criar(nome, pedir_senha())
            print(f"Usuário '{nome.strip()}' criado. Agora é só entrar em /login.")
    except (ErroValidacao, ErroNegocio, NaoEncontrado) as e:
        print(f"Erro: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

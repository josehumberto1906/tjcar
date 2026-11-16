# TJ Car — Gestão de oficina mecânica

Sistema web que funciona no computador e no celular (layout responsivo, instalável como app).

- **Clientes e veículos**: cadastro com busca; um cliente pode ter vários veículos.
- **Estoque de peças**: preço, quantidade e estoque mínimo, com alerta de reposição.
- **Catálogo de serviços**: serviços comuns com preço padrão.
- **Ordens de serviço**: abre a ordem para um veículo, lança os serviços (com preços) e as peças usadas; o estoque baixa sozinho. Fluxo: aberta → em andamento → concluída (ou cancelada, que devolve as peças).
- **Painel**: faturamento do mês, ordens em aberto e peças para repor.
- **Impressão**: botão "Imprimir" na ordem de serviço.

## Como rodar

```bash
pip install -r requirements.txt
python criar_usuario.py      # cria o seu usuário e senha (só na primeira vez)
python app.py
```

Abra http://localhost:5000 no computador.

**No celular** (mesmo Wi-Fi): descubra o IP do computador (ex.: `192.168.0.15`) e abra `http://192.168.0.15:5000`.
No Chrome do celular use "Adicionar à tela inicial" para instalar como aplicativo.

Os dados ficam no arquivo `tjcar.db` (SQLite). Faça cópia dele para ter backup.

## Estrutura

```
app.py            rotas da API (Flask) e entrega do site
models.py         classes: Cliente, Veiculo, Peca, Servico, OrdemDeServico (regras de negócio)
repositorios.py   acesso ao banco: um repositório por entidade
database.py       conexão e criação das tabelas SQLite
static/           frontend (index.html, style.css, app.js)
```

## Login e usuários

Todas as telas e a API exigem login. Os usuários são gerenciados pelo terminal:

```bash
python criar_usuario.py                      # cria um usuário (pergunta nome e senha)
python criar_usuario.py --trocar-senha ana   # troca a senha (desconecta quem estava logado)
python criar_usuario.py --listar             # lista os usuários
python criar_usuario.py --excluir ana        # exclui um usuário
```

- Senhas com no mínimo 8 caracteres, guardadas apenas como hash (nunca em texto).
- Depois de 5 senhas erradas seguidas para o mesmo usuário, o login é bloqueado por 10 minutos.
- A sessão dura 7 dias; o botão "Sair" encerra na hora.
- A chave que assina a sessão fica em `tjcar.key` (criada sozinha, não vai para o GitHub).

## Colocando na internet

1. **Use sempre https** (PythonAnywhere, Render etc. já fornecem) e defina `TJCAR_HTTPS=1`
   no ambiente, para o cookie de sessão só trafegar criptografado.
2. Crie o usuário no servidor com `python criar_usuario.py` (no console do serviço).
3. Faça backup do arquivo `tjcar.db` com frequência.

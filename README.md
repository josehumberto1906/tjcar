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

## Observação de segurança

Esta versão não tem login: use apenas na rede da oficina. Para colocar na internet,
adicione autenticação e HTTPS antes.

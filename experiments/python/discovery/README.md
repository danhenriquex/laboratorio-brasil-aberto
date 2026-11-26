# E0 — Inventário e conectividade das fontes

Ferramenta de linha de comando que responde à pergunta do experimento E0: **quais fontes do catálogo respondem hoje, com que autenticação e em que formato, e onde as hipóteses de acesso do catálogo estavam erradas?**

Ela lê `discovery/sources.json`, faz uma única consulta de leitura, sequencial e espaçada, a cada fonte com `probe_url` e grava dois relatórios em `discovery/reports/`, um JSON e um HTML. O relatório traz só a estrutura das respostas (nomes de campos e tipos), nunca os valores.

## Uso

A partir da raiz do repositório:

```bash
uv sync --project experiments/python/discovery
uv run --directory experiments/python/discovery pytest                   # testes, sem rede
uv run --project experiments/python/discovery inventario --rodada 1      # execução real
```

Opções e códigos de saída: [contracts/cli.md](../../../specs/001-inventario-fontes/contracts/cli.md).
Guia de validação completo: [quickstart.md](../../../specs/001-inventario-fontes/quickstart.md).

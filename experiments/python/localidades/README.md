# E1 — Serviço de localidades (IBGE)

**Pergunta do experimento:** o que é preciso para expor as localidades do IBGE como um serviço próprio, com contrato estável, procedência em cada resposta e comportamento previsível quando o IBGE falha ou demora?

Serviço HTTP somente leitura, com Python, FastAPI e httpx, que cumpre o contrato compartilhado com o E4: [`contracts/localidades/openapi.yaml`](../../../contracts/localidades/openapi.yaml).

## Como rodar

Todos os comandos partem da raiz do repositório.

```bash
uv sync --project experiments/python/localidades

# testes da implementação (sem rede externa)
uv run --directory experiments/python/localidades pytest

# verificação de caixa-preta do contrato (IBGE falso + serviço + suíte)
contracts/localidades/verificacao/verificar.sh "uv run --project experiments/python/localidades localidades"

# execução real contra o IBGE, em 127.0.0.1:8000
uv run --project experiments/python/localidades localidades
```

## Configuração

Variáveis comuns ao E1 e ao E4, com padrões e regras em [`contracts/localidades/README.md`](../../../contracts/localidades/README.md):
- `LOCALIDADES_HOST`
- `LOCALIDADES_PORTA`
- `LOCALIDADES_IBGE_URL`
- `LOCALIDADES_PRAZO_FONTE_S`
- `LOCALIDADES_VALIDADE_S`
- `LOCALIDADES_ITENS_MAX`

O roteiro de validação completo está em [`specs/002-servico-localidades/quickstart.md`](../../../specs/002-servico-localidades/quickstart.md).

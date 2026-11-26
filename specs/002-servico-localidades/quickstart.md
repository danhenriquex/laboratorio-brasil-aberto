# Quickstart: E1 — Serviço de localidades (IBGE)

Guia de validação ponta a ponta. Rotas e formatos estão em [contracts/localidades/openapi.yaml](../../contracts/localidades/openapi.yaml), e as regras, em [data-model.md](data-model.md). Todos os comandos partem da raiz do repositório.

## Pré-requisitos

- `uv` instalado (o Python ≥ 3.11 vem por ele).
- `curl` e, opcionalmente, `jq`.

```bash
uv sync --project experiments/python/localidades
uv sync --project contracts/localidades/verificacao
```

## 1. Testes da implementação (sem rede)

```bash
uv run --directory experiments/python/localidades pytest
```

Use `--directory`, e não `--project`: rodado da raiz, o pytest procuraria testes em todo o repositório.

**Esperado**: todos passam. O `conftest` recusa conexões fora do loopback, e o IBGE é simulado com `respx` (FR-027).

## 2. Verificação de caixa-preta do contrato

```bash
contracts/localidades/verificacao/verificar.sh "uv run --project experiments/python/localidades localidades"
```

O script faz quatro coisas:

1. sobe o IBGE falso em `127.0.0.1:8099`;
2. sobe o serviço com `LOCALIDADES_IBGE_URL=http://127.0.0.1:8099/api/v1/localidades`, `LOCALIDADES_PRAZO_FONTE_S=1` e `LOCALIDADES_VALIDADE_S=2`;
3. espera o `/health`;
4. roda a suíte e encerra os dois processos.

**Esperado**: todos os cenários passam, e cada um conferiu a resposta contra o `openapi.yaml`:

| Cenário | O que prova |
|---|---|
| Listas e consultas | US1 e US2 |
| Erros 400 e 404 | entradas inválidas e inexistentes |
| Cópia válida | zero consultas novas à fonte (SC-004) |
| Fonte fora, lenta ou inválida, sem cópia | 502 e 504 em até 2 s com o prazo de 1 s (SC-005) |
| Fonte fora com cópia vencida | `desatualizado: true` |
| Busca por nome | US4 |
| `/health`, `/metrics` e `X-Correlation-Id` | US5 |

## 3. Testes com a rede externa bloqueada (SC-006)

```bash
sandbox-exec -p '(version 1)(allow default)(deny network*)(allow network* (local ip "localhost:*"))(allow network* (remote ip "localhost:*"))' \
  uv run --offline --directory experiments/python/localidades pytest
UV_OFFLINE=1 sandbox-exec -p '(version 1)(allow default)(deny network*)(allow network* (local ip "localhost:*"))(allow network* (remote ip "localhost:*"))' \
  contracts/localidades/verificacao/verificar.sh "uv run --offline --project experiments/python/localidades localidades"
```

Antes, confirme que o bloqueio funciona: dentro do mesmo sandbox, `curl -sS https://servicodados.ibge.gov.br/api/v1/localidades/estados` precisa falhar.

**Esperado**: as duas execuções passam.

## 4. Execução real contra o IBGE (manual)

```bash
uv run --project experiments/python/localidades localidades   # escuta em 127.0.0.1:8000
```

Em outro terminal:

```bash
curl -s localhost:8000/v1/ufs | jq '.dados | length, .[0]'                 # 27, e a primeira UF por nome (Acre)
curl -s localhost:8000/v1/ufs/rj/municipios?nome=niteroi | jq '.dados'     # [{"codigo":"3303302","nome":"Niterói"}]
curl -s localhost:8000/v1/municipios/3304557 | jq '.dados, .meta'         # Rio de Janeiro, com regiões e procedência
curl -s -i localhost:8000/v1/municipios/9999999 | head -1                  # 404 (o IBGE responde [])
curl -s -i localhost:8000/v1/municipios/12ab | head -1                     # 400, sem consultar o IBGE
curl -s 'localhost:8000/v1/ufs/MG/municipios?itens=500&pagina=2' | jq '.paginacao'   # total 853, paginas 2
curl -s -H 'X-Correlation-Id: teste-123' -i localhost:8000/health | grep -i correlation
curl -s localhost:8000/metrics | grep localidades_cache_total
```

Repita a primeira chamada: a resposta sai da cópia guardada, com o mesmo `coletado_em`, e o `localidades_cache_total{resultado="acerto"}` sobe.

**Esperado**: registre no `RESULTS.md` a data, as latências da primeira chamada e da repetida, e qualquer diferença em relação às fixtures.

## 5. Gravar ou atualizar as fixtures do IBGE (manual, raro)

As fixtures em `contracts/localidades/fixtures-ibge/` são respostas reais do IBGE gravadas numa data. Elas só são regravadas quando o IBGE mudar algo. A data entra no `README.md` da pasta. Os testes automatizados nunca fazem isso (Constituição IV).

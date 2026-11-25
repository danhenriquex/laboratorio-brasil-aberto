# Quickstart: E0 — Inventário e conectividade das fontes

Guia para validar a feature de ponta a ponta. Os detalhes estão em [contracts/cli.md](contracts/cli.md), [contracts/relatorio.schema.json](contracts/relatorio.schema.json) e [data-model.md](data-model.md).

## Pré-requisitos

- `uv` instalado (testado com 0.13) e Python 3.11 ou mais recente disponível para o `uv`.
- Rodar todos os comandos a partir da raiz do repositório.
- Não é preciso nenhuma chave nem `.env`: o E0 não usa credenciais.

## 1. Instalar e rodar os testes (sem rede)

```bash
uv sync --project experiments/python/discovery
uv run --project experiments/python/discovery pytest
```

**Esperado**: todos os testes passam. Para comprovar SC-007, rode com a rede desligada e confira que o resultado é o mesmo.

Cenários que a suíte deve cobrir, com respostas simuladas:

| Cenário | Resultado esperado no relatório |
|---|---|
| Fonte responde JSON | `respondeu`, status, latência, `formato_detectado: json`, `amostra.campos` preenchido |
| Tempo esgotado | `falhou` / `tempo_esgotado`; a fonte seguinte ainda é consultada |
| Conexão recusada ou DNS | `falhou` / `indisponivel` |
| 401, ou redirecionamento para `sso.acesso.gov.br` | `falhou` / `exige_autenticacao`, `auth_observada: exige` |
| 403 | `falhou` / `acesso_negado` |
| 429 com `Retry-After` | `falhou` / `limite_requisicoes`, `retry_after` preenchido, uma única consulta |
| 200 com HTML declarado como JSON | `formato_detectado: html`, `formato_divergente: true` |
| 200 com JSON quebrado | `falhou` / `resposta_invalida` |
| Lista vazia | `amostra.vazia: true` |
| Resposta acima de 1 MiB | `truncada: true` |
| Resposta com nomes e e-mails fictícios | nenhum dos valores aparece no JSON nem no HTML (SC-004) |
| Fonte sem `probe_url` | `sem_teste`, nenhuma requisição registrada no mock |
| Catálogo inválido | código de saída 1, nenhum relatório |
| Intervalo | o relógio simulado mostra ≥ intervalo entre consultas, e uma consulta por fonte (SC-005) |
| Interrupção | código 130, `interrompida: true`, fontes restantes como `nao_executada` |
| Relatório | o JSON gerado valida contra `relatorio.schema.json` |

## 2. Execução real: rodada 1

Esta é uma chamada real às fontes. Faça manualmente, nunca na suíte de testes (princípio IV).

```bash
uv run --project experiments/python/discovery inventario --rodada 1
```

**Esperado** (SC-001, SC-002):
- termina em menos de 1 minuto, com código de saída 0;
- o terminal lista as 4 fontes da rodada 1: IBGE localidades, BCB SGS, BCB IFData (sem teste automatizado) e Câmara;
- dois arquivos novos em `discovery/reports/`: `inventario-<timestamp>.json` e `.html`.

## 3. Conferir os relatórios

```bash
open discovery/reports/inventario-*.html   # macOS: o mais recente aparece por último
```

Lendo só o HTML, responda para cada fonte da rodada 1 (SC-006): ela responde? Exige autenticação? Em que formato? Onde a hipótese do catálogo estava errada?

Confira também:
- cada linha traz a data e hora da coleta (UTC e Brasília) e o link da documentação;
- o aviso de que a sondagem não confirma licença, limites nem termos de uso (FR-020);
- na Câmara, a amostra mostra só nomes de campos e tipos, nenhum nome de deputado (FR-015).

## 4. Filtros e erros de uso

```bash
uv run --project experiments/python/discovery inventario --fonte ibge-localidades   # 1 fonte, 1 consulta
uv run --project experiments/python/discovery inventario --fonte nao-existe         # código 2, nenhuma consulta
uv run --project experiments/python/discovery inventario --catalogo /tmp/nao-existe.json  # código 1
```

## 5. Fechamento do experimento

1. Guardar o relatório real da rodada 1 em `discovery/reports/`.
2. Preencher uma ficha por fonte da rodada 1 em `discovery/fichas/` (modelo `_TEMPLATE.md`), seção "Resultado do teste de conectividade".
3. Copiar `docs/templates/RESULTS.md` para `specs/001-inventario-fontes/RESULTS.md` e preencher.
4. Atualizar manualmente o `verification` em `discovery/sources.json` onde o relatório sugerir, sempre com o escopo que a sonda permite.

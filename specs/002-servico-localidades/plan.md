# Implementation Plan: E1 — Serviço de localidades (IBGE)

**Branch**: `002-servico-localidades` | **Date**: 2026-11-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-servico-localidades/spec.md`

## Summary

Serviço HTTP somente leitura que repassa a API de localidades do IBGE. Ele expõe UFs, municípios por UF (paginados e com busca por nome) e município por código, sempre com procedência. Erros saem padronizados, e o serviço guarda cópias com validade, servindo a cópia vencida quando a fonte falha.

Abordagem:

- **Contrato primeiro:** um OpenAPI 3.1 escrito à mão em `contracts/localidades/`, compartilhado com o E4.
- **Implementação:** Python com FastAPI e httpx assíncrono, cache em memória e prazo total por consulta.
- **Verificação de caixa-preta:** uma suíte que fala com o serviço só pelo endereço, diante de um "IBGE falso" controlável, para servir igual ao E1 e ao E4.
- **Resposta real do IBGE:** a sondagem de 2026-11-26 decidiu como tratar "não encontrado", porque o IBGE responde 200 com `[]`.

Detalhes em [research.md](research.md).

## Technical Context

**Language/Version**: Python ≥ 3.11 (`requires-python = ">=3.11"`; uv local com 3.12)

**Primary Dependencies**:

- runtime: `fastapi` (traz `pydantic` e `starlette`), `uvicorn`, `httpx` (cliente assíncrono) e `prometheus-client`;
- biblioteca padrão: `logging` (registro em JSON), `unicodedata` (busca sem acento) e `asyncio` (prazo total e consulta única por chave).

**Storage**: nenhum banco. A cópia guardada fica em memória do processo, e as fixtures do IBGE são arquivos JSON versionados

**Testing**:

- `pytest`, `respx` e o `TestClient` do FastAPI nos testes da implementação;
- suíte de caixa-preta com `pytest`, `httpx`, `jsonschema` e `pyyaml`, mais um IBGE falso feito com a biblioteca padrão (`http.server`);
- `openapi-spec-validator` para validar o próprio contrato.

**Target Platform**: máquina local (macOS). Nada específico de plataforma; escuta em `127.0.0.1`

**Project Type**: web service (API HTTP somente leitura), mais uma suíte de verificação independente de linguagem

**Performance Goals**: com o dado guardado, p95 < 500 ms por pedido (SC-003; o esperado é de poucos ms). A primeira consulta custa o tempo do IBGE, que foi de 140 a 430 ms em 2026-11-26

**Constraints**:

- prazo total de 10 s por consulta ao IBGE (FR-014);
- no máximo 1 consulta à fonte por pedido e nenhuma nova tentativa (FR-017);
- validade da cópia de 24 h (FR-015);
- página de até 500 itens;
- nenhuma credencial;
- testes sem rede externa (FR-027).

**Scale/Scope**: 27 UFs e 5.571 municípios; a maior UF é MG, com 853. Uso local por um desenvolvedor e, depois, por outros serviços do laboratório. A memória da cópia guardada é limitada pelo próprio domínio: em torno de 3 MB, se tudo for consultado

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Como o plano atende | Situação |
|---|---|---|
| I. Fontes oficiais primeiro | Única fonte: a API oficial do IBGE. `meta.url_documentacao` aponta para a documentação oficial. Licença registrada como "não encontrei" na ficha | ✅ |
| II. Rastreabilidade | Toda resposta com dados leva `meta` com fonte, URL consultada, documentação, `coletado_em` (UTC, da consulta original) e `desatualizado`. Cada registro leva o seu `codigo` oficial (R10). Vigência não se aplica: não são normas | ✅ |
| III. Verificar antes de afirmar | O comportamento do IBGE (não encontrado = `[]`, chave real `regiao-intermediaria`) foi confirmado em chamada real datada (R1). A ficha é atualizada com isso | ✅ |
| IV. Testes sem rede | Testes da implementação com `respx`; suíte de caixa-preta contra um IBGE falso em `127.0.0.1`; fixtures gravadas uma vez, com data. Verificação com a rede externa bloqueada (R13) | ✅ |
| V. Resiliência | Prazo total por consulta, erros de domínio (R11), cache com validade e cópia vencida em caso de falha (R5), nenhuma nova tentativa, falha isolada por pedido | ✅ |
| VI. Contrato como fronteira | OpenAPI 3.1 em `contracts/localidades/openapi.yaml`, erros em `application/problem+json` (RFC 9457). O E4 compartilha o contrato e a suíte de verificação, e nunca o código do serviço | ✅ |
| VII. Privacidade | Unidades territoriais; nenhum dado pessoal. O registro de pedidos não guarda IP nem cabeçalhos além da correlação | ✅ |
| VIII. Cautela jurídica e financeira | Não se aplica | n/a |
| IX. Segredos fora do código | Nenhuma credencial; configuração por variáveis `LOCALIDADES_*` | ✅ |
| X. Simplicidade | Um processo, cache em memória (sem Redis), sem banco, sem Docker. A suíte de verificação é um projeto pequeno, justificado por servir a dois experimentos | ✅ (ver Complexity Tracking) |

**Padrões de serviço (Additional Constraints)**:

- `/health` e `/metrics` ✅;
- `/v1/...` ✅;
- paginação `pagina`/`itens` ✅;
- `X-Correlation-Id` ✅.

**Reavaliação pós-design (Fase 1)**: o contrato e o modelo de dados não introduziram violação. A procedência é obrigatória no schema (`required: [meta]`) e o formato de erro é único, o que reforça II e VI por construção. **Gate: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/002-servico-localidades/
├── spec.md
├── plan.md              # este arquivo
├── research.md          # decisões R1–R14
├── data-model.md        # entidades, validação, ordenação, estados da cópia guardada
├── quickstart.md        # validação ponta a ponta
├── contracts/
│   └── README.md        # aponta para o contrato compartilhado em contracts/localidades/
├── checklists/
│   └── requirements.md
├── tasks.md             # /speckit-tasks
└── RESULTS.md           # fechamento do experimento
```

### Source Code (repository root)

```text
contracts/localidades/                 # compartilhado entre E1 e E4
├── openapi.yaml                       # contrato v1 (OpenAPI 3.1)
├── README.md                          # rotas, configuração comum (LOCALIDADES_*), como verificar
├── fixtures-ibge/                     # respostas reais do IBGE gravadas em 2026-11-26 (+ casos sintéticos)
└── verificacao/                       # suíte de caixa-preta (projeto uv próprio)
    ├── pyproject.toml
    ├── verificar.sh                   # sobe o IBGE falso e o serviço (comando recebido), roda a suíte, encerra
    ├── src/ibge_falso/                # servidor http.server com fixtures e modos: normal, fora, lento, invalido
    └── tests/                         # cenários US1–US5 validados contra o openapi.yaml

experiments/python/localidades/        # E1
├── pyproject.toml                     # projeto uv; script "localidades"
├── README.md
├── src/localidades/
│   ├── __init__.py                    # __version__
│   ├── __main__.py                    # python -m localidades (uvicorn com a configuração)
│   ├── config.py                      # Configuracao a partir de LOCALIDADES_*
│   ├── dominio.py                     # UF, Regiao, Municipio, Procedencia, Pagina; dobrar(), ordenar, buscar, paginar
│   ├── erros.py                       # erros de domínio (EntradaInvalida, NaoEncontrado, Fonte*)
│   ├── fonte_ibge.py                  # cliente assíncrono: prazo total, classificação de falhas, normalização
│   ├── cache.py                       # cópia com validade, consulta única por chave, cópia vencida em falha
│   ├── servico.py                     # casos de uso; não importa FastAPI (portas e adaptadores)
│   ├── api.py                         # FastAPI: rotas v1, problem+json, correlação, /health, /metrics
│   ├── metricas.py                    # contadores e histograma Prometheus
│   └── registro.py                    # log JSON por pedido
└── tests/
    ├── conftest.py                    # bloqueio de rede externa, relógio falso, fixtures do IBGE
    ├── unit/                          # dominio, cache, fonte_ibge (respx), config
    └── integration/                   # API completa com TestClient + respx
```

**Structure Decision**:

- **Serviço:** fica em `experiments/python/localidades/`, conforme a estrutura do repositório. Só passa para `services/` se "se graduar" depois do E4.
- **Contrato e suíte:** ficam juntos em `contracts/localidades/`, porque são o que o E1 e o E4 compartilham. A suíte é um projeto `uv` separado, e o serviço não depende dela: ela fala com qualquer implementação pela rede.
- **Fixtures:** as respostas gravadas do IBGE ficam uma única vez em `contracts/localidades/fixtures-ibge/`, e os testes do E1 as leem por caminho relativo, como o E0 fazia com o schema.

## Complexity Tracking

| Item | Por que é necessário | Alternativa mais simples rejeitada porque |
|---|---|---|
| Suíte de verificação como projeto separado, com IBGE falso controlável | O E1 e o E4 precisam provar o **mesmo** comportamento (FR-021, SC-008), inclusive diante de falha e lentidão da fonte. Uma suíte por implementação mediria duas coisas diferentes | Testes só dentro de cada implementação divergiriam com o tempo; ferramentas geradoras (Schemathesis) não exercitam a fonte fora do ar nem a cópia vencida |
| Consulta única por chave (uma tarefa compartilhada por recurso, T050) | Caso de borda da spec: vários pedidos simultâneos pelo mesmo dado não devem multiplicar as consultas ao IBGE | Sem compartilhar a consulta, N pedidos simultâneos viram N consultas, contra o princípio V. Uma trava simples também não basta: com a fonte travada, os pedidos fazem fila e o último espera N prazos |

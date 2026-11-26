# Implementation Plan: E0 — Inventário e conectividade das fontes

**Branch**: `001-inventario-fontes` | **Date**: 2026-11-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-inventario-fontes/spec.md`

## Summary

Ferramenta de linha de comando (`inventario`) que lê `discovery/sources.json`, faz uma única consulta de leitura, sequencial e espaçada, a cada fonte com `probe_url` e grava dois relatórios com timestamp em `discovery/reports/`: um JSON validado por JSON Schema e um HTML autocontido.

Para cada fonte, o relatório traz status, latência, formato declarado e detectado, tamanho, autenticação observada, redirecionamentos, data de coleta, estrutura da amostra (só nomes de campos e tipos, nunca valores) e a divergência entre a hipótese do catálogo e o observado.

Abordagem: Python com `httpx` em modo streaming, com teto de leitura de 1 MiB. Falhas são classificadas em causas de domínio, e relógio e espera são injetáveis para testar o ritmo. Os testes rodam sem rede, com `respx`. Detalhes das decisões em [research.md](research.md).

## Technical Context

**Language/Version**: Python ≥ 3.11 (`requires-python = ">=3.11"`; ambiente local: 3.15)

**Primary Dependencies**: `httpx` (runtime). Biblioteca padrão para CLI (`argparse`), modelos (`dataclasses`), formatos (`json`, `csv`, `xml.etree`), HTML (`string.Template` + `html.escape`) e fuso (`zoneinfo`)

**Storage**: arquivos. Lê o catálogo JSON e grava relatórios JSON e HTML em `discovery/reports/`. Corpos de resposta nunca vão para o disco

**Testing**: `pytest` + `respx` (simulação do `httpx`, sem rede) + `jsonschema` (validação do relatório contra o contrato)

**Target Platform**: máquina local do desenvolvedor (macOS; nada específico de plataforma)

**Project Type**: CLI (um pacote Python gerenciado por `uv`)

**Performance Goals**: rodada 1 em < 1 min (SC-001). Com 3 sondas esgotando o tempo limite: 3 × 15 s + 2 × 2 s = 49 s. Pior caso patológico (conexão lenta e servidor parado antes do primeiro bloco): ≈ 94 s, aceito e registrado no R8 do research.md

**Constraints**: 1 consulta por fonte por execução, sem paralelismo nem nova tentativa; intervalo ≥ 1 s (padrão 2 s); tempo limite ≤ 60 s (padrão 15 s); leitura ≤ 1 MiB por resposta; no máximo 5 redirecionamentos; nenhum valor de resposta nos relatórios

**Scale/Scope**: catálogo com cerca de 14 fontes hoje (3 com sonda); amostra de até 5 registros por fonte

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Como o plano atende | Situação |
|---|---|---|
| I. Fontes oficiais primeiro | Só consulta `probe_url` de órgãos oficiais do catálogo; cada resultado traz `url_documentacao`; o relatório avisa que licença, limites e termos dependem da documentação oficial (FR-020) | ✅ |
| II. Rastreabilidade | Cada resultado carrega `fonte_id`, `url_teste`, `url_final` e `coletado_em` (UTC); a execução registra ferramenta e versão, catálogo e `schema_version`, filtros e configuração. Não há "id de registro" porque a sonda não devolve dados de negócio | ✅ |
| III. Verificar antes de afirmar | Grau do catálogo e grau sugerido lado a lado, com escopo limitado a conectividade e autenticação (R11); o catálogo nunca é alterado automaticamente | ✅ |
| IV. Testes sem rede | Suíte inteira com `respx`; chamadas reais só na execução manual (quickstart §2), com data registrada no relatório | ✅ |
| V. Resiliência | Tempo limite por consulta, causas de erro de domínio (R3), falha isolada por fonte, respeito a 429 sem nova tentativa. **Sem cache**: ver justificativa abaixo | ✅ (justificado) |
| VI. Contrato como fronteira | Não é serviço HTTP, então não há OpenAPI em `contracts/` na raiz. O contrato da ferramenta é a CLI e o JSON Schema do relatório, em `specs/001-inventario-fontes/contracts/` | ✅ (n/a para OpenAPI) |
| VII. Privacidade | O modelo de amostra não tem campo para valor (R5); teste com dados pessoais fictícios (SC-004); corpos não são gravados | ✅ |
| VIII. Cautela jurídica e financeira | Não se aplica: não responde perguntas jurídicas nem financeiras | n/a |
| IX. Segredos fora do código | Nenhuma credencial usada ou aceita; `User-Agent` genérico, sem dados do usuário | ✅ |
| X. Simplicidade | Um pacote, uma dependência de runtime, sem banco, fila, cache ou framework web; HTML com a biblioteca padrão | ✅ |

**Justificativa da ausência de cache (V)**: o princípio pede cache "quando o dado muda pouco" para serviços que repassam dados. O E0 existe para observar a fonte agora: um cache esconderia justamente indisponibilidade e mudanças de autenticação. O limite de 1 consulta por fonte por execução já protege a fonte.

**Reavaliação pós-design (Fase 1)**: nenhum artefato introduziu violação. O schema do relatório (`additionalProperties: false`, `CampoAmostra` só com `caminho` e `tipos`) reforça o princípio VII por construção. **Gate: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/001-inventario-fontes/
├── spec.md
├── plan.md              # este arquivo
├── research.md          # decisões R1–R13
├── data-model.md        # entidades, invariantes, transições
├── quickstart.md        # validação ponta a ponta
├── contracts/
│   ├── cli.md                   # opções, saída, códigos de saída
│   └── relatorio.schema.json    # JSON Schema do relatório v1
├── checklists/
│   └── requirements.md
├── tasks.md             # /speckit-tasks
└── RESULTS.md           # fechamento do experimento
```

### Source Code (repository root)

```text
experiments/python/discovery/
├── pyproject.toml            # projeto uv; script "inventario"; httpx; dev: pytest, respx, jsonschema
├── README.md                 # como rodar (aponta para o quickstart)
├── src/inventario_fontes/
│   ├── __init__.py           # __version__
│   ├── __main__.py           # python -m inventario_fontes
│   ├── cli.py                # argparse, filtros, códigos de saída, resumo no terminal
│   ├── catalogo.py           # leitura e validação do sources.json → Fonte
│   ├── modelos.py            # dataclasses: Fonte, ResultadoSondagem, EstruturaAmostra, CampoAmostra, Divergencia, Execucao, Resumo
│   ├── sonda.py              # consulta única com httpx (stream, teto, redirecionamentos), classificação de falhas, detecção de login
│   ├── formato.py            # detecção de formato (declarado × detectado)
│   ├── amostra.py            # inferência de estrutura JSON/CSV/XML sem reter valores
│   ├── avaliacao.py          # hipótese × observado, grau sugerido
│   ├── execucao.py           # laço sequencial, ritmo (relógio/espera injetáveis), interrupção, resumo
│   └── relatorio/
│       ├── __init__.py
│       ├── json_.py          # serialização + nome de arquivo sem sobrescrita
│       └── html.py           # string.Template + html.escape, CSS inline
└── tests/
    ├── conftest.py           # fixtures: catálogo mínimo, relógio falso, bloqueio de rede real
    ├── fixtures/             # respostas gravadas/sintéticas (IBGE, BCB, Câmara, HTML de erro, CSV, XML)
    ├── unit/                 # catalogo, formato, amostra, avaliacao, sonda (respx)
    ├── integration/          # execução completa com respx: cenários do quickstart §1
    └── contract/             # relatório JSON valida contra specs/.../relatorio.schema.json
```

**Structure Decision**: um único projeto `uv` em `experiments/python/discovery/`, conforme o roteiro e o prompt do E0. O pacote se chama `inventario_fontes`, para não colidir com nomes genéricos. Os testes ficam no próprio projeto, divididos em unit, integration e contract. O teste de contrato lê o schema diretamente de `specs/001-inventario-fontes/contracts/`, para que contrato e implementação não divirjam. Os relatórios saem em `discovery/reports/` (fora do pacote), e as fixtures usam dados sintéticos ou respostas reais reduzidas, sem dados pessoais.

## Complexity Tracking

Sem violações a justificar. A ausência de cache está justificada no Constitution Check.

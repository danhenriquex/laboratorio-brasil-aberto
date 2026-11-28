# Implementation Plan: E8 — Serviço de localidades (IBGE), em Rust

**Branch**: `005-localidades-rust` | **Date**: 2026-11-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-localidades-rust/spec.md`, que reaproveita o comportamento de [specs/002-servico-localidades/spec.md](../002-servico-localidades/spec.md)

## Summary

Reimplementar o serviço de localidades do E1, do E4 e do E7 em **Rust 1.100, com axum sobre tokio**, cumprindo o mesmo contrato ([contracts/localidades/openapi.yaml](../../contracts/localidades/openapi.yaml)) e passando na mesma suíte de caixa-preta (82 cenários). Depois, comparar as quatro implementações com as 9 medidas do E4 e a mesma avaliação qualitativa.

O desenho reproduz as decisões já validadas:

- prazo total por consulta;
- cópia com validade e cópia vencida em caso de falha;
- consulta compartilhada **inclusive na falha**;
- códigos e siglas validados contra o data-model;
- problem+json com URNs;
- métricas e registro com os mesmos nomes.

Como no E7, as lições das convergências do E4 (T044 a T050) e a do E7 (`OPTIONS *`) entram **no desenho**, e o FR-009 pede registrar como cada uma se comportou em Rust. Detalhes em [research.md](research.md).

## Technical Context

**Language/Version**: Rust 1.100.1, a estável mais recente, de 2026-11-27, conferida em rust-lang.org e blog.rust-lang.org/releases em 2026-11-28. Instalação pelo `rustup`, o instalador oficial (o Homebrew ainda está na 1.100.0). O `Cargo.toml` declara `edition = "2024"` e `rust-version = "1.100"`.

**Primary Dependencies** (versões conferidas na API do crates.io em 2026-11-28):

- **Servidor HTTP:** `axum` 0.8.9 sobre `tokio` 1.54.1 (e `hyper` 1.13.0, que vem com ele);
- **Cliente HTTP:** `reqwest` 0.13.5;
- **JSON:** `serde` 1.0.229 e `serde_json` 1.0.154;
- **Métricas:** `prometheus` 0.14.0, que escreve o formato texto do Prometheus (R10);
- **Dobra de texto:** `unicode-normalization` 0.1.26 e `caseless` 0.2.2;
- **Consulta compartilhada:** `futures` 0.3.34 (`Shared`);
- **Leitura da *query*:** `percent-encoding` 2.3.2;
- **Data e UUID:** `time` 0.3.55 e `uuid` 1.29.3.

**Storage**: nenhum. A cópia guardada fica em memória (`HashMap` protegido por `Mutex`), e as fixtures são as mesmas do E1, em `contracts/localidades/fixtures-ibge/`

**Testing**:

- `cargo test`, com `#[tokio::test]`. O IBGE simulado é um servidor axum em `127.0.0.1:0`, dentro do próprio teste, como o `httptest` no E7. Nenhuma biblioteca de *mock* externa;
- suíte de caixa-preta compartilhada (`contracts/localidades/verificacao/`), via `verificar.sh "experiments/rust/localidades/target/release/localidades"`.

**Build**: `cargo build --release`, que gera um binário único otimizado. O build com otimização é uma das medidas (FR-006) e é registrado tal como for

**Target Platform**: máquina local (macOS, arm64). Escuta em `127.0.0.1`

**Project Type**: web service (API HTTP somente leitura)

**Performance Goals**:

- os mesmos do E1, com pedido atendido pela cópia guardada abaixo de 500 ms (SC-003 do E1);
- partida até o `/health` bem abaixo dos 30 s do `verificar.sh`.

**Constraints**:

- as do E1: prazo total de 10 s, no máximo uma consulta por pedido, validade de 24 h, página de até 500 itens e nenhuma credencial;
- a mesma configuração `LOCALIDADES_*`, com as regras de validação do E4 e do E7 (FR-003);
- a mesma ordem de nomes das outras três implementações (FR-004).

**Scale/Scope**: o do E1: 27 UFs e 5.571 municípios

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Como o plano atende | Situação |
|---|---|---|
| I. Fontes oficiais primeiro | Mesma fonte e mesma procedência do E1 | ✅ |
| II. Rastreabilidade | `meta` idêntico ao do E1, com `coletado_em` da consulta original no mesmo formato, conferido pela suíte | ✅ |
| III. Verificar antes de afirmar | Versões conferidas em rust-lang.org e no crates.io em 2026-11-28. O 405 do axum para método não suportado foi lido na documentação; o resto do comportamento da pilha HTTP (caminho mal codificado, `OPTIONS *`, barras repetidas) será conferido por teste antes de se decidir algo sobre ele | ✅ |
| IV. Testes sem rede | IBGE simulado em loopback, fixtures do repositório e verificação em sandbox sem rede externa, com `cargo test --offline` depois de popular o registro local de crates | ✅ |
| V. Resiliência | Prazo total com `tokio::time::timeout`, erros de domínio, cópia vencida e consulta compartilhada inclusive na falha | ✅ |
| VI. Contrato como fronteira | Mesmo `openapi.yaml`. Nenhum código compartilhado com as outras implementações, só o contrato, as fixtures e a suíte | ✅ |
| VII. Privacidade | Sem dados pessoais. O registro não guarda IP | ✅ |
| VIII. Cautela jurídica e financeira | Não se aplica | n/a |
| IX. Segredos fora do código | Nenhuma credencial | ✅ |
| X. Simplicidade | Um binário, o framework mais comum do ecossistema e crates pequenas e mantidas. Sem banco, Redis nem Docker | ✅ (ver Complexity Tracking) |

**Linguagens (Additional Constraints, constituição 1.1.0)**: Rust é permitido, "na versão estável vigente, confirmada na documentação oficial no início de cada experimento e registrada no plano". Escolha: **Rust 1.100.1** (R1). É a primeira vez de Rust no projeto, e ela entra como experimento, com pergunta, timebox e `RESULTS.md`, reimplementando um serviço que já tem contrato e suíte.

**Reavaliação pós-design (Fase 1)**: o desenho não acrescenta comportamento nem dependência além das listadas, e o contrato não muda. A suíte só ganha cenários se o E8 revelar um caso novo, e eles precisam passar também nas outras três (FR-002). **Gate: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/005-localidades-rust/
├── spec.md              # E8: referência à spec do E1 + US6 (comparação entre quatro)
├── plan.md              # este arquivo
├── research.md          # decisões R1–R15 do Rust e método de comparação
├── data-model.md        # mapeamento das entidades do E1 para tipos Rust
├── quickstart.md        # setup do Rust, testes, verificação, comparação
├── contracts/
│   └── README.md        # aponta para o contrato compartilhado
├── checklists/
│   └── requirements.md
├── ergonomia.md         # diário de ergonomia, escrito durante a implementação
├── tasks.md             # /speckit-tasks
└── RESULTS.md           # fechamento e comparação com as outras três
```

### Source Code (repository root)

```text
experiments/rust/localidades/               # E8
├── Cargo.toml, Cargo.lock                  # edition 2024; dependências fixadas
├── README.md
├── src/
│   ├── main.rs                             # lê a configuração, monta as peças, sobe o servidor
│   ├── lib.rs                              # expõe os módulos para os testes de integração
│   ├── config.rs                           # LOCALIDADES_* lidas e validadas à mão (R11)
│   ├── dominio.rs                          # structs, dobrar, paginação, validação, UFs oficiais — sem axum
│   ├── erros.rs                            # ErroDominio (tipo, título, status) e os seis tipos
│   ├── fonte.rs                            # cliente do IBGE: prazo total, classificação, normalização
│   ├── cache.rs                            # cópia com validade + consulta compartilhada
│   ├── servico.rs                          # casos de uso — sem axum
│   ├── api.rs                              # rotas v1, envelope, problem+json, leitura da query
│   ├── topo.rs                             # camada de topo: correlação, caminho irregular, fallbacks (R3)
│   └── operacao.rs                         # /health, /metrics, registro JSON, métricas
└── tests/                                  # testes de integração (um arquivo por história)

contracts/localidades/verificacao/          # compartilhado: só muda se o E8 revelar caso novo (passa nos quatro)
specs/005-localidades-rust/medicao/         # medir.py estendido para o E8 (US6)
```

**Structure Decision**:

- **Onde fica:** um *crate* Cargo em `experiments/rust/localidades/`, ao lado das outras implementações (`experiments/<linguagem>/`).
- **Módulos:** espelham as camadas das outras (`dominio`, `fonte`, `cache`, `servico`, `api`, `operacao`), mais `topo`, que concentra o que no E7 ficou no handler de topo. `dominio` e `servico` não dependem do axum.
- **Testes:** os de unidade ficam no próprio módulo (`#[cfg(test)] mod tests`), e os de integração em `tests/`, o costume da linguagem.
- **Binário e biblioteca:** um `lib.rs` expõe os módulos para os testes de integração, e o `main.rs` só monta e sobe.
- **Recursos compartilhados:** fixtures e contrato são lidos de `contracts/localidades/`, sem cópia.

## Complexity Tracking

| Item | Por que é necessário | Alternativa mais simples rejeitada porque |
|---|---|---|
| `axum` + `tokio` | A biblioteca padrão do Rust não tem servidor HTTP nem runtime assíncrono. O axum é o caminho mais comum do ecossistema, como o FastAPI, o Spring e o `net/http` nas outras | Um servidor sem framework sobre o `hyper` daria mais controle, mas foge do caminho comum, que é o que o experimento compara |
| `reqwest` | A biblioteca padrão não tem cliente HTTP, nem com TLS | O cliente do `hyper` exigiria montar TLS e conexões à mão |
| `prometheus` | Dá o formato texto do Prometheus com os nomes exatos do contrato | O `prometheus-client`, do próprio projeto Prometheus, escreve OpenMetrics e muda o tipo do conteúdo; ver R10 |
| `unicode-normalization` e `caseless` | A biblioteca padrão não tem normalização NFKD nem *casefold* | Uma tabela manual de acentos daria divergência em casos raros |
| `futures` (`Shared`) | Compartilha o resultado de uma consulta, inclusive o erro, entre os pedidos que esperam | Um mapa de canais escrito à mão resolve, mas o `Shared` é a peça comum do ecossistema |

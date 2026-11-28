---
description: "Lista de tarefas do E8 — Serviço de localidades (IBGE), em Rust"
---

# Tasks: E8 — Serviço de localidades (IBGE), em Rust

**Input**: Documentos de design em `specs/005-localidades-rust/`. O comportamento vem de `specs/002-servico-localidades/`.

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/localidades/openapi.yaml](../../contracts/localidades/openapi.yaml), [quickstart.md](quickstart.md)

**Tests**: incluídos. O critério de pronto é a suíte de caixa-preta (FR-002), e a constituição (princípio IV) proíbe rede nos testes. Em cada história:

1. escreva os testes da implementação primeiro e confirme que falham;
2. implemente;
3. rode os cenários da história na suíte de caixa-preta contra o binário.

**Referência de comportamento**: o código do E1 (`experiments/python/localidades/`), do E4 (`experiments/java/localidades/`) e do E7 (`experiments/go/localidades/`) é a referência executável de cada regra. Na dúvida, o comportamento do E1 e a suíte decidem.

**Lições anteriores**: as lacunas das convergências do E4 (T044 a T050) e a do E7 (`OPTIONS *`) entram aqui como tarefa desde o início, e cada uma é registrada no `RESULTS.md` (FR-009).

**Organization**: tarefas agrupadas por história de usuário. Cada fase vira **uma branch e um PR**, e a próxima só começa depois do merge da anterior.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: história de usuário: US1 a US5, as do E1, e US6, a comparação

## Path Conventions

- **Projeto:** `experiments/rust/localidades/`, chamado de **`R/`** abaixo.
- **Código:** `R/src/<módulo>.rs`, com os testes de unidade no próprio módulo (`#[cfg(test)] mod tests`) e os de integração em `R/tests/`.
- **Comandos:**
  - testes: `(cd experiments/rust/localidades && cargo clippy --all-targets -- -D warnings && cargo test)`;
  - binário: `(cd experiments/rust/localidades && cargo build --release)`;
  - caixa-preta: `contracts/localidades/verificacao/verificar.sh "experiments/rust/localidades/target/release/localidades" [-k filtro]`, a partir da raiz.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Rust, crate, dependências fixadas, diário de ergonomia e a sondagem da pilha HTTP que o research R3 pede antes de decidir.

- [X] T001 Instalar o Rust 1.100 com o `rustup` (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`), **depois de confirmação do usuário** (é uma mudança no sistema; o usuário pode preferir rodar no próprio terminal). Conferir com `rustc --version`, que deve mostrar `rustc 1.100.x`, e registrar a versão exata e o tempo gasto em `specs/005-localidades-rust/ergonomia.md`.
- [X] T002 Criar o crate em `R/` com `cargo new --name localidades experiments/rust/localidades`, declarar `edition = "2024"` e `rust-version = "1.100"` no `R/Cargo.toml`, criar `R/rust-toolchain.toml` com o canal `1.100` e fixar as dependências do research com `cargo add`: `axum@0.8.9`, `tokio@1.54.1` (recursos `macros`, `rt-multi-thread`, `net`, `signal`, `time`, `sync`), `reqwest@0.13.5` (sem os recursos padrão de TLS do sistema se o padrão pedir OpenSSL; com `rustls`), `serde@1.0.229` (`derive`), `serde_json@1.0.154`, `prometheus@0.14.0`, `unicode-normalization@0.1.26`, `caseless@0.2.2`, `futures@0.3.34`, `percent-encoding@2.3.2`, `time@0.3.55` (`formatting`), `uuid@1.29.3` (`v4`), e, como dependência de teste, `tower` com o recurso `util` (para o `oneshot`). Versionar `R/Cargo.toml` e `R/Cargo.lock`. Acrescentar ao `.gitignore` da raiz `experiments/rust/localidades/target/` (o `target/` já ignorado pelo padrão geral também vale, mas a linha documenta).
- [X] T003 [P] Criar `R/README.md`, espelhando o README do E7: pergunta do E8, pré-requisitos (Rust 1.100 pelo `rustup`), comandos de teste, de verificação e de execução, e links para o quickstart e o contrato. Criar também `specs/005-localidades-rust/ergonomia.md`, o diário do FR-007, com uma seção por ponto (setup, testes, contrato, erros e métricas) e a seção "Lições anteriores" com a tabela das 8 lições do FR-009 vazia.
- [X] T004 Criar `R/src/main.rs` mínimo com axum, que sobe em `127.0.0.1:8000` com `GET /health` devolvendo `{"status":"ok"}`, e medir o primeiro `cargo build --release` (registrar o tempo com o cache frio no diário). Com o esqueleto rodando, **sondar a pilha HTTP** com pedidos crus (research R3) e registrar no diário o que o `hyper` e o axum fazem com: `GET /v1/municipios/%ZZ`, `GET //health`, `GET /./health`, `GET /x/../health`, `GET /health;x`, `POST /health`, `TRACE /health`, `OPTIONS *` e `GET /health` com `Accept: application/xml`. Esse resultado decide a forma da camada de topo (T013): se o `%ZZ` for recusado antes da aplicação, avaliar a solução do E7 (sanear a linha do pedido) e registrar a decisão no research como atualização do R3.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: domínio, configuração, erros, cliente do IBGE e camada de topo, já com as lições anteriores.

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

### Testes da fundação (escrever primeiro)

- [X] T005 [P] Criar o apoio de testes em `R/tests/apoio/mod.rs`: localizar a raiz do repositório subindo até achar `contracts/localidades` e ler `contracts/localidades/fixtures-ibge/*.json`; um relógio falso com instante inicial `2026-11-26T12:00:00.123Z`, fonte monotônica e `avancar(Duration)`; e um IBGE simulado (servidor axum em `127.0.0.1:0`) que serve as fixtures por caminho, conta os pedidos por caminho e simula atraso, status, corpo e fonte travada. Nenhum teste fala com host externo.
- [X] T006 [P] Escrever os testes de unidade de `R/src/dominio.rs`, com os mesmos casos do `dominio_test.go` do E7: `dobrar` (`"Niterói"` → `"niteroi"`, `"SÃO"` → `"sao"`, apóstrofo mantido); ordenação por (nome dobrado, código); `filtrar_por_nome`; `paginar` (`paginas = ceil(total/itens)`, total 0 → `paginas` 0, página além do fim vazia com o total, página enorme sem estouro); `resolver_uf` (`" rj "` e `"33"` → `"33"`, `"XX"` e `"99"` → `nao-encontrado`, `"R1"`, `"123"`, `""` e `"３３"` → `entrada-invalida`); `validar_codigo_municipio` ("`^\d{7}$`" só ASCII, `"330455７"` recusado); `validar_paginacao` ("inteiro de 1 a `ITENS_MAX` (padrão 500)", `pagina` como `i64`); `validar_nome` ("aparado; de 2 a 60 caracteres", contados em caracteres e não em bytes); e um `repr` que imita o do Python nas mensagens (`'R1'`, `"d'Oeste"`).
- [X] T007 [P] Escrever os testes de unidade de `R/src/config.rs`: os padrões do R14 do E1; a leitura das `LOCALIDADES_*` e a URL sem barra final; a recusa, com mensagem que cita a variável e o valor, de `abc`, `0`, `-1`, `NaN`, `inf`, `infinity`, `1e300`, `1e400` e `0.0001` em prazo e validade (lição da **T049**: "número finito entre 0,001 e 10⁹"), de `0` e `1.5` em `LOCALIDADES_ITENS_MAX`, de `ftp://ibge` em `LOCALIDADES_IBGE_URL` e de `abc` e `99999` em `LOCALIDADES_PORTA`; e a aceitação dos limites `0.001` e `1000000000`.
- [X] T008 [P] Escrever `R/tests/fonte.rs` com o IBGE simulado, espelhando o `ibge_test.go` do E7: classificação (conexão recusada, 503 e 429 → `fonte-indisponivel`; atraso de 300 ms com prazo de 50 ms → `fonte-lenta` em menos de 300 ms; 404, 301, HTML com 200, JSON sem campo obrigatório e lista vazia de UFs → `resposta-inesperada-da-fonte`); normalização (27 UFs, 92 municípios do RJ, objeto ou lista de 1, `[]` → `nao-encontrado`, `5101837` sem microrregião aceito, sem região imediata recusado); formato exato de códigos e siglas (T048 e T049 do E1); exatamente 1 pedido por chamada, o `User-Agent` do laboratório e a medição também na falha.

### Implementação da fundação

- [X] T009 [P] Implementar `R/src/erros.rs`: `ErroDominio` com os seis construtores do data-model, `de_fonte()`, `Clone` e `IntoResponse` (problem+json com `type`, `title`, `status`, `detail`; o `correlacao_id` é completado pela camada de topo).
- [X] T010 Implementar `R/src/dominio.rs` conforme o data-model do E8, sem depender do axum: as *structs* com `Serialize`; `UFS_OFICIAIS`; `dobrar` (NFKD com `unicode-normalization`, sem marcas combinantes, `caseless::default_case_fold_str`); `ordenar`, `filtrar_por_nome`, `paginar`, `resolver_uf`, `validar_codigo_municipio`, `validar_paginacao`, `validar_nome` e `repr`. Ao final, T006 passa.
- [X] T011 Implementar `R/src/config.rs` conforme o research R11, recusando explicitamente valores não finitos (`is_finite()`), com a mensagem do E1. Ao final, T007 passa.
- [X] T012 Implementar `R/src/fonte.rs` conforme o research R6: `reqwest` sem redirecionamento, com o `User-Agent` `laboratorio-brasil-aberto-localidades/0.1.0`; prazo total com `tokio::time::timeout` cobrindo pedido e corpo; classificação e normalização do E1; medição por um callback (recurso, segundos) também na falha; mensagens sem o corpo do IBGE. Ao final, T008 passa.
- [X] T013 Implementar a camada de topo em `R/src/topo.rs` e `R/src/operacao.rs` (saúde), e escrever `R/tests/base.rs`, espelhando o `base_test.go` do E7. A forma segue o resultado da sondagem da T004:
  - correlação (`^[A-Za-z0-9._-]{1,64}$` ou UUID v4) numa extensão do pedido e no cabeçalho de toda resposta;
  - caminho cru com `;`, barras repetidas, segmentos `.` ou `..`, ou que não começa com `/` → 404 `nao-encontrado`, sem redirecionar (lições da **T050** do E4 e da **T044** do E7);
  - `fallback` e `method_not_allowed_fallback` do roteador → o mesmo 404, inclusive para `TRACE`, sem eco (lição da **T047**);
  - `panic` → 500 `erro-interno` sem rastro;
  - `GET /health` → `{"status":"ok"}` em `application/json`, ignorando o `Accept` (lição da **T048**);
  - o que o teste cobre: 404 em problem+json para `/v2/ufs`, `/ufs`, `/nada`, `/v1` e `/`; `POST`, `PUT`, `DELETE`, `PATCH` e `TRACE` no `/health` dão 404, e o `TRACE` não ecoa; `//health`, `/./health`, `/x/../health`, `/health;x` e `OPTIONS *` dão 404, com pedido cru num servidor de verdade; correlação válida volta igual e inválida vira UUID v4; `panic` vira 500 sem rastro; `Accept` não muda o formato.
- [X] T014 Implementar a base de `R/src/servico.rs`, sem depender do axum: `Meta` com `coletado_em` no formato do data-model (`.000Z` para 0 ms, testado), e `obter` chamando a fonte direto (a cópia guardada entra na T027).
- [X] T015 Montar `R/src/lib.rs` e `R/src/main.rs`: configuração com erro → mensagem em stderr e saída 2; cliente, serviço e roteador; servidor em `LOCALIDADES_HOST:LOCALIDADES_PORTA` com encerramento por SIGTERM terminando os pedidos em andamento. Gerar o binário e rodar `verificar.sh "experiments/rust/localidades/target/release/localidades" -k "contrato_valido or saude or correlacao"`.

**Checkpoint**: `cargo test` passa (domínio, configuração, cliente e base HTTP), e o binário sobe e responde `/health` pelo `verificar.sh`.

---

## Phase 3: User Story 1 - Listar estados e os municípios de um estado (Priority: P1) 🎯 MVP

**Goal**: `GET /v1/ufs`, `GET /v1/ufs/{uf}` e `GET /v1/ufs/{uf}/municipios` (sem o filtro por nome).

**Independent Test**: os cenários de `test_us1_ufs_municipios.py` e `test_paridade_ordenacao.py` (sem as buscas) passam contra o binário.

- [X] T016 [P] [US1] Escrever `R/tests/ufs.rs`, com os casos do `ufs_test.go` do E7: 27 UFs ordenadas (Acre primeiro); `/v1/ufs/rj`, `/v1/ufs/33` e `/v1/ufs/%20RJ%20`; `XX`, `99` e `R1` sem chamar o IBGE; RJ com 92 municípios e `paginacao {1, 100, 92, 1}`; página parcial e além do fim; `itens=0`, `itens=501`, `pagina=0`, `itens=1.5` e `pagina=x` com o detalhe do E1; **T045** (`pagina=99999999999`, `pagina` com 30 dígitos, `itens` repetido vale o último); **T046** (`itens=%ZZ`, `pagina=%E3` e `itens=%` crus dão 400); **T048** (`Accept: application/xml` em `/v1/ufs`); **T050** (`;` no caminho dá 404 sem consultar o IBGE); campos na ordem `dados`, `paginacao`, `meta`, e `paginacao` ausente em `/v1/ufs/{uf}`.
- [X] T017 [US1] Em `R/src/servico.rs`, implementar `listar_ufs`, `obter_uf` (UF ausente no IBGE → `resposta-inesperada-da-fonte`) e `listar_municipios(uf, pagina, itens, nome)` (validar, resolver, buscar, ordenar e paginar).
- [X] T018 [US1] Em `R/src/api.rs`, criar as três rotas com o envelope `Resposta<T>` e a leitura da *query* do research R4 (texto cru, `%` inválido ou UTF-8 inválido → 400, `+` como espaço, último valor, `pagina` que estoura `i64` como além do fim). Ao final, T016 passa.
- [X] T019 [US1] Rodar `verificar.sh "experiments/rust/localidades/target/release/localidades" -k "us1 or paridade or contrato_valido"` e registrar no diário o que exigiu ajuste.

**Checkpoint**: US1 verificada pela mesma suíte. É o MVP do E8.

---

## Phase 4: User Story 2 - Consultar um município pelo código oficial (Priority: P1)

**Goal**: `GET /v1/municipios/{codigo}`.

**Independent Test**: `test_us2_municipio.py` passa contra o binário.

- [X] T020 [P] [US2] Escrever `R/tests/municipio.rs`, com os casos do `municipio_test.go` do E7: Rio de Janeiro com UF e regiões; `9999999` → 404 com o detalhe do E1; `12ab`, `123456`, `12345678` e `330455７` → 400 sem chamar o IBGE; `3545803` com apóstrofo sem escape; `5101837` e `5300108`; e a lição da **T044** com pedido cru (`/v1/municipios/%ZZ`, `%`, `%E3` e `/v1/ufs/R%ZZ/municipios` → 400; `/v1/municipios/%2F` → 404; todos em problem+json com correlação).
- [X] T021 [US2] Em `R/src/servico.rs`, implementar `obter_municipio(codigo)`.
- [X] T022 [US2] Em `R/src/api.rs`, criar `GET /v1/municipios/{codigo}`, decodificando o segmento a partir do caminho cru para recusar o escape inválido como entrada inválida. Ao final, T020 passa.
- [X] T023 [US2] Rodar `verificar.sh "experiments/rust/localidades/target/release/localidades" -k us2` e registrar no diário como a T044 se comportou em Rust.

---

## Phase 5: User Story 3 - Comportamento previsível quando o IBGE falha ou demora (Priority: P2)

**Goal**: cópia guardada com validade, consulta compartilhada **inclusive na falha** e cópia vencida em caso de falha.

**Independent Test**: `test_us3_falhas.py` passa contra o binário.

- [X] T024 [P] [US3] Escrever os testes de unidade de `R/src/cache.rs` com o relógio falso: acerto dentro da validade; falta depois dela; cópia vencida como `desatualizado` quando a fonte falha; "não encontrado" e erros não guardados; "não encontrado" não usa cópia vencida; 20 pedidos simultâneos geram **uma** consulta e recebem o mesmo resultado, **inclusive o mesmo erro**; só quem iniciou conta como falta; e um pedido que desiste (futuro abandonado) não cancela a consulta dos outros.
- [X] T025 [P] [US3] Escrever `R/tests/falhas.rs`: fonte fora → 502; resposta inválida → 502; fonte lenta → 504 dentro do prazo; cópia válida não consulta a fonte, e `/v1/ufs` e `/v1/ufs/{uf}` dividem a cópia; cópia vencida servida com `desatualizado: true` e o `coletado_em` original; 5 pedidos simultâneos com a fonte travada dão 504 no prazo, com uma consulta; e um cliente que desiste não atrapalha os outros nem conta como erro interno.
- [X] T026 [US3] Implementar `R/src/cache.rs` conforme o research R7: `HashMap` com `Mutex` nunca segurado num `await`; consultas em andamento como `Shared` sobre um `tokio::spawn`, que não morre com o pedido; relógios injetáveis. Ao final, T024 passa.
- [X] T027 [US3] Em `R/src/servico.rs`, trocar o `obter` para usar o cache, com o `meta` vindo da entrada e o resultado da cópia disponível para as métricas e o registro. Ao final, T025 passa.
- [X] T028 [US3] Rodar `verificar.sh "experiments/rust/localidades/target/release/localidades" -k us3` e registrar no diário a comparação da consulta compartilhada com o `asyncio` do E1, o `CompletableFuture` do E4 e o `singleflight` do E7.

---

## Phase 6: User Story 4 - Encontrar um município pelo nome dentro de um estado (Priority: P3)

**Goal**: o parâmetro `nome` em `GET /v1/ufs/{uf}/municipios`.

**Independent Test**: `test_us4_busca.py` e as buscas de `test_paridade_ordenacao.py` passam contra o binário.

- [ ] T029 [P] [US4] Escrever `R/tests/busca.rs`, com os casos do `busca_test.go` do E7: `niteroi` e `NITERÓI`; `são` e `SAO` em SP, em ordem e paginados; sem resultado com `dados: []`; `a`, `"  a  "`, `""` e 61 caracteres → 400 sem consultar; duas buscas na mesma UF, uma consulta; e a lição da **T046** com `nome=%ZZ`, `nome=s%E3o` e `nome=%` crus → 400.
- [ ] T030 [US4] Acrescentar o `nome` opcional a `listar_municipios` em `R/src/servico.rs` e à rota de `R/src/api.rs` (validar, filtrar, ordenar e paginar). Ao final, T029 passa.
- [ ] T031 [US4] Rodar `verificar.sh "experiments/rust/localidades/target/release/localidades" -k "us4 or paridade"`.

---

## Phase 7: User Story 5 - Saber se o serviço está saudável e como está sendo usado (Priority: P3)

**Goal**: métricas com os nomes do contrato, registro JSON por pedido e correlação verificada de fora.

**Independent Test**: `test_us5_operacao.py` passa contra o binário, e a suíte inteira também.

- [ ] T032 [P] [US5] Escrever `R/tests/operacao.rs`: o `/metrics` expõe `localidades_pedidos_total{rota,status}`, `localidades_erros_total{tipo}`, `localidades_cache_total{resultado}` e `localidades_fonte_duracao_segundos_bucket{recurso}` com as faixas do E1, sem sufixo de unidade; rota inexistente conta como `rota="nao-encontrado"`; o `/metrics` responde `text/plain` com qualquer `Accept`; cada pedido gera uma linha JSON com `momento`, `nivel`, `correlacao_id`, `metodo`, `rota`, `status`, `duracao_ms`, `cache` e `fonte_ms`, nessa ordem e sem IP, com `nivel` `error` nos 5xx.
- [ ] T033 [P] [US5] Implementar as métricas em `R/src/operacao.rs` com o `prometheus` 0.14.0 (registro próprio, `IntCounterVec`, `HistogramVec` com as faixas do E1, `TextEncoder`) e o `GET /metrics`.
- [ ] T034 [US5] Implementar o registro JSON em `R/src/operacao.rs` com `serde_json` (research R12) e integrá-lo à camada de topo, com o estado do pedido numa extensão (rota, uso da cópia, tipo de erro e tempo da fonte). Ao final, T032 passa.
- [ ] T035 [US5] Rodar a suíte inteira, `verificar.sh "experiments/rust/localidades/target/release/localidades"`, e confirmar que **todos** os 82 cenários passam (SC-001).

**Checkpoint**: E8 funcionalmente equivalente às outras três, verificado pela mesma suíte.

---

## Phase 8: User Story 6 - Comparar o E1, o E4, o E7 e o E8 com medidas (Priority: P2)

**Goal**: as 9 medidas do FR-006 para as quatro implementações e a avaliação qualitativa do FR-007, pelo método do research R15.

**Independent Test**: a tabela comparativa do `RESULTS.md` fica preenchida para as quatro implementações, com data e método.

- [ ] T036 [US6] Criar `specs/005-localidades-rust/medicao/medir.py` e `medir.sh` a partir dos do E7, acrescentando o E8: build `cargo build --release` (com o `target/` frio e quente), suíte `cargo test`, subida pelo binário otimizado, artefato = tamanho do binário, linhas `.rs` de produção e de teste, e dependências diretas lidas do `Cargo.toml`. A tabela de saída passa a ter quatro colunas.
- [ ] T037 [US6] Rodar o `medir.sh` na mesma máquina e no mesmo dia, com os caches dos quatro ecossistemas populados, e guardar a saída em `specs/005-localidades-rust/medicao/resultado-AAAA-MM-DD.md`.
- [ ] T038 [US6] Consolidar o `specs/005-localidades-rust/ergonomia.md` numa nota de 1 a 5 com justificativa para cada ponto do FR-007, ao lado das notas do E1, do E4 e do E7. Toda diferença citada traz a medida e o contexto (FR-008).

---

## Phase 9: Polish & Fechamento do experimento

- [ ] T039 Verificar sem rede externa (SC-004), com o perfil do quickstart §3: `cargo test --offline` e a suíte de caixa-preta, os dois dentro do sandbox, mais um `curl` ao IBGE que precisa falhar no mesmo sandbox.
- [ ] T040 Fazer a execução real contra o IBGE, conforme o quickstart §5, com as quatro implementações lado a lado recebendo os mesmos pedidos, e comparar os corpos ignorando só o `coletado_em`, a correlação e o `instance` do Spring.
- [ ] T041 [P] Acrescentar a `docs/adr/0001-convencoes-comuns-de-api.md` uma seção "Confirmação no E8", com o que a quarta implementação mostrou.
- [ ] T042 Escrever `specs/005-localidades-rust/RESULTS.md` a partir de `docs/templates/RESULTS.md`, com a resposta curta, a tabela das 9 medidas para as quatro implementações, a tabela das **8 lições** (FR-009, SC-006), as limitações (o E8 veio depois das outras três) e os próximos passos (os E2 e E3 do roteiro, e a decisão sobre qual implementação "se gradua").
- [ ] T043 [P] Atualizar `docs/roteiro.md` com a data de conclusão do E8, e o painel de comparação (artefato "Localidades: Python × Java × Go") com a quarta coluna, se o usuário pedir.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1):** sem dependências. A T001 depende da confirmação do usuário, e a T004 decide a forma da T013.
- **Fundação (Fase 2):** depende do Setup e bloqueia todas as histórias.
- **US1 e US2 (Fases 3 e 4):** dependem da Fundação; a ordem de entrega segue a prioridade.
- **US3 (Fase 5):** troca o `obter` do serviço, então vem depois da US1 e da US2.
- **US4 (Fase 6):** depende da US1 (o mesmo handler e o mesmo serviço).
- **US5 (Fase 7):** fecha a suíte inteira, por isso vem depois das outras histórias.
- **US6 (Fase 8):** depende de a suíte inteira passar (T035).
- **Fechamento (Fase 9):** depende de todas.

### Ordem de entrega (uma branch e um PR por fase, esperando cada merge)

1. Setup + Fundação (T001–T015)
2. US1 (T016–T019) — MVP
3. US2 (T020–T023)
4. US3 (T024–T028)
5. US4 (T029–T031)
6. US5 (T032–T035)
7. US6 (T036–T038)
8. Fechamento (T039–T043)

### Parallel Opportunities

- Na Fundação, os testes T005 a T008 e o módulo de erros (T009) tocam arquivos diferentes.
- Em cada história, o teste [P] pode ser escrito enquanto a fase anterior está em revisão, sem commit antes do merge dela.
- Na US5, métricas (T033) e o teste (T032) são independentes.
- No Fechamento, ADR (T041) e roteiro (T043) são independentes.

## Parallel Example: Foundational

```text
T006 dominio (testes)   T007 config (testes)   T008 tests/fonte.rs   T009 erros.rs
        ↓                       ↓                      ↓
T010 dominio            T011 config            T012 fonte
                         ↓
       T013 camada de topo (forma decidida na T004) → T014 serviço → T015 main.rs
```

## Implementation Strategy

### MVP First

Setup, Fundação e US1 entregam um serviço que lista UFs e municípios e passa nos cenários da US1 e da paridade. Já é comparável com as outras três nesse recorte.

### Incremental Delivery

Cada história acrescenta um grupo de cenários da suíte. A US5 fecha os 82 cenários (SC-001), a US6 entrega a comparação entre as quatro, e o Fechamento confirma sem rede, contra o IBGE real, e registra as 8 lições (FR-009).

## Notes

- O `tasks.md` é a fonte da verdade. As issues do board espelham as fases.
- Nenhum teste fala com a rede externa: o IBGE é sempre um servidor local dentro do teste ou o IBGE falso da suíte.
- `cargo clippy --all-targets -- -D warnings` e `cargo fmt --check` sem saída fazem parte do "testes passam" de cada fase.
- Se a implementação em Rust revelar um caso novo que a suíte não cobre, o cenário entra na suíte compartilhada e precisa passar nas outras três (FR-002).

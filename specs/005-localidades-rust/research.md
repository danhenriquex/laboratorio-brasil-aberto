# Research: E8 — Serviço de localidades (IBGE), em Rust

**Data**: 2026-11-28 | **Spec**: [spec.md](spec.md) | **Plano**: [plan.md](plan.md)

As decisões de **comportamento** e de contrato são as do E1 ([specs/002-servico-localidades/research.md](../002-servico-localidades/research.md)): R1 (IBGE real), R4 (caixa-preta), R5 (cópia guardada), R6 (prazo e classificação), R7 (códigos como texto), R8 (dobra e ordenação), R9 (paginação), R10 (envelope e `meta`), R11 (erros), R12 (observabilidade) e R14 (configuração). O método de comparação é o do E4 (R13) e do E7 (R15), estendido para quatro implementações.

Abaixo está o "como" em Rust. As versões foram conferidas em 2026-11-28 em rust-lang.org, blog.rust-lang.org/releases e na API do crates.io.

## R1. Versão do Rust

- **Decision**: **Rust 1.100.1**, instalado pelo `rustup` (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`, o comando que rustup.rs mostra para Unix). O `Cargo.toml` declara `edition = "2024"` e `rust-version = "1.100"`, e um `rust-toolchain.toml` fixa o canal `1.100`.
- **Rationale**: rust-lang.org mostra "Version 1.100.1", e o blog lista "Announcing Rust 1.100.1" em 2026-11-27. A constituição 1.1.0 pede a versão estável vigente, confirmada na documentação oficial. O `rustup` é o instalador oficial, instala sem senha de administrador (em `~/.rustup` e `~/.cargo`) e já está na 1.100.1; o Homebrew ainda está na 1.100.0.
- **Alternatives considered**: `brew install rust` (1.100.0, uma versão de correção atrás, e sem o `rustup` para trocar de versão).
- **Situação do ambiente**: a máquina não tem Rust. A instalação é a primeira tarefa e pede confirmação do usuário, como foi com o JDK e o Go.

## R2. Servidor HTTP: axum sobre tokio

- **Decision**: **axum 0.8.9** sobre **tokio 1.54.1**, com o runtime de várias threads.
- **Rationale**: a biblioteca padrão do Rust não tem servidor HTTP nem runtime assíncrono, então um framework é inevitável. O axum é o caminho mais comum do ecossistema, mantido pelo projeto tokio, e é o equivalente ao FastAPI, ao Spring e ao `net/http` nas outras implementações. As rotas com extração tipada (`Path`, `State`) deixam os handlers curtos.
- **Alternatives considered**:
  - actix-web: popular, mas com runtime próprio e menos alinhado ao resto do ecossistema tokio;
  - hyper puro: mais controle, mas foge do caminho comum;
  - Rocket: menos usado hoje.

## R3. Camada de topo e as lições das convergências

A documentação do axum confirma um comportamento fora do contrato: "Create a default `MethodRouter` that will respond with `405 Method Not Allowed` to all requests". É o mesmo do `ServeMux` do Go. O resto da pilha (o `hyper` e o `http::Uri`) **será conferido por teste** no esqueleto, antes de qualquer decisão: caminho com escape inválido (`%ZZ`), `OPTIONS *`, barras repetidas, `.` e `..`, `;` e `TRACE`.

- **Decision**: uma camada de topo (`axum::middleware::from_fn`, em `topo.rs`) que envolve o roteador inteiro, inclusive os *fallbacks*:
  1. aplica a correlação e escreve o `X-Correlation-Id` em toda resposta;
  2. recusa com 404 `nao-encontrado` o caminho cru com `;`, barras repetidas, segmentos `.` ou `..`, e o alvo que não começa com `/` (como o `*` do `OPTIONS *`). Isso cobre a T050 do E4 e a T044 do E7;
  3. converte um `panic` em 500 `erro-interno`, sem rastro (`tower-http` não entra; um `catch_unwind` sobre o futuro basta);
- o roteador tem `fallback` e `method_not_allowed_fallback` apontando para o mesmo 404 `nao-encontrado` do contrato (lição da T047 do E4). Nada é ecoado;
- **caminho mal codificado (T044 do E4):** o que o `hyper` fizer com `%ZZ` é conferido por teste. Se ele recusar antes da aplicação, como o `net/http`, a decisão do E7 (sanear a linha do pedido) é reavaliada. Se ele deixar passar, o handler decodifica o segmento e recusa com 400 `entrada-invalida`.
- **HEAD:** fica como no E4 e no E7, divergência já registrada.
- **Rationale**: no E7, as mesmas lições ficaram num handler de topo e nenhuma virou convergência. Aqui elas ficam numa camada única, e a suíte (que já tem os cenários) confere.

## R4. Parâmetros da *query*

- **Decision**: a *query* é lida do texto cru (`Uri::query()`), sem o extrator `Query` do axum, que usa `serde_urlencoded` e decodifica de forma tolerante:
  - um `%` que não inicia um escape de dois dígitos hexadecimais, ou um valor que decodifica para UTF-8 inválido (`percent_decode_str(...).decode_utf8()`), dá 400 `entrada-invalida` (lição da T046 do E4);
  - `+` vira espaço, como em `application/x-www-form-urlencoded`;
  - parâmetro repetido vale pelo **último** valor (T045);
  - `pagina` só com dígitos que estoura `i64` conta como além do fim (T045).
- **Rationale**: o mesmo desenho do E7, com o `percent-encoding` 2.3.2, que faz parte do projeto `url`.

## R5. Formato da resposta e cabeçalho `Accept`

- **Decision**: os handlers escrevem sempre `application/json` no sucesso e `application/problem+json` no erro, e o `Accept` é ignorado. O axum não negocia conteúdo, então a lição da T048 sai de graça; um teste fixa isso mesmo assim.
- **JSON:** `serde_json` não escapa `<`, `>` e `&`, escreve os campos na ordem da *struct* e não acrescenta quebra de linha. O `paginacao` some quando não se aplica (`#[serde(skip_serializing_if = "Option::is_none")]`).

## R6. Cliente do IBGE e prazo total

- **Decision**:
  - **Cliente:** `reqwest` 0.13.5, com `redirect::Policy::none()`, sem nova tentativa e com o `User-Agent` do laboratório;
  - **Prazo total:** `tokio::time::timeout(prazo, ...)` em volta do pedido **e** da leitura do corpo, o mesmo efeito do `asyncio.timeout` do E1;
  - **Leitura do JSON:** para `serde_json::Value`, com a mesma normalização manual das outras (códigos com a quantidade exata de dígitos, siglas `^[A-Z]{2}$` e `^[A-Z]{1,2}$`, objeto ou lista de 1 item, `[]` como "não encontrado");
  - **Classificação, a mesma do R6 do E1:** prazo esgotado → `FonteLenta`; erro de conexão → `FonteIndisponivel`; 5xx e 429 → `FonteIndisponivel`; outro status diferente de 200, JSON inválido ou fora da forma → `RespostaInesperadaDaFonte`.

## R7. Cópia guardada e consulta compartilhada

- **Decision**:
  - **Cópia guardada:** `HashMap<String, Guardada>` atrás de um `std::sync::Mutex`, nunca segurado durante um `await`;
  - **Consulta compartilhada:** um `HashMap<String, Shared<BoxFuture<Result<Entrada, ErroDominio>>>>` com as consultas em andamento. A consulta roda num `tokio::spawn`, que não morre com o pedido que a iniciou (o `shield` do E1, o `WithoutCancel` do E7), e o `Shared` entrega o mesmo resultado, **inclusive o erro**, a todos os pedidos que esperam;
  - **Prazo de cada pedido:** cada pedido espera a consulta e pode desistir sem cancelá-la;
  - **Falha com cópia vencida:** cada pedido devolve a cópia marcada como desatualizada;
  - **Relógio:** injetável (uma função de instante de parede e outra monotônica).
- **Rationale**: em Rust, um futuro abandonado é cancelado. O `tokio::spawn` desacopla a consulta do pedido de forma explícita.
- **Alternatives considered**: crates de *singleflight* da comunidade (pouco usadas); `moka` (cache completo, mas sem a cópia vencida em caso de falha sem adaptação).

## R8. Erros

- **Decision**: um `struct ErroDominio { tipo, titulo, status, detalhe }` que implementa `IntoResponse` (problem+json com `type`, `title`, `status`, `detail` e `correlacao_id`). Os handlers devolvem `Result<Json<Resposta>, ErroDominio>`, e o operador `?` propaga o erro. A correlação chega à resposta pela camada de topo, que completa o corpo do problema.
- **Rationale**: o erro como valor tipado, com `?`, é o caminho da linguagem. É um dos pontos da comparação (FR-007).

## R9. Dobra, ordenação e paridade

- **Decision**: NFKD com `unicode-normalization`, remoção das marcas combinantes (`is_combining_mark`) e *casefold* com `caseless::default_case_fold_str`. Ordenação por (nome dobrado, código). A paridade é conferida pelo cenário da suíte com os 645 municípios de SP (FR-004, SC-005).
- **Ponto de atenção**: o `is_combining_mark` usa a classe de combinação canônica, e o E1 usa a categoria `Mn`. As duas coincidem para os nomes brasileiros, e o cenário de paridade confirma.

## R10. Métricas com os nomes do contrato

- **Decision**: `prometheus` 0.14.0, num `Registry` próprio, com `IntCounterVec` para os três contadores e `HistogramVec` com as faixas do E1. O `/metrics` usa o `TextEncoder`, que escreve o formato texto do Prometheus (`text/plain; version=0.0.4`), e ignora o `Accept`.
- **Rationale**: o contrato pede o formato texto do Prometheus e o `Content-Type` `text/plain`. O `prometheus-client` 0.26.0, do próprio projeto Prometheus, escreve OpenMetrics (outro tipo de conteúdo e um `# EOF` no fim), o que exigiria contornar o formato. O `prometheus` 0.14.0 teve a última versão em 2025-03; fica registrado como risco de manutenção.

## R11. Configuração `LOCALIDADES_*`

- **Decision**: leitura com `std::env::var` e `str::parse`, com os padrões do E1 e as regras do E4 e do E7. O `parse::<f64>()` do Rust aceita `inf`, `infinity` e `NaN`, que são recusados com `is_finite()` (a lição da T049, de novo). Prazo e validade ficam entre 0,001 e 10⁹ s. Valor inválido impede a partida com a mensagem do E1 (`configuração inválida: LOCALIDADES_X precisa …, recebi '…'`) e código de saída 2.

## R12. Correlação e registro

- **Decision**:
  - **Correlação:** na camada de topo, com a regra do R12 do E1 (1 a 64 caracteres em `[A-Za-z0-9._-]`, senão UUID v4 do `uuid`), guardada numa extensão do pedido;
  - **Registro:** uma linha JSON por pedido, escrita com `serde_json` direto no `stdout`, com os campos do E1 na mesma ordem. O `tracing-subscriber` em JSON usaria nomes de campo próprios (`timestamp`, `fields`...), então não entra;
  - **Status, uso da cópia e tempo da fonte:** um estado do pedido numa extensão, preenchido pelo serviço e pelo cliente.

## R13. Testes

- **Decision**:
  - **Ferramentas:** `cargo test`, `#[tokio::test]` e `assert_eq!`;
  - **IBGE simulado:** um servidor axum em `127.0.0.1:0`, dentro do teste, servindo as fixtures e contando os pedidos;
  - **Testes de API:** o roteador inteiro chamado com `tower::ServiceExt::oneshot`, sem rede, e, nos casos que dependem do pedido cru, um servidor de verdade com o pedido escrito à mão num `TcpStream`, como no E4 e no E7;
  - **SC-004 (sem rede):** `cargo test --offline` dentro do sandbox, depois de popular o registro local de crates.

## R14. Caixa-preta e paridade

- **Decision**: o binário otimizado (`target/release/localidades`) é verificado com `verificar.sh`. O contrato não muda. Se o E8 revelar um caso novo, o cenário entra na suíte e precisa passar nas outras três (FR-002).

## R15. Comparação entre quatro (FR-006, FR-007 e FR-009)

- **Decision**:
  - o `medir.py` do E7 ganha a quarta implementação: build `cargo build --release`, suíte `cargo test`, artefato = binário otimizado, linhas `.rs` (com `tests/` e os blocos `#[cfg(test)]` contados como testes) e dependências diretas lidas do `[dependencies]` e do `[dev-dependencies]` do `Cargo.toml`;
  - o tempo de build é medido com o cache do `target/` frio e quente, porque a compilação otimizada de um *crate* com dependências pode levar muito mais que nas outras linguagens (caso de borda da spec);
  - a nota qualitativa vai num `ergonomia.md` escrito durante a implementação;
  - o `RESULTS.md` tem a tabela das 8 lições (FR-009, SC-006).

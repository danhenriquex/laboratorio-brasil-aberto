# Resultados: E8 — Serviço de localidades (IBGE), em Rust

- **Pergunta que o experimento respondia:** como é construir e operar o mesmo serviço de localidades em Rust, do setup aos testes e ao cumprimento do mesmo contrato, comparado ao E1 (Python), ao E4 (Java) e ao E7 (Go)?
- **Timebox previsto / usado:** 2 a 3 sessões curtas / 1 sessão (2026-11-28), em 9 PRs: spec e plano (#94), fundação (#95), US1 a US6 (#96 a #101) e este fechamento.
- **Linguagem e ferramentas:** Rust 1.100.1 (edition 2024), instalado pelo `rustup`; axum 0.8.9 sobre tokio 1.54.1; reqwest 0.13.5 (TLS com `rustls`); serde e serde_json; prometheus 0.14.0 (sem a feature `protobuf`); unicode-normalization e caseless; futures (`Shared`); percent-encoding, time e uuid. Nos testes, só o `tower` (`oneshot`), além do próprio `cargo test`.
- **Data de conclusão:** 2026-11-28

## Resposta curta
**O mesmo serviço em Rust cumpriu o mesmo contrato sem mudar uma linha dele.** Passou nos 82 cenários de caixa-preta, os mesmos do E1, do E4 e do E7, e devolveu, contra o IBGE real, respostas idênticas às das outras três implementações.

- **Onde o Rust se destacou:** no custo de operar, empatado com o Go. Partida em 0,02 s, 11 MB de memória e um binário de 8,9 MB, sem runtime à parte (E7: 0,03 s, 15 MB e 14,9 MB). E nas garantias de compilação: na consulta compartilhada, os erros de concorrência viraram erros de compilação, e não testes intermitentes.
- **Onde cobrou:** no tempo de compilação. Do clone à primeira resposta foram **17,3 s**, porque o `target/` começa vazio e as 174 crates são compiladas do zero (E1: 1,2 s; E7: 1,3 s; E4: 3,0 s). Depois de mudar um arquivo, a suíte leva 5,2 s, perto dos 6,5 s do E4 e longe do 1,1 s do E7. O código ficou do tamanho do E7 (1.753 linhas de produção), porque a leitura da *query*, da configuração e do JSON do IBGE também é escrita à mão.
- **Contrato:** das quatro pilhas HTTP, a do Rust foi a que menos decidiu antes da aplicação. Nenhuma das 8 lições anteriores exigiu mexer na conexão, como o E7 precisou.
- **Latência:** igual à do E7 (0,12 ms com a cópia guardada). As quatro ficam bem abaixo de 1 ms, e num pedido real ao IBGE a rede domina. Num serviço que só repassa dados, a linguagem continua não sendo o gargalo.

## O que foi feito
Serviço em `experiments/rust/localidades/`, com as mesmas rotas, regras e configuração `LOCALIDADES_*` das outras três, nos mesmos módulos (`dominio`, `fonte`, `cache`, `servico`, `api`, `operacao`), mais `topo`, a camada que põe a correlação, o formato e o 499 em todo pedido. O trabalho seguiu as histórias US1 a US5 do E1 e a US6 de comparação, agora entre quatro implementações. As lições das convergências do E4 e do E7 entraram como tarefas desde o início (FR-009), e o diário de ergonomia ([ergonomia.md](ergonomia.md)) foi escrito durante cada fase.

## Fontes e documentação oficial
As mesmas do E1: a API de localidades do IBGE e a [ficha da fonte](../../discovery/fichas/ibge-localidades.md). Versões conferidas em 2026-11-28 em rust-lang.org, blog.rust-lang.org/releases e na API do crates.io. O comportamento do hyper e do axum diante de entrada mal formada foi conferido na prática, com pedidos crus contra o esqueleto (T004, registrado no [diário](ergonomia.md#cumprir-o-contrato-escrito-à-mão)).

## Como executar localmente
A partir da raiz do repositório, com o Rust 1.100 instalado pelo `rustup`:

```bash
(cd experiments/rust/localidades && cargo clippy --all-targets -- -D warnings && cargo test)   # 74 testes
(cd experiments/rust/localidades && cargo build --release)
contracts/localidades/verificacao/verificar.sh "experiments/rust/localidades/target/release/localidades"   # 82 cenários
specs/005-localidades-rust/medicao/medir.sh                                                     # comparação E1 × E4 × E7 × E8
```

## Exemplos de requisição e resposta
Execução real contra o IBGE em **2026-11-28 17:39 UTC**, com o E1, o E4, o E7 e o E8 lado a lado recebendo os mesmos pedidos. O corpo foi comparado ignorando só o `coletado_em`, a correlação e o `instance` que o Spring acrescenta:

```text
/v1/ufs                                  E1 200 173 ms | E4 200 507 ms | E7 200 147 ms | E8 200 195 ms | corpo igual
/v1/ufs/RJ                               E1 200   7 ms | E4 200  13 ms | E7 200   1 ms | E8 200   0 ms | corpo igual
/v1/ufs/rj/municipios?nome=niteroi       E1 200 107 ms | E4 200 134 ms | E7 200 119 ms | E8 200 164 ms | corpo igual
/v1/municipios/3304557                   E1 200 258 ms | E4 200 205 ms | E7 200 207 ms | E8 200  93 ms | corpo igual
/v1/municipios/9999999                   E1 404 112 ms | E4 404 124 ms | E7 404 105 ms | E8 404 507 ms | corpo igual
/v1/ufs/MG/municipios?itens=500&pagina=2 E1 200 117 ms | E4 200 155 ms | E7 200 110 ms | E8 200 145 ms | corpo igual
/v1/municipios/12ab                      E1 400   4 ms | E4 400   8 ms | E7 400   1 ms | E8 400   1 ms | corpo igual
/v1/ufs (repetido, cópia guardada)       E1 200   3 ms | E4 200   4 ms | E7 200   1 ms | E8 200   0 ms | corpo igual
```

As latências da primeira consulta são, sobretudo, as do IBGE em cada momento: os pedidos foram feitos em sequência, e os 507 ms do E4 em `/v1/ufs` e do E8 em `/v1/municipios/9999999` não se repetiram nas outras rotas.

## Comparação medida (US6)
Na mesma máquina e no mesmo dia, com mediana de 3 execuções e contra o IBGE falso, sem rede. Detalhes e método em [medicao/resultado-2026-11-28.md](medicao/resultado-2026-11-28.md):

| Medida | E1 (Python) | E4 (Java) | E7 (Go) | E8 (Rust) |
|---|---|---|---|---|
| Do clone local à primeira resposta (`/v1/ufs`) | 1.2 s | 3.0 s | 1.3 s | 17.3 s |
| Build (dentro do clone) | 0.2 s | 1.7 s | 0.8 s | 16.9 s |
| Suíte de testes da implementação | 0.9 s | 6.1 s | 1.0 s | 0.7 s |
| _Contexto:_ build depois de mudar um arquivo de produção | 0.0 s | 1.5 s | 0.1 s | 1.9 s |
| _Contexto:_ suíte depois de mudar um arquivo de produção | 0.9 s | 6.5 s | 1.1 s | 5.2 s |
| Partida até o `/health` responder | 0.15 s | 0.98 s | 0.03 s | 0.02 s |
| Memória (RSS) depois de 10 pedidos | 55 MB | 252 MB | 15 MB | 11 MB |
| Tamanho do artefato | 80.9 MB | 26.3 MB | 14.9 MB | 8.9 MB |
| Linhas de código (produção / testes, sem linhas em branco) | 799 / 817 | 1279 / 1513 | 1766 / 2038 | 1753 / 2406 |
| Dependências diretas (runtime + teste) | 4 + 2 | 4 + 3 | 3 + 0 | 12 + 1 |
| Latência mediana com a cópia guardada (20 pedidos) | 0.38 ms | 0.76 ms | 0.12 ms | 0.12 ms |
| _Contexto:_ a mesma latência depois de 500 pedidos de aquecimento | 0.36 ms | 0.37 ms | 0.08 ms | 0.09 ms |

O build do clone do E8 é o caso do `target/` vazio: o cache de build do Go é global, e o do Rust fica dentro do projeto. As duas linhas de contexto mostram o build e a suíte com o cache quente.

A avaliação qualitativa (notas de 1 a 5 em setup, testes, contrato, erros e métricas) está no [diário de ergonomia](ergonomia.md#avaliação-fr-007): E8 com 4, 3, 4, 4 e 4.

## As 8 lições anteriores em Rust (FR-009, SC-006)
Para cada lacuna achada nas convergências do E4 e do E7, se o mesmo comportamento apareceu em Rust e como foi tratado:

| Lição | Apareceu em Rust? | Como foi tratada |
|---|---|---|
| T044 do E4 — caminho mal codificado fora do formato | Quase não: o hyper deixa o pedido chegar, e só o extrator `Path` recusaria o segmento com a sua própria resposta | A rejeição do `Path` vira o texto literal do segmento, que a validação recusa com 400 `entrada-invalida`. Sem saneamento da linha do pedido, ao contrário do E7 |
| T045 do E4 — `pagina` grande demais e parâmetro repetido | Em parte: `pagina=99999999999` cabe em `i64`, mas 30 dígitos estouram; o extrator `Query` não foi usado | Só dígitos que estouram `i64` valem como além do fim; a leitura da *query* crua usa o último valor repetido |
| T046 do E4 — *query* mal codificada virando 500 | Não viraria 500: o extrator `Query` decodificaria de forma tolerante, e a *query* chega crua ao handler | A leitura do texto cru recusa `%` sem dois dígitos hexadecimais e UTF-8 inválido com 400 `entrada-invalida` |
| T047 do E4 — `TRACE` fora do formato e ecoando o pedido | Em parte: o axum responde 405 com `Allow` e sem corpo, sem eco | `method_not_allowed_fallback` → 404 `nao-encontrado`; teste com pedido cru confere que nada é ecoado |
| T048 do E4 — `Accept` mudando o formato da resposta | Não: o axum não negocia conteúdo, e o `TextEncoder` das métricas também não | Os handlers escrevem o `Content-Type`; testes fixam isso para `/health`, para os erros e para o `/metrics` |
| T049 do E4 — configuração infinita ou arredondada para zero | Sim: o `parse::<f64>()` aceita `inf`, `infinity` e `NaN` | Recusa explícita com `is_finite()`, mais os limites de 0,001 e 10⁹ s, com a mensagem do E1 |
| T050 do E4 — parâmetros de caminho (`;`) ignorados | Não: o `;` é texto, e o roteador não normaliza `//`, `.` nem `..` | Nada a fazer além do `fallback`: o caminho não casa rota nenhuma e cai no 404 do contrato |
| T044 do E7 — `OPTIONS *` respondido pelo próprio servidor | Não: o hyper entrega o `OPTIONS *` ao roteador | O `fallback` dá o 404 do contrato, com correlação; teste com pedido cru |

**Leitura:** das 8 lacunas, 4 não apareceram em Rust (T048 e T050 do E4, T044 do E7, e a T046, que não viraria 500), 3 apareceram de outra forma ou em parte (T044, T045 e T047 do E4) e só uma apareceu de fato (T049, a terceira linguagem seguida). Como já eram tarefas desde o início, nenhuma virou convergência. A comparação com o E7 confirma a leitura de lá: os desvios de contrato vêm da pilha HTTP de cada ecossistema, e a do Rust é a que menos decide antes da aplicação.

## Critérios de sucesso
- **SC-001, contrato sem mudança:** os 82 cenários passaram contra o E8, os mesmos das outras três.
- **SC-002, critérios do E1:** valem para o E8, medidos pela mesma suíte (cópia em menos de 0,5 s, falha sem cópia dentro do prazo, consulta única com pedidos simultâneos).
- **SC-003, tabela comparativa:** as 9 medidas preenchidas para as quatro implementações, com data e método.
- **SC-004, testes sem rede:** em 2026-11-28, dentro do sandbox sem rede externa, passaram os 74 testes do E8 (`cargo test --offline`) e os 82 cenários, e um `curl` ao IBGE falhou no mesmo sandbox (`Could not resolve host`).
- **SC-005, paridade de ordenação:** a ordem dos 645 municípios de SP e as buscas da suíte deram o mesmo resultado nas quatro.
- **SC-006, lições anteriores:** as 8 têm registro (tabela acima).

## O que funcionou
- **Uma pilha que não decide antes da aplicação:** o hyper entrega ao roteador tudo o que o contrato precisa tratar. Os *fallbacks* do axum e uma camada de topo bastaram, sem embrulhar a conexão.
- **O compilador como revisor de concorrência:** o `Shared` exige resultado `Clone`, `Send` e `Sync`, e cada descuido virou erro de compilação, inclusive nos testes.
- **`serde`:** o JSON do contrato e a linha de registro saíram de *structs* com `#[derive(Serialize)]`, na ordem da declaração e sem as armadilhas de escape do Go.
- **Lições como tarefas:** de novo, levar as convergências anteriores para o plano evitou convergências do mesmo tipo.
- **Paridade de ordenação:** NFKD com `caseless` deu a mesma ordem do Python sem ajuste.

## O que falhou ou surpreendeu
- **Tempo de compilação:** 17,3 s do clone à primeira resposta, e 5,2 s para rodar os testes depois de mudar um arquivo. É o ponto que mais pesa no dia a dia.
- **Cancelamento por descarte:** um futuro abandonado é cancelado, então a consulta compartilhada precisou de um `tokio::spawn`, e o registro do cliente que desiste precisou de uma guarda com `Drop`. São padrões que as outras linguagens não exigiram.
- **O `task_local` não atravessa o `spawn`:** o estado do pedido precisou ser levado à mão para a tarefa da consulta ao IBGE.
- **Dependências:** 12 diretas e 174 crates ao todo, porque a biblioteca padrão não traz servidor HTTP, runtime assíncrono, JSON, cliente HTTP nem UUID.
- **Manutenção do `prometheus`:** a última versão do crate é de 2025-03, e o crate oficial do projeto Prometheus escreve OpenMetrics, fora do contrato. Fica como risco.
- **Ordem do TDD na US4:** a busca entrou junto com a US1, e os testes dela vieram depois do código. Uma mutação temporária confirmou que os testes pegam a falta da busca.

## Limitações
- **Ordem de construção:** o E8 foi o último, com as decisões e as lições das outras três conhecidas. Isso o favorece em acertar o desenho e não diz nada sobre a linguagem. Explica, em parte, o timebox: uma sessão, contra duas do E7.
- **Mesmo autor:** as quatro implementações têm o mesmo autor (o assistente). Uma equipe com mais experiência num dos ecossistemas daria outras notas.
- **Medição:** feita numa única máquina (macOS, arm64), com os caches de dependências quentes. A medida "do clone à primeira resposta" não inclui baixar as dependências pela primeira vez; no E8, inclui compilar todas elas.
- **Linhas de código:** a contagem do E8 trata os blocos `#[cfg(test)]` de `src/` e os arquivos de `tests/` como testes, e o `rustfmt` quebra as asserções longas em várias linhas.
- **Divergências que continuam fora da spec:** `HEAD` (aceito pelo E4, pelo E7 e pelo E8, recusado pelo E1) e barra no fim do caminho (o E1 redireciona; o E4, o E7 e o E8 dão 404), conferidas no E8 em 2026-11-28.

## Checklist de conclusão
- [x] A fonte foi identificada e documentada (a mesma do E1)
- [x] As condições de acesso foram verificadas (execução real em 2026-11-28)
- [x] O dado foi consumido ou baixado (fixtures do E1 e execução real)
- [x] A estrutura dos dados foi inspecionada (corpos idênticos aos das outras três)
- [x] Os casos de erro foram testados (os 82 cenários e os 74 testes)
- [x] O resultado pode ser reproduzido (comandos acima e `medir.sh`)
- [x] As limitações estão registradas
- [x] A utilidade do experimento foi avaliada (abaixo)

## Decisões e próximos passos
- **Utilidade:** alta, para o método. A régua do E1 (contrato escrito à mão, suíte de caixa-preta e medição) funcionou numa quarta linguagem sem mudança. Com quatro pilhas HTTP, a tabela das lições mostra o padrão com clareza: o contrato quebra na entrada mal formada, e cada pilha quebra num lugar diferente.
- **ADR:** a [ADR 0001](../../docs/adr/0001-convencoes-comuns-de-api.md) ganhou a seção "Confirmação no E8", com uma regra nova: toda leitura de número de configuração precisa recusar valores não finitos. A [ADR 0002](../../docs/adr/0002-go-e-rust-como-linguagens.md) previu este experimento.
- **Qual implementação "se gradua" para `services/`:** continua em aberto, por decisão do usuário. Com as quatro medidas:
  - se o critério for o custo de operar, o E7 e o E8 empatam, e o E7 compila muito mais rápido;
  - se for o custo de construir e manter, o E1 (menos código e o ciclo mais curto).
- **Próximos experimentos:** os **E2 e E3** do roteiro, que deixam o serviço de localidades e voltam para fontes novas.
- **Ideias que ficaram de fora:**
  - um `target/` compartilhado (`CARGO_TARGET_DIR`) ou `sccache`, para medir o build do clone com o cache quente, como o do Go;
  - juntar os 7 arquivos de `tests/` num único binário de teste, para medir quanto do ciclo de 5,2 s é ligação;
  - um cenário na suíte para `HEAD`, se a spec decidir o comportamento.

# Diário de ergonomia: E8 (Rust), comparado ao E1 (Python), ao E4 (Java) e ao E7 (Go)

Escrito durante a implementação, e não de memória no fim (FR-007; research R15). As notas de 1 a 5 entram na consolidação da US6 (T038).

## Setup

- **2026-11-28, instalação:** o usuário instalou o Rust pelo `rustup` no próprio terminal, antes da T001: `rustc 1.100.1 (20ddd0171 2026-11-25)` e `cargo 1.100.1`, a versão listada em rust-lang.org. Sem senha de administrador, como no Go.
- **2026-11-28, crate e dependências:** `cargo new` e `cargo add` das dependências do research levaram 12 s, incluindo o download do índice. O `Cargo.lock` é o *lockfile*. O `reqwest` 0.13 já vem com TLS em Rust puro (`rustls` com `aws-lc-rs`) por padrão, sem depender do OpenSSL do sistema.
- **2026-11-28, primeiro build otimizado:** `cargo build --release` do esqueleto levou **34 s com o cache frio** (25 s de compilação e o resto de download), e menos de 1 s quando só o crate muda. As 12 dependências diretas puxam **179 crates** ao todo. O binário do esqueleto tem 2,6 MB.
- **Aviso de dependência sem uso:** o cargo 1.100 avisa no build quando uma dependência declarada ainda não é usada (`warning: unused dependency`), o equivalente ao que o `go mod tidy` fazia no E7, mas sem remover nada.

## Testes

- **2026-11-28, fundação:** `cargo test` com `#[tokio::test]` e `assert_eq!`. O IBGE simulado é um servidor axum em `127.0.0.1:0` dentro do próprio teste, sem biblioteca de *mock*. Os testes de API chamam o roteador com `tower::ServiceExt::oneshot`, sem rede, e os pedidos crus vão a um servidor de verdade por `TcpStream`, como no E4 e no E7. Os testes de unidade ficam no próprio módulo (`#[cfg(test)]`), e os de integração em `tests/`.
- **Velocidade (medida na US6):** com tudo compilado, a suíte de 74 testes roda em **0,7 s** (E1: 0,9 s; E7: 1,0 s; E4: 6,1 s). Depois de mudar um arquivo de produção, sobe para **5,2 s** (E1: 0,9 s; E7: 1,1 s; E4: 6,5 s), porque o crate e os 7 binários de teste de integração (um por arquivo de `tests/`) são recompilados e ligados de novo. É o ponto em que o Rust mais pesa no ciclo: cada mudança passa pelo compilador antes de qualquer teste rodar.
- **`clippy`:** com `-D warnings`, ele pegou dois pontos nos testes, e uma das sugestões (`cmp_owned`) mudaria a semântica, comparando um número JSON com um texto. Foi preciso reescrever em vez de aceitar a sugestão.

## Cumprir o contrato escrito à mão

- **2026-11-28, sondagem da pilha HTTP (T004):** com o esqueleto (só `GET /health`), pedidos crus mostraram que, ao contrário do Go, quase nada é decidido antes da aplicação:

  | Pedido | Resposta do esqueleto | Comparação |
  |---|---|---|
  | `GET /v1/municipios/%ZZ` | 404 vazio, do roteador | o `hyper` deixa passar; no E7, o `net/http` recusava antes do handler |
  | `GET //health`, `/./health`, `/x/../health` | 404 vazio | sem limpeza nem redirecionamento; no E7, o `ServeMux` redirecionava |
  | `GET /health;x` | 404 vazio | o `;` é texto; no E4, o Tomcat o descartava |
  | `POST /health`, `TRACE /health` | **405** com `Allow: GET,HEAD`, sem corpo | o mesmo 405 do E7, mas sem eco no `TRACE` |
  | `OPTIONS *` | 404 vazio, do roteador | chega à aplicação; no E7, o `http.Server` respondia sozinho |
  | `HEAD /health` | 200 | aceito, como no E4 e no E7 |
  | `GET /health` com `Accept: application/xml` | 200 em JSON | sem negociação |
  | `GET /health?x=%ZZ` | 200 | a *query* só é lida se o handler pedir |

- **2026-11-28, US1:** os 27 cenários da US1, da paridade de ordenação (os 645 municípios de SP) e de contrato passaram de primeira contra o binário. A paridade veio da dobra com `unicode-normalization` e `caseless`, sem ajuste, apesar da diferença entre a classe de combinação usada aqui e a categoria `Mn` do E1 (research R9).
- **Extratores e suas rejeições:** o axum lê os parâmetros por extratores tipados (`Path`, `Query`, `State`), o que deixa os handlers curtos. Mas cada extrator tem a sua resposta de erro pronta, fora do contrato: o `Path` recusaria `%ZZ` e o `Query` decodificaria de forma tolerante. A saída foi receber `Result<Path<String>, PathRejection>`, transformando a rejeição no texto literal do segmento, e ler a *query* do texto cru (`Uri::query()`), com a mesma regra do E7.
- **`serde_json`:** não escapa `<>&`, não põe quebra de linha no fim e escreve os campos na ordem da *struct*. As três armadilhas de JSON do Go não existem aqui.
- **2026-11-28, US2 e a lição da T044:** no Go, o `%ZZ` no caminho exigiu embrulhar o `net.Listener`, porque o `net/http` recusava o pedido antes de qualquer handler. Em Rust, o `hyper` entrega o pedido, e o único obstáculo é o extrator `Path`, que recusaria o segmento. Com a rejeição transformada no texto literal, `%ZZ`, `%` e `%E3` viram 400 `entrada-invalida` com correlação, como no E1. A barra codificada (`%2F`) decodifica para `/`, que também não é um código de 7 dígitos, e dá 400. A tarefa T020 previa 404, por analogia com o E7, mas o teste aceita 400 ou 404, como a suíte.
- **2026-11-28, configuração:** o `parse::<f64>()` do Rust aceita `inf`, `infinity` e `NaN` e transforma `1e400` em infinito sem erro. É a mesma lacuna da T049 do E4, a terceira linguagem seguida em que ela aparece. A recusa é explícita com `is_finite()`, e a mensagem sai igual à do E1.

  **Decisão (atualiza o R3):** não há `Ouvinte` como no E7. Basta o `fallback` e o `method_not_allowed_fallback` do roteador levarem ao 404 do contrato, e a camada de topo pôr a correlação e o formato. Fica um cuidado: o extrator `Path` do axum decodifica o segmento e, com `%ZZ`, recusaria o pedido com a sua própria resposta de erro. A rejeição dele precisa virar `entrada-invalida`.

- **2026-11-28, US4 e a ordem do TDD invertida:** o filtro `nome` entrou na US1, junto da listagem, porque a validação, a dobra e a ordem de aplicação (validar, filtrar, ordenar e paginar) são as mesmas do E1 e já estavam no domínio. Assim, os 6 testes de `tests/busca.rs` (T029) passaram de primeira, e a T030 não teve código novo. Para não aceitar um teste verde sem prova, uma mutação temporária desligou a validação e o filtro: 4 dos 6 falharam. Os outros 2 cobrem a decodificação da *query* e a cópia guardada, que ficam fora do filtro. Os 16 cenários da US4 e da paridade passaram contra o binário. A lição da T046 do E4 (`nome=%ZZ`, `nome=s%E3o` e `nome=%` crus → 400) já vinha coberta pela leitura da *query* do texto cru, feita na US1.

## Consulta compartilhada e concorrência

- **2026-11-28, US3:** a parte em que o modelo assíncrono do Rust mais pesou. Um futuro abandonado é cancelado (quando o cliente desiste, o hyper descarta o futuro do pedido), então a consulta ao IBGE não pode morar no futuro do pedido que a iniciou. A solução foi um `tokio::spawn` para a consulta e um `Shared` (do `futures`) sobre o resultado da tarefa, guardado num mapa de consultas em andamento. Quem chega durante a consulta clona o `Shared` e recebe o mesmo resultado, **inclusive o erro** (lição da T050 do E1).
  - **O `task_local` não atravessa o `spawn`:** o estado do pedido, onde o tempo da fonte é anotado, precisou ser levado de forma explícita para a tarefa da consulta (`ESTADO.scope(estado, tarefa)`). No Go, o `context` fazia isso de graça; no E1, o `ContextVar` também atravessa o `create_task`.
  - **O compilador ajudou:** o `Shared` exige que o resultado seja `Clone` e, para ir entre threads, `Send` e `Sync`. O tipo de erro e os dados (com `Arc`) precisaram satisfazer isso, e qualquer descuido virava erro de compilação, e não condição de corrida. O mesmo aconteceu no apoio de testes: um `get` que guardava uma referência à resposta através de um `await` não compilava ao rodar em outra tarefa.
  - **Comparação:** no E1, foram 3 convergências até acertar; no E4, o `CompletableFuture` acertou de primeira; no E7, o `singleflight` resolveu numa chamada, verificado pelo `-race`. No E8, o desenho também veio pronto e os 8 cenários da US3 passaram de primeira, mas com mais peças à mão (mapa de consultas, `spawn`, `Shared` e o `scope` do estado). Em compensação, a ausência de corrida é garantida pelo compilador, e não por um teste.
- **Cliente que desiste:** em Rust, o futuro do pedido é descartado inteiro, inclusive a camada de topo. Não há resposta nem linha de registro para esse pedido, o que é diferente do E7, que registrava 499. Fica anotado para a US5.

## Tratamento de erros

- **2026-11-28, fundação:** o `ErroDominio` implementa `IntoResponse`, e os handlers devolvem `Result<_, ErroDominio>` com o operador `?`. É tão explícito quanto o erro como valor do Go, mas sem o `if err != nil` a cada chamada. A leitura do JSON do IBGE campo a campo saiu curta com um tipo de erro local (`Forma`) e `?`.
- **Correlação no corpo do erro:** como o `IntoResponse` não recebe o pedido, a correlação chega por um `task_local` do tokio, posto pela camada de topo. Funciona, mas a consulta ao IBGE roda noutra tarefa (US3), e lá o `task_local` não existe: será preciso levá-lo junto de forma explícita.
- **Panic:** um `catch_unwind` sobre o futuro do pedido, na camada de topo, transforma o `panic` em 500 sem rastro. Sem ele, o hyper derrubaria só a conexão.

## Métricas e registro

- **2026-11-28, US5:** o `prometheus` 0.14.0 num `Registry` próprio, com `IntCounterVec` e `HistogramVec`, saiu como no E7: os nomes não ganham sufixo de unidade e as faixas são as do E1. O `TextEncoder` só escreve o formato texto e não olha o `Accept`, então não foi preciso retirar o cabeçalho, como o `promhttp` exigia no E7. O serviço não usa o protobuf, que é a feature padrão do crate, então ela saiu (`default-features = false`), e a árvore caiu de 180 para 174 crates. Ficam de fora os coletores de processo: no crate, eles dependem do `procfs` e só funcionam no Linux. No E4, a JVM expõe os seus; no E7, o Go expõe os do *runtime*.
- **Registro:** uma *struct* com `#[derive(Serialize)]` e os campos do E1 na ordem da declaração, escrita com `serde_json` numa única escrita por linha, sob um `Mutex`. Foram poucas dezenas de linhas, sem biblioteca de registro. No E7, o `slog` precisou de um `ReplaceAttr` para renomear e remover campos.
- **Cliente que desiste (pendência da US3):** quando o cliente desiste, o hyper descarta o futuro do pedido, inclusive a camada de topo, e nenhuma linha depois do `await` roda. A saída foi uma guarda com `Drop`: se a resposta não saiu, o pedido é observado com 499 (a convenção do nginx), sem contar como erro do serviço. O resultado é o mesmo do E7, mas o mecanismo é o oposto: lá o `context` cancelado chega ao handler, e aqui é o destrutor que avisa que o futuro morreu. Um teste com `tokio::time::timeout` em volta do pedido fixa o comportamento.
- **Suíte inteira:** **82 de 82** cenários contra o binário otimizado, sem rede (SC-001). As 103 linhas que o binário escreveu durante a suíte são JSON válido, e os 502 e 504 saem com `nivel` `error`.

## Avaliação (FR-007)

Notas de 1 (difícil) a 5 (fácil) para a experiência de construir o mesmo serviço. As notas do E1, do E4 e do E7 são as do [diário do E7](../004-localidades-go/ergonomia.md). As medidas estão em [medicao/resultado-2026-11-28.md](medicao/resultado-2026-11-28.md), tiradas no mesmo dia e na mesma máquina para as quatro.

| Ponto | E1 (Python) | E4 (Java) | E7 (Go) | E8 (Rust) | Por quê (E8) |
|---|---|---|---|---|---|
| **Setup** | 5 | 3 | 5 | 4 | O `rustup` instala sem senha de administrador, e o `cargo` faz tudo (criar, adicionar dependência, compilar, testar, formatar e analisar), sem *wrapper* nem arquivo de build à parte; `cargo new` e as dependências levaram 12 s. Perde um ponto pelo build frio: do clone à primeira resposta, **17,3 s**, dos quais 16,9 s de compilação (E1: 1,2 s; E7: 1,3 s; E4: 3,0 s). O `target/` fica dentro do projeto, e cada clone compila as 174 crates do zero, enquanto o cache de build do Go é global. |
| **Escrita de testes** | 4 | 3 | 4 | 3 | O `cargo test` vem pronto, os testes de unidade ficam no próprio arquivo e o `#[tokio::test]` resolve os assíncronos. O compilador pegou nos testes erros que, em outra linguagem, seriam intermitentes (uma referência guardada através de um `await`). Perde dois pontos pelo ciclo depois de uma mudança, **5,2 s** contra 1,1 s do E7 e 0,9 s do E1, perto dos 6,5 s do E4, e pelas asserções escritas à mão, como no Go. É a maior suíte das quatro (2.406 linhas). |
| **Cumprir o contrato escrito à mão** | 4 | 4 | 3 | 4 | Das 8 lições anteriores, nenhuma exigiu mexer na conexão: as que pediram código (a rejeição do extrator `Path`, a leitura da *query* crua, o estouro de `pagina` e a recusa de `inf` na configuração) ficaram nos handlers e na configuração. O hyper entrega ao roteador `%ZZ`, `//`, `;` e `OPTIONS *` sem decidir nada antes, então não foi preciso embrulhar a conexão como no E7, e o `serde_json` não tem as armadilhas do JSON do Go. Perde um ponto porque cada extrator tem a sua resposta de erro pronta, fora do contrato, e porque a normalização do IBGE e a leitura da configuração são escritas à mão: 1.753 linhas de produção, quase as mesmas do E7 (1.766), contra 1.279 do E4 e 799 do E1. |
| **Tratamento de erros** | 3 | 4 | 4 | 4 | `Result` com o operador `?` deixa cada falha explícita sem o `if err != nil` do Go, e um único `IntoResponse` converte em problem+json. O compilador exige tratar cada `Result`, e o `catch_unwind` resolve o 500 sem rastro. Perde um ponto pela correlação no corpo do erro: o `IntoResponse` não recebe o pedido, então ela viaja num `task_local`, que precisou ser levado à mão para a tarefa da consulta ao IBGE. |
| **Métricas e registro** | 4 | 3 | 4 | 4 | O `prometheus` dá os nomes exatos, sem sufixo de unidade, e o `TextEncoder` não negocia formato, então não houve o que desligar, ao contrário do E7. O registro do E1 saiu de uma *struct* com `#[derive(Serialize)]`, sem biblioteca de registro. Perde um ponto pelo risco de manutenção do crate (última versão em 2025-03; o crate oficial do Prometheus escreve OpenMetrics), pela falta de coletores de processo fora do Linux e pela guarda com `Drop` que o 499 do cliente que desiste exigiu. |

**Cuidados de leitura (FR-008):**
- **Ordem de construção:** o E8 foi o último, com as lições das convergências do E1, do E4 e do E7 já viradas tarefas desde o início, e com o desenho da consulta compartilhada já conhecido. Isso o favorece em "acertar o desenho" e não diz nada sobre a linguagem.
- **Mesmo autor:** as quatro implementações foram escritas pelo mesmo assistente. Uma equipe com experiência maior num dos ecossistemas daria outras notas.
- **Build frio × quente:** os 16,9 s de build no clone são o caso do `target/` vazio, com o registro de crates já baixado. Com o cache quente, um build depois de mudar um arquivo leva 1,9 s (E4: 1,5 s; E7: 0,1 s; o E1 não compila). Quem trabalha sempre no mesmo diretório paga o build frio uma vez; quem clona para cada execução (uma integração contínua sem cache, por exemplo) paga sempre.
- **Números da execução:** a partida (0,02 s), a memória (11 MB) e o binário (8,9 MB) são os menores das quatro, mas ficam na mesma ordem de grandeza do E7 (0,03 s, 15 MB e 14,9 MB): os dois compilam para um binário nativo sem runtime à parte. A diferença de memória para o E7 é de 4 MB num serviço pequeno, e não deve ser extrapolada. A latência com a cópia guardada é igual à do E7 (0,12 ms; 0,09 ms aquecida contra 0,08 ms), e as quatro ficam bem abaixo de 1 ms em loopback. Num pedido real ao IBGE, a rede domina.
- **Dependências:** as 12 diretas do E8 são o maior número das quatro, porque a biblioteca padrão do Rust não tem servidor HTTP, runtime assíncrono, JSON, cliente HTTP nem UUID. Elas puxam 174 crates ao todo (sem o `protobuf` do `prometheus`, que saiu na US5). O E7 tem 3 diretas e 8 indiretas, porque a biblioteca padrão do Go já traz quase tudo.
- **Linhas de testes:** o E8 conta como teste os blocos `#[cfg(test)]` dentro de `src/` e os arquivos de `tests/`. Os casos espelham os do E7, com alguns a mais (o 499 do cliente que desiste e testes de unidade do cache). Parte da diferença de linhas vem da formatação do `rustfmt`, que quebra as tuplas das asserções em várias linhas.

## Lições anteriores

Uma linha por comportamento fora do contrato achado antes, preenchida à medida que cada um aparecer (FR-009). A tabela final vai para o `RESULTS.md`.

| Lição | Apareceu em Rust? | Como foi tratada |
|---|---|---|
| T044 do E4 — caminho mal codificado fora do formato | Quase não: o `hyper` deixa o pedido chegar, e só o extrator `Path` recusaria o segmento com a sua própria resposta | A rejeição do `Path` vira o texto literal do segmento, que a validação recusa com 400 `entrada-invalida`. Sem saneamento da linha do pedido, ao contrário do E7 |
| T045 do E4 — `pagina` grande demais e parâmetro repetido | Em parte: `pagina=99999999999` cabe em `i64`, mas 30 dígitos estouram; o extrator `Query` não foi usado | Só dígitos que estouram `i64` valem como além do fim; a leitura da *query* crua usa o último valor repetido |
| T046 do E4 — *query* mal codificada virando 500 | Não viraria 500: o extrator `Query` decodificaria de forma tolerante, e a *query* chega crua ao handler | A leitura do texto cru recusa `%` sem dois dígitos hexadecimais e UTF-8 inválido com 400 `entrada-invalida` |
| T047 do E4 — `TRACE` fora do formato e ecoando o pedido | Em parte: o axum responde 405 com `Allow` e sem corpo, sem eco | `method_not_allowed_fallback` → 404 `nao-encontrado`; teste com pedido cru confere que nada é ecoado |
| T048 do E4 — `Accept` mudando o formato da resposta | Não: o axum não negocia conteúdo | Os handlers escrevem o `Content-Type`; um teste fixa isso para `/health` e para os erros |
| T049 do E4 — configuração infinita ou arredondada para zero | Sim: o `parse::<f64>()` aceita `inf`, `infinity` e `NaN` | Recusa explícita com `is_finite()`, mais os limites de 0,001 e 10⁹ s, com a mensagem do E1 |
| T050 do E4 — parâmetros de caminho (`;`) ignorados | Não: o `;` é texto, e o roteador não normaliza `//`, `.` nem `..` | Nada a fazer além do `fallback`: o caminho não casa rota nenhuma e cai no 404 do contrato |
| T044 do E7 — `OPTIONS *` respondido pelo próprio servidor | Não: o hyper entrega o `OPTIONS *` ao roteador | O `fallback` dá o 404 do contrato, com correlação; teste com pedido cru |

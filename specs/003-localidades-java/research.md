# Research: E4 — Serviço de localidades (IBGE), em Java

**Data**: 2026-11-27 | **Spec**: [spec.md](spec.md) | **Plano**: [plan.md](plan.md)

As decisões de **comportamento** e de contrato são as do E1 ([specs/002-servico-localidades/research.md](../002-servico-localidades/research.md)), e estas não as repetem:

| Decisão do E1 | Assunto |
|---|---|
| R1 | comportamento real do IBGE |
| R4 | caixa-preta e IBGE falso |
| R5 | cópia guardada |
| R6 | prazo e classificação das falhas |
| R7 | códigos como texto |
| R8 | dobra e ordenação |
| R9 | paginação |
| R10 | envelope e `meta` |
| R11 | erros |
| R12 | observabilidade |
| R14 | configuração |

Abaixo está o "como" em Java. As versões foram conferidas em 2026-11-27 no Homebrew e no Maven Central.

## R1. JDK

- **Decision**: **JDK 25 (LTS)**, distribuição Eclipse Temurin 25.0.5, instalada com `brew install --cask temurin@25`. O projeto declara `<maven.compiler.release>25</maven.compiler.release>` e um `.java-version` com `25`.
- **Rationale**: a constituição pede "JDK de suporte longo, versão a confirmar no E4". O 25 é o LTS mais recente (o 27, de setembro de 2026, não é LTS) e traz threads virtuais maduras, *records* e *pattern matching*, que deixam o código mais próximo do Python em concisão.
- **Alternatives considered**:
  - JDK 21 (LTS anterior): funcionaria, mas sem motivo para começar um projeto novo numa versão mais velha;
  - JDK 27: não é LTS.
- **Situação do ambiente**: a máquina não tem JDK nem Maven. A instalação do JDK é a primeira tarefa e pede confirmação do usuário. O Maven não precisa ser instalado, porque vem pelo Maven Wrapper.

## R2. Framework

- **Decision**: **Spring Boot 4.1.3**, com Spring MVC rodando em **threads virtuais** (`spring.threads.virtual.enabled=true`).
- **Rationale**:
  - é o caminho mais comum no mercado Java, assim como o FastAPI no Python, e a pergunta do E4 é sobre a ergonomia desse caminho;
  - tem `ProblemDetail` nativo (RFC 9457);
  - integra o Micrometer;
  - com threads virtuais, o código bloqueante fica simples sem perder concorrência, o que evita a programação reativa (WebFlux).

  A linha 4.1 foi preferida à 4.2.0, publicada em 19/11/2026, por ser uma linha com mais patches. As duas saíram no mesmo dia (4.1.3 e 4.2.0).
- **Alternatives considered**:
  - Javalin ou JDK puro (`HttpServer`): menores, mas pouco representativos;
  - Quarkus ou Micronaut: bons em tempo de partida, mas um segundo ecossistema para avaliar;
  - WebFlux: o modelo reativo complicaria o código sem necessidade, já que as threads virtuais resolvem a concorrência.

## R3. Contrato primeiro

- **Decision**: nenhum gerador de OpenAPI (sem springdoc). As respostas são *records* escritos à mão, e o contrato continua sendo o `openapi.yaml` compartilhado, verificado de fora pela suíte.
- **Rationale**: é o mesmo princípio do E1 (R3 do E1). Gerar o contrato a partir do código criaria um segundo contrato.
- **Alternatives considered**: `openapi-generator` para gerar os DTOs a partir do contrato. Seria fiel ao contrato primeiro, mas acrescenta etapa de build e código gerado para cinco tipos simples. Fica registrado como ideia para comparar.

## R4. Cliente do IBGE e prazo total

- **Decision**:
  - **Cliente:** `java.net.http.HttpClient`, da JDK, com `connectTimeout` igual ao prazo e sem nova tentativa. Ele não refaz pedidos sozinho.
  - **Prazo total:** `sendAsync(pedido, ofByteArray()).orTimeout(prazo)`. O prazo cobre conexão, cabeçalhos e corpo, como o `asyncio.timeout` do E1.
  - **Leitura do JSON:** Jackson, para `JsonNode`, com normalização manual pelas mesmas regras do E1:
    - "não encontrado" é `[]`;
    - um objeto ou uma lista de 1 item é aceito;
    - `microrregiao` é opcional;
    - código com a quantidade **exata** de dígitos (T048);
    - siglas `^[A-Z]{2}$` e `^[A-Z]{1,2}$` (T049).
  - **Classificação, a mesma do R6 do E1:**

    | Exceção ou status | Erro |
    |---|---|
    | `TimeoutException` / `HttpTimeoutException` | `FonteLenta` |
    | `ConnectException`, outros `IOException` | `FonteIndisponivel` |
    | 5xx e 429 | `FonteIndisponivel` |
    | outro status diferente de 200, JSON inválido ou fora da forma | `RespostaInesperadaDaFonte` |

- **Rationale**: o cliente da JDK evita uma dependência (Constituição X), e o `orTimeout` dá o prazo total que o E0 ensinou a exigir.
- **Alternatives considered**:
  - `RestClient` do Spring: é mais "Spring", mas o prazo total ainda exigiria uma composição assíncrona;
  - OkHttp: uma dependência a mais.

## R5. Cópia guardada e consulta compartilhada

- **Decision**:
  - **Cópia guardada:** `ConcurrentHashMap<String, Guardada>`.
  - **Consultas em andamento:** `ConcurrentHashMap<String, CompletableFuture<Entrada>>`. O `computeIfAbsent` cria **uma** consulta por chave, e todos os pedidos simultâneos aguardam o mesmo futuro, recebendo o mesmo resultado, **inclusive a falha** (lição da T050 do E1).
  - **Fim da consulta:** ao terminar, o futuro sai do mapa só se ainda for o mesmo (`remove(chave, futuro)`).
  - **Falha com cópia vencida:** cada pedido que esperava devolve a cópia marcada como desatualizada.
  - **Não guardados:** "não encontrado" e erros não entram na cópia.
  - **Relógio:** é injetável (`Clock` e uma fonte monotônica), para os testes não esperarem de verdade.
- **Rationale**: as estruturas concorrentes da JDK dão a consulta única em poucas linhas. O `CompletableFuture` compartilha naturalmente o resultado e a exceção.
- **Alternatives considered**:
  - Caffeine (`AsyncLoadingCache`): tem consulta única, mas não serve a cópia vencida em caso de falha sem adaptação;
  - Spring Cache (`@Cacheable`): esconde a lógica que o experimento quer comparar e não tem validade por entrada nem cópia vencida.

## R6. Erros

- **Decision**:
  - um `@RestControllerAdvice` converte `ErroDominio` em `ProblemDetail`, com `type` igual à URN, `title`, `status`, `detail` e a propriedade `correlacao_id`;
  - `NoResourceFoundException` e `HttpRequestMethodNotSupportedException` viram 404 `nao-encontrado`;
  - erros de conversão de parâmetro viram 400;
  - qualquer outra exceção vira 500 `erro-interno`, com o `detail` genérico;
  - o `Content-Type` é `application/problem+json`, nativo do `ProblemDetail`;
  - `server.error.include-stacktrace=never`, e as páginas de erro padrão do Spring ficam desligadas.
- **Rationale**: o Spring 6+ já implementa a RFC 9457, e esse é um ponto a observar na comparação (no FastAPI foi preciso montar à mão). A propriedade extra `instance`, que o Spring pode incluir, é permitida pelo contrato, porque o schema `Problema` não fecha propriedades adicionais.

## R7. Dobra, ordenação e paridade com o E1

- **Decision**: `Normalizer.normalize(s, NFKD)`, depois remoção de `\p{Mn}` e `toLowerCase(Locale.ROOT)`.
  - **A JDK não tem `casefold`:** a diferença em relação ao Python aparece só em caracteres como `ß` ou ligaduras, que não ocorrem em nomes de municípios brasileiros.
  - **Garantia de igualdade:** um **cenário novo na suíte compartilhada** calcula a ordem esperada dos 645 municípios de SP com a regra do E1 e a compara com a resposta do serviço. Ele precisa passar no E1 e no E4 (FR-004, SC-005).
- **Rationale**: a regra é a mesma em espírito. A paridade não é presumida, é verificada.

## R8. Métricas com os nomes do contrato

- **Decision**: Micrometer com `micrometer-registry-prometheus`.

  | Métrica no Micrometer | Nome exposto |
  |---|---|
  | `Counter` `localidades.pedidos` (rótulos `rota`, `status`) | `localidades_pedidos_total` |
  | `Counter` `localidades.erros` (rótulo `tipo`) | `localidades_erros_total` |
  | `Counter` `localidades.cache` (rótulo `resultado`) | `localidades_cache_total` |
  | **`DistributionSummary`** `localidades.fonte.duracao.segundos` (rótulo `recurso`), sem unidade base, com as mesmas faixas do E1 (`serviceLevelObjectives`) | `localidades_fonte_duracao_segundos_bucket`, `_count` e `_sum` |

  O rótulo `rota` vem do atributo `BEST_MATCHING_PATTERN_ATTRIBUTE` do Spring, que dá o modelo da rota (`/v1/municipios/{codigo}`), ou vale `nao-encontrado`.

  O `/metrics` é um controller próprio que devolve o `scrape()` do registro. Os endpoints do actuator ficam todos desligados.
- **Rationale**: um `Timer` do Micrometer acrescentaria o sufixo de unidade `_seconds`, e o nome exposto deixaria de ser o do contrato. Esse era um dos pontos que a ADR 0001 mandava revisitar no E4. Com o `DistributionSummary` sem unidade, o nome fica exato.

## R9. Correlação e registro

- **Decision**:
  - **Correlação:** um filtro (`OncePerRequestFilter`), na ordem mais alta, aplica a regra do R12 do E1: aceita de 1 a 64 caracteres em `[A-Za-z0-9._-]` ou gera um UUID v4. Ele guarda o valor num atributo do pedido, devolve-o no cabeçalho de toda resposta e o entrega ao `ProblemDetail`.
  - **Registro:** no fim do pedido, o mesmo filtro escreve **uma linha JSON** com Jackson, num logger dedicado cujo padrão é só a mensagem (`%m%n`), com os mesmos campos do E1: `momento`, `nivel`, `correlacao_id`, `metodo`, `rota`, `status`, `duracao_ms`, `cache` e `fonte_ms`.
  - **Tempo da fonte e uso da cópia:** passam por atributos do pedido. O tempo da fonte é medido no cliente e anotado no pedido que iniciou a consulta.
  - **Outros logs:** o logging do Spring fica em `WARN`, para não poluir a saída.
- **Rationale**: o *structured logging* nativo do Spring Boot (ECS e Logstash) usa nomes de campos próprios. Para comparar com o E1, os campos precisam ser os mesmos.

## R10. Configuração `LOCALIDADES_*`

- **Decision**: o `application.properties` liga cada variável de forma **explícita**:
  - `localidades.prazo-fonte-s=${LOCALIDADES_PRAZO_FONTE_S:10}` e o mesmo para as outras;
  - `server.address=${LOCALIDADES_HOST:127.0.0.1}`;
  - `server.port=${LOCALIDADES_PORTA:8000}`.

  Um *record* `@ConfigurationProperties("localidades")` com `@Validated` (`@Positive` e `@Pattern` na URL) impede a partida com valor inválido, com a mensagem de erro do Spring.
- **Rationale**: o *relaxed binding* do Spring trata cada `_` da variável de ambiente como separador de nível. `LOCALIDADES_PRAZO_FONTE_S` viraria `localidades.prazo.fonte.s`, e não `localidades.prazo-fonte-s`. O mapeamento explícito mantém os nomes do contrato (R14 do E1) sem depender dessa regra.

## R11. Testes

- **Decision**:
  - **Ferramentas:** JUnit 5 e AssertJ.
  - **IBGE simulado:** WireMock 3.13.2, em porta local aleatória, servindo as fixtures de `contracts/localidades/fixtures-ibge/`, lidas por caminho relativo à raiz do repositório.
  - **Testes de integração:** `@SpringBootTest` com `MockMvc` e a URL do IBGE apontando para o WireMock.
  - **Testes de concorrência da cópia:** um relógio falso e `CompletableFuture` controlados pelo teste.
  - **SC-004 (sem rede):** os testes rodam no mesmo sandbox do E1, com `./mvnw -o`, depois de um build que popula `~/.m2`.
- **Rationale**: é o equivalente direto do `respx` e do `TestClient` do E1. O WireMock é o padrão de mercado para simular HTTP em Java.

## R12. Caixa-preta e paridade

- **Decision**:
  - o serviço é empacotado como `target/localidades.jar` (`finalName`) e verificado com `contracts/localidades/verificacao/verificar.sh "java -jar experiments/java/localidades/target/localidades.jar"`, depois de `./mvnw -q package`;
  - a suíte ganha um cenário de **paridade de ordenação** (R7), escrito para passar também no E1;
  - o contrato não muda.
- **Rationale**: é o critério de pronto definido no fechamento do E1, mais a verificação de paridade que a mudança de linguagem pede.

## R13. Método da comparação (FR-006 e FR-007)

- **Decision**: as medidas são tiradas no mesmo dia e na mesma máquina, com o cache de dependências já populado. Cada tempo é a **mediana de 3 execuções**, com `/usr/bin/time -l`, que dá o tempo e o pico de memória.

  | Medida | Método no E1 | Método no E4 |
  |---|---|---|
  | Do clone à primeira resposta | `git clone` local, `uv sync`, subir e `curl` | `git clone` local, `./mvnw -q package -DskipTests`, subir e `curl` |
  | Build | `uv sync` (sem build) | `./mvnw -q package -DskipTests` |
  | Suíte da implementação | `uv run --directory … pytest` | `./mvnw -q test` |
  | Partida até o `/health` | do comando ao primeiro 200 | idem |
  | Memória em repouso | RSS depois de 10 pedidos (`ps -o rss`) | idem |
  | Tamanho do artefato | pasta `.venv` + código | `localidades.jar` |
  | Linhas de código | produção e testes (`wc -l`, sem linhas em branco) | idem |
  | Dependências diretas | `pyproject.toml` | `pom.xml` |
  | Latência com cópia | mediana de 20 pedidos repetidos | idem |

  Para a avaliação qualitativa, cada um dos cinco pontos do FR-007 recebe uma nota de 1 a 5 com uma frase de justificativa, escrita durante a implementação, e não de memória no fim.
- **Rationale**: números iguais em forma permitem comparar sem declarar vencedor sem medida (FR-008, Constituição: "não declaram vencedor antes de medir").

## R14. Ordem do roteiro

- **Decision**: o E4 é antecipado para logo depois do E1. O `docs/roteiro.md` é atualizado: E0, E1, **E4**, E2, E3, E5, E6.
- **Rationale**: com o E1 fresco, a comparação de ergonomia é mais justa (sugestão registrada no fechamento do E1). A spec, o contrato, as fixtures e a suíte já existem, então o E4 é curto.

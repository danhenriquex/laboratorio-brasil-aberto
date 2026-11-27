---

description: "Lista de tarefas do E4 — Serviço de localidades (IBGE), em Java"
---

# Tasks: E4 — Serviço de localidades (IBGE), em Java

**Input**: Documentos de design em `specs/003-localidades-java/`. O comportamento vem de `specs/002-servico-localidades/`.

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/localidades/openapi.yaml](../../contracts/localidades/openapi.yaml), [quickstart.md](quickstart.md)

**Tests**: incluídos. O critério de pronto é a suíte de caixa-preta (FR-002), e a constituição (princípio IV) proíbe rede nos testes. Em cada história:
1. escreva os testes da implementação primeiro e confirme que falham;
2. implemente;
3. rode os cenários da história na suíte de caixa-preta contra o jar.

**Referência de comportamento**: o código do E1 (`experiments/python/localidades/src/localidades/`) é a referência executável de cada regra. Na dúvida, o comportamento do E1 e a suíte decidem.

**Organization**: tarefas agrupadas por história de usuário. Cada fase vira **uma branch e um PR**, e a próxima só começa depois do merge da anterior.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: história de usuário: US1 a US5, as do E1, e US6, a comparação

## Path Conventions

- **Projeto:** `experiments/java/localidades/`, chamado de **`J/`** abaixo.
- **Código:** `J/src/main/java/io/github/danhenriquex/brasilaberto/localidades/`, chamado de **`MAIN/`**.
- **Testes:** `J/src/test/java/io/github/danhenriquex/brasilaberto/localidades/`, chamado de **`TEST/`**.
- **Recursos:** `J/src/main/resources/`.
- **Comandos:**
  - build e testes: `(cd experiments/java/localidades && ./mvnw -q test)`;
  - caixa-preta: `./mvnw -q package -DskipTests` e depois `contracts/localidades/verificacao/verificar.sh "java -jar experiments/java/localidades/target/localidades.jar" [-k filtro]`, a partir da raiz.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: JDK, projeto Spring Boot e diário de ergonomia.

- [X] T001 Instalar o JDK 25 com `brew install --cask temurin@25`, **depois de confirmação do usuário** (é uma mudança no sistema). Conferir com `java -version`, que deve mostrar `25.0.x`, e registrar a versão exata e o tempo gasto em `specs/003-localidades-java/ergonomia.md`.
- [X] T002 Gerar o esqueleto em `experiments/java/localidades/` pelo Spring Initializr, o caminho comum de setup no ecossistema e parte da medida de ergonomia:
  - **Comando:**

    ```bash
    curl -s https://start.spring.io/starter.zip \
      -d type=maven-project -d javaVersion=25 -d bootVersion=4.1.3 \
      -d groupId=io.github.danhenriquex.brasilaberto -d artifactId=localidades -d name=localidades \
      -d packageName=io.github.danhenriquex.brasilaberto.localidades \
      -d dependencies=web,actuator,prometheus -o …
    ```

    Depois, descompactar em `J/`.
  - **Arquivos resultantes:** `J/pom.xml`, `J/mvnw`, `J/mvnw.cmd`, `J/.mvn/wrapper/` e `MAIN/LocalidadesApplication.java`.
  - **Ajustes no `J/pom.xml`:**
    - `<finalName>localidades</finalName>`;
    - dependência de teste `org.wiremock:wiremock-standalone:3.13.2`;
    - wrapper apontando para o Maven 3.10.x em `J/.mvn/wrapper/maven-wrapper.properties`.
- [X] T003 [P] Criar `J/.java-version` (`25`) e `J/src/main/resources/application.properties`, conforme os R2, R9 e R10 do research:
  - `server.address=${LOCALIDADES_HOST:127.0.0.1}` e `server.port=${LOCALIDADES_PORTA:8000}`;
  - `localidades.ibge-url=${LOCALIDADES_IBGE_URL:https://servicodados.ibge.gov.br/api/v1/localidades}`;
  - `localidades.prazo-fonte-s=${LOCALIDADES_PRAZO_FONTE_S:10}`;
  - `localidades.validade-s=${LOCALIDADES_VALIDADE_S:86400}`;
  - `localidades.itens-max=${LOCALIDADES_ITENS_MAX:500}`;
  - `spring.threads.virtual.enabled=true`;
  - `spring.main.banner-mode=off`;
  - `logging.level.root=WARN`;
  - `server.error.include-stacktrace=never` e `server.error.whitelabel.enabled=false`;
  - `management.endpoints.access.default=none` e `management.endpoints.web.exposure.exclude=*`.
- [X] T004 [P] Criar `J/README.md`, espelhando o README do E1: pergunta do E4, pré-requisitos (JDK 25), comandos de teste, de verificação e de execução, e links para o quickstart e o contrato. Criar também `specs/003-localidades-java/ergonomia.md`, o diário do FR-007, com uma seção por ponto: setup, testes, contrato, erros e métricas.
- [X] T005 Rodar `(cd experiments/java/localidades && ./mvnw -q package)`, confirmar que o projeto vazio compila e sobe, e versionar o wrapper e o `pom.xml`. O Maven não tem lockfile; as versões ficam fixadas no `pom.xml`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: domínio, configuração, erros, cliente do IBGE, base da API e do serviço, mais o cenário de paridade na suíte compartilhada.

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

### Testes da fundação (escrever primeiro)

- [X] T006 [P] Criar o apoio de testes em `TEST/apoio/`:
  - `Fixtures.java`: localiza a raiz do repositório subindo até achar `contracts/localidades` e lê `contracts/localidades/fixtures-ibge/*.json`;
  - `RelogioFalso.java`: um `Clock` com instante inicial `2026-11-26T12:00:00.123Z`, mais uma fonte monotônica, com `avancar(Duration)`;
  - `IbgeSimulado.java`: um WireMock em porta aleatória de `127.0.0.1`, com ajuda para registrar respostas a partir das fixtures. Nenhum teste fala com host externo.
- [X] T007 [P] Escrever `TEST/dominio/DominioTest.java`, com os mesmos casos do `test_dominio.py` do E1:
  - **`Dobra.dobrar`:** `"Niterói"` dá `"niteroi"`, `"SÃO"` dá `"sao"`, e o apóstrofo é mantido;
  - **ordenação** por `(dobrar(nome), codigo)`;
  - **`filtrarPorNome`;**
  - **`paginar`:** `paginas = ceil(total/itens)`, total 0 dá `paginas` 0, e página além do fim devolve vazio com o total;
  - **`resolverUf`:**
    - `" rj "` e `"33"` resolvem para `"33"`;
    - `"XX"` e `"99"` levantam `NaoEncontrado`;
    - `"R1"`, `"123"` e `""` levantam `EntradaInvalida`;
  - **`validarCodigoMunicipio`:** exige "`^\d{7}$`" só com dígitos ASCII, e `"330455７"` é recusado;
  - **`validarPaginacao`:** "inteiro de 1 a `ITENS_MAX` (padrão 500)", com o limite citado na mensagem;
  - **`validarNome`:** "aparado; de 2 a 60 caracteres".
- [X] T008 [P] Escrever `TEST/config/ConfiguracaoTest.java` com `ApplicationContextRunner`, cobrindo:
  - os padrões de R14 do E1: `127.0.0.1`, `8000`, a URL do IBGE, `10`, `86400` e `500`;
  - a leitura pelas variáveis `LOCALIDADES_*`;
  - a recusa de valores inválidos (não numérico, zero, negativo e URL sem `http://` ou `https://`), em que o contexto não sobe.
- [X] T009 [P] Escrever `TEST/fonte/ClienteIbgeTest.java` com o `IbgeSimulado`, espelhando o `test_fonte_ibge.py` do E1:
  - **Classificação:**

    | Situação simulada | Erro esperado |
    |---|---|
    | conexão recusada | `FonteIndisponivel` |
    | 503 e 429 | `FonteIndisponivel` |
    | atraso de 300 ms com prazo de 50 ms | `FonteLenta` em menos de 300 ms |
    | 404 | `RespostaInesperadaDaFonte` |
    | HTML com status 200 | `RespostaInesperadaDaFonte` |
    | JSON sem campo obrigatório | `RespostaInesperadaDaFonte` |

  - **Normalização:** 27 UFs com códigos em texto; 92 municípios do RJ; objeto ou lista de 1 aceitos; `[]` vira `NaoEncontrado`; `5101837` sem microrregião é aceito.
  - **Formato exato (T048 e T049 do E1):**
    - id de 5 dígitos na lista de municípios, UF com id `1` e região imediata com 5 dígitos levantam `RespostaInesperadaDaFonte`;
    - siglas `rj`, `Norte` (região) e `R J` também.
  - **Demais garantias:** exatamente 1 pedido por chamada e o `User-Agent` do laboratório.

### Implementação da fundação

- [X] T010 [P] Implementar `MAIN/erros/`:
  - `ErroDominio extends RuntimeException`, com `tipo()`, `titulo()`, `status()` e `urn()` (`urn:brasil-aberto:problema:` + tipo);
  - as subclasses `EntradaInvalida` (400), `NaoEncontrado` (404), `FonteIndisponivel` (502), `FonteLenta` (504), `RespostaInesperadaDaFonte` (502) e `ErroInterno` (500), com os títulos do E1;
  - a interface `ErroDeFonte`, implementada pelas três de fonte.
- [X] T011 Implementar `MAIN/dominio/` conforme o `data-model.md` do E4, sem anotações do Spring Web:
  - os `record`s das entidades;
  - `UfsOficiais`, com os 27 códigos e siglas;
  - `Dobra`: `Normalizer` NFKD, remoção de `\p{Mn}` e `toLowerCase(Locale.ROOT)`;
  - `Paginacao`/`Pagina` e `paginar`;
  - `Validacao` (`resolverUf`, `validarCodigoMunicipio`, `validarPaginacao` e `validarNome`), com `Pattern`s ASCII.

  Ao final, T007 passa.
- [X] T012 Implementar `MAIN/config/Configuracao.java` como `record` `@ConfigurationProperties("localidades")` `@Validated`, com `@Positive` nos números e `@Pattern("^https?://.+")` na URL, e habilitá-lo em `LocalidadesApplication`. A URL sem barra final é normalizada. Ao final, T008 passa.
- [X] T013 Implementar `MAIN/fonte/ClienteIbge.java`:
  - **Cliente:** `HttpClient` com `connectTimeout(prazo)`, sem redirecionamento e com o `User-Agent` `laboratorio-brasil-aberto-localidades/0.1.0`;
  - **Prazo total:** `sendAsync(…, ofByteArray()).orTimeout(prazo)`;
  - **Classificação:** a do R4 do research do E4;
  - **Normalização:** com Jackson (`JsonNode`), com quantidade **exata** de dígitos e siglas `^[A-Z]{2}$` e `^[A-Z]{1,2}$`;
  - **Medição:** chama um `BiConsumer<String, Double>` (recurso, segundos) a cada consulta;
  - **Mensagens de erro:** nunca contêm o corpo do IBGE.

  Ao final, T009 passa.
- [X] T014 Implementar a base HTTP e escrever `TEST/api/ApiBaseTest.java` (MockMvc), espelhando o `test_api_base.py` do E1:
  - **`MAIN/operacao/FiltroCorrelacao.java`** (`OncePerRequestFilter`, ordem mais alta): aceita `^[A-Za-z0-9._-]{1,64}$` ou gera um UUID v4, guarda o valor em atributo do pedido e o devolve em toda resposta;
  - **`MAIN/api/TratadorDeErros.java`** (`@RestControllerAdvice`), que devolve `ProblemDetail` com `type` URN e `correlacao_id`:
    - `ErroDominio` vira o problema correspondente;
    - `NoResourceFoundException` e `HttpRequestMethodNotSupportedException` viram 404 `nao-encontrado`;
    - erros de conversão de parâmetro viram 400;
    - qualquer outra exceção vira 500 `erro-interno` com o `detail` genérico;
  - **`MAIN/operacao/SaudeController.java`:** `GET /health` devolve `{"status":"ok"}`;
  - **o que o teste cobre:**
    - 404 para `/v2/ufs`, `/ufs` e `/nada`;
    - `POST /health` dá 404;
    - a correlação volta igual quando válida e é trocada quando inválida;
    - um 500 sem rastro de execução no corpo;
    - `Content-Type` `application/problem+json`.
- [X] T015 Implementar a base de `MAIN/servico/ServicoLocalidades.java`, sem Spring Web:
  - **`Meta`:** `fonte`, `url_fonte`, `url_documentacao` e `coletado_em`, formatado com `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'` em UTC. Um teste em `TEST/servico/MetaTest.java` confere que um instante com 0 ms sai como `.000Z`;
  - **`obter(chave, buscar)`:** nesta fase, chama a fonte direto. A cópia guardada entra em T028.

### Paridade na suíte compartilhada (FR-004, SC-005)

- [X] T016 Escrever `contracts/localidades/verificacao/tests/test_paridade_ordenacao.py`:
  - **Ordem esperada:** calculada a partir de `fixtures-ibge/municipios-uf-35.json` com a regra R8 do E1 (`unicodedata` NFKD, sem `Mn`, `casefold`, desempate pelo código).
  - **Comparação da lista:** a lista completa de SP, em duas páginas de 500, sai com os 645 códigos na mesma ordem.
  - **Comparação das buscas:** `nome=são` e `nome=SAO` dão o mesmo resultado esperado.
  - **Antes de seguir:** confirmar que passa **contra o E1**, com `verificar.sh "uv run --project experiments/python/localidades localidades" -k paridade`.

**Checkpoint**: `./mvnw -q test` passa (domínio, configuração, cliente e base da API), e o jar sobe e responde `/health` pelo `verificar.sh` (`-k contrato_valido`).

---

## Phase 3: User Story 1 - Listar estados e os municípios de um estado (Priority: P1) 🎯 MVP

**Goal**: `GET /v1/ufs`, `GET /v1/ufs/{uf}` e `GET /v1/ufs/{uf}/municipios` (sem o filtro por nome), como na US1 do E1.

**Independent Test**: os cenários `test_us1_ufs_municipios.py` e `test_paridade_ordenacao.py` (sem as buscas) passam contra o jar.

- [X] T017 [P] [US1] Escrever `TEST/api/ApiUfsTest.java` (MockMvc + `IbgeSimulado`), com os casos do `test_api_ufs.py` do E1:
  - 27 UFs ordenadas, com Acre primeiro;
  - `/v1/ufs/rj`, `/v1/ufs/33` e `/v1/ufs/%20RJ%20`;
  - `XX` e `99` dão 404, e `R1` dá 400, os três sem chamar o IBGE;
  - RJ com 92 municípios, `paginacao {1, 100, 92, 1}` e Angra dos Reis primeiro;
  - `itens=10&pagina=10` devolve 2 itens, e uma página além do fim devolve vazio;
  - `itens` 0, 501 ou `dez` e `pagina=0` dão 400, com o limite no `detail`;
  - `[]` para o RJ dá 502;
  - o DF tem 1 município;
  - 1 chamada ao IBGE por pedido.
- [X] T018 [US1] Em `MAIN/servico/ServicoLocalidades.java`, implementar `listarUfs()`, `obterUf(param)` (com uma UF da tabela ausente no IBGE virando `RespostaInesperadaDaFonte`) e `listarMunicipios(uf, pagina, itens)` (validar, resolver, buscar, ordenar e paginar).
- [X] T019 [US1] Criar `MAIN/api/UfsController.java` com as três rotas e o envelope `Resposta<T>` (`dados`, `paginacao` só nas listas, `meta`). `pagina` e `itens` chegam como `String` e são validados pelo domínio, para o `detail` citar `itens_max`. Ao final, T017 passa.
- [X] T020 [US1] Rodar `verificar.sh "java -jar …" -k "us1 or paridade or contrato_valido"` e registrar no diário de ergonomia o que exigiu ajuste para cumprir o contrato.

**Checkpoint**: US1 verificada pela mesma suíte do E1. É o MVP do E4.

---

## Phase 4: User Story 2 - Consultar um município pelo código oficial (Priority: P1)

**Goal**: `GET /v1/municipios/{codigo}`.

**Independent Test**: `test_us2_municipio.py` passa contra o jar.

- [X] T021 [P] [US2] Escrever `TEST/api/ApiMunicipioTest.java`, com os casos do `test_api_municipio.py` do E1:
  - `3304557` completo, com UF e regiões imediata e intermediária;
  - `9999999` dá 404;
  - `12ab`, `123456` e `12345678` dão 400 sem chamar o IBGE;
  - `Santa Bárbara d'Oeste` sai idêntico ao da fixture;
  - `5101837` dá 200;
  - um município sem região imediata dá 502.
- [X] T022 [US2] Em `MAIN/servico/ServicoLocalidades.java`, implementar `obterMunicipio(codigo)`.
- [X] T023 [US2] Criar `MAIN/api/MunicipiosController.java` com `GET /v1/municipios/{codigo}`. Ao final, T021 passa.
- [X] T024 [US2] Rodar `verificar.sh "java -jar …" -k us2` e registrar observações no diário.

---

## Phase 5: User Story 3 - Comportamento previsível quando o IBGE falha ou demora (Priority: P2)

**Goal**: cópia guardada com validade, consulta compartilhada **inclusive na falha** (lição da T050 do E1) e cópia vencida em caso de falha.

**Independent Test**: `test_us3_falhas.py` passa contra o jar, inclusive o cenário "pedidos simultâneos com a fonte travada não fazem fila".

- [X] T025 [P] [US3] Escrever `TEST/cache/CacheComValidadeTest.java` com o `RelogioFalso`, espelhando o `test_cache.py` do E1:
  - **cópia válida:** atende sem consultar;
  - **cópia vencida:** se a fonte responder, renova; se falhar, devolve a cópia marcada como desatualizada e com o `coletado_em` original, para cada um dos três erros de fonte;
  - **cópia ausente com falha:** propaga o erro;
  - **o que não é guardado:** `NaoEncontrado` e erros;
  - **`NaoEncontrado` com cópia vencida:** propaga;
  - **10 pedidos simultâneos com sucesso:** 1 consulta; um recebe `falta` e nove recebem `acerto`;
  - **10 pedidos simultâneos com falha:** 1 consulta, todos recebem a falha e terminam em menos de 2× o atraso;
  - **cópia vencida com falha e 5 pedidos simultâneos:** todos recebem `desatualizado`, com 1 consulta.
- [X] T026 [P] [US3] Escrever `TEST/api/ApiFalhasTest.java`, espelhando o `test_api_falhas.py` do E1:
  - **sem cópia:** fora, lenta e HTML dão 502, 504 e 502, sem corpo, rastro ou endereço interno no `detail`;
  - **com cópia:** uma cópia válida evita a consulta; uma vencida é servida quando a fonte falha e renovada quando ela responde;
  - **isolamento:** uma falha não afeta o pedido seguinte;
  - **listas:** também usam a cópia.
- [X] T027 [US3] Implementar `MAIN/cache/CacheComValidade.java` conforme o R5 do E4:
  - `ConcurrentHashMap` de guardadas;
  - `ConcurrentHashMap<String, CompletableFuture<Entrada>>` de consultas em andamento, com `computeIfAbsent` e, ao terminar, `remove(chave, futuro)`;
  - quem espera recebe o mesmo resultado, inclusive a exceção;
  - um erro de `ErroDeFonte` com cópia vencida devolve a cópia desatualizada;
  - o relógio é injetável.

  Ao final, T025 passa.
- [X] T028 [US3] Em `MAIN/servico/ServicoLocalidades.java`, trocar o `obter` para usar a `CacheComValidade`. O `meta` vem da entrada (`coletado_em` original e `desatualizado`), e o `resultado` da cópia fica exposto para as métricas. Ao final, T026 passa.
- [X] T029 [US3] Rodar `verificar.sh "java -jar …" -k us3` e registrar no diário como foi implementar a consulta compartilhada em Java comparado ao `asyncio`.

---

## Phase 6: User Story 4 - Encontrar um município pelo nome dentro de um estado (Priority: P3)

**Goal**: o parâmetro `nome` em `GET /v1/ufs/{uf}/municipios`.

**Independent Test**: `test_us4_busca.py` e as buscas de `test_paridade_ordenacao.py` passam contra o jar.

- [X] T030 [P] [US4] Escrever `TEST/api/ApiBuscaTest.java`, espelhando o `test_api_busca.py` do E1:
  - `niteroi`, `NITERÓI` e `  Niterói  ` acham Niterói;
  - `são` devolve vários resultados, em ordem e paginados;
  - uma busca sem resultado devolve `[]` com `paginas` 0;
  - `a`, `  a  `, `""` e 61 caracteres dão 400, com o limite no `detail`;
  - duas buscas na mesma UF geram 1 consulta.
- [X] T031 [US4] Acrescentar o `nome` opcional a `listarMunicipios` em `MAIN/servico/ServicoLocalidades.java` (validar, depois filtrar, ordenar e paginar) e ao `UfsController`. Ao final, T030 passa.
- [X] T032 [US4] Rodar `verificar.sh "java -jar …" -k "us4 or paridade"`.

---

## Phase 7: User Story 5 - Saber se o serviço está saudável e como está sendo usado (Priority: P3)

**Goal**: métricas com os nomes do contrato, registro JSON por pedido e correlação verificada de fora.

**Independent Test**: `test_us5_operacao.py` passa contra o jar, e a suíte inteira também.

- [X] T033 [P] [US5] Escrever `TEST/operacao/OperacaoTest.java`, espelhando o `test_api_operacao.py` do E1:
  - **`/health`:** responde com o IBGE fora e sem chamá-lo;
  - **`/metrics`**, depois de acerto, falta, desatualizado, `fonte-lenta` e `entrada-invalida`, contém exatamente:
    - `localidades_pedidos_total{rota="/v1/municipios/{codigo}",status="200"}`;
    - `localidades_erros_total{tipo="fonte-lenta"}`;
    - `localidades_cache_total{resultado="acerto"}`, `{resultado="falta"}` e `{resultado="desatualizado"}`;
    - `localidades_fonte_duracao_segundos_count{recurso="municipio"}`;
  - **rotas inexistentes:** viram `rota="nao-encontrado"`, sem multiplicar séries;
  - **registro:** uma linha JSON por pedido, com os campos do R12 do E1 e sem IP.
- [X] T034 [P] [US5] Implementar `MAIN/operacao/Metricas.java` com o Micrometer:
  - os `Counter`s `localidades.pedidos`, `localidades.erros` e `localidades.cache`;
  - o **`DistributionSummary`** `localidades.fonte.duracao.segundos`, sem unidade base, com `serviceLevelObjectives` 0,05, 0,1, 0,25, 0,5, 1, 2,5, 5 e 10;
  - o `MetricasController`, com `GET /metrics` devolvendo o `scrape()` do `PrometheusMeterRegistry` em `text/plain`.

  Conferir no teste que **nenhum nome ganhou sufixo de unidade** (R8).
- [X] T035 [US5] Implementar `MAIN/operacao/RegistroPedidos.java` e integrar no `FiltroCorrelacao`:
  - no fim de cada pedido, registrar as métricas;
  - escrever uma linha JSON (Jackson) num logger dedicado com padrão `%m%n`, configurado em `J/src/main/resources/logback-spring.xml`;
  - a rota vem do `BEST_MATCHING_PATTERN_ATTRIBUTE`;
  - o uso da cópia e o tempo da fonte vêm de atributos do pedido.

  Ao final, T033 passa.
- [X] T036 [US5] Rodar a suíte inteira, `verificar.sh "java -jar experiments/java/localidades/target/localidades.jar"`, e confirmar que **todos** os cenários passam, os mesmos do E1 mais o de paridade (SC-001).

**Checkpoint**: E4 funcionalmente equivalente ao E1, verificado pela mesma suíte.

---

## Phase 8: User Story 6 - Comparar o E1 e o E4 com medidas (Priority: P2)

**Goal**: as 9 medidas do FR-006 e a avaliação qualitativa do FR-007, pelo método do R13 do research.

**Independent Test**: a tabela comparativa do `RESULTS.md` fica preenchida para as duas implementações, com data e método.

- [X] T037 [US6] Escrever `specs/003-localidades-java/medicao/medir.sh`, que tira as 9 medidas do R13 para o E1 e para o E4, com mediana de 3 execuções e `/usr/bin/time -l`:
  - do clone local à primeira resposta;
  - build;
  - suíte da implementação;
  - partida até o `/health`;
  - RSS depois de 10 pedidos;
  - tamanho do artefato;
  - linhas de produção e de teste, sem linhas em branco;
  - dependências diretas;
  - latência mediana de 20 pedidos com a cópia guardada, contra o IBGE falso.

  O script imprime uma tabela em Markdown com data e método.
- [X] T038 [US6] Rodar o `medir.sh` na mesma máquina e no mesmo dia, com os caches populados, e guardar a saída em `specs/003-localidades-java/medicao/resultado-AAAA-MM-DD.md`.
- [X] T039 [US6] Consolidar o `specs/003-localidades-java/ergonomia.md` numa nota de 1 a 5 com justificativa para cada ponto do FR-007 (setup, testes, contrato, erros e métricas), para o E1 e para o E4. Toda diferença citada traz a medida e o contexto (FR-008).

---

## Phase 9: Polish & Fechamento do experimento

- [X] T040 Verificar sem rede externa (SC-004), com o perfil do quickstart §3:
  - o `curl` ao IBGE falha;
  - `./mvnw -o -q test` passa;
  - o `verificar.sh` passa contra o jar;
  - como regressão, os testes do E1, a caixa-preta do E1 e os testes do E0 também passam.
- [X] T041 Fazer a execução real contra o IBGE, conforme o quickstart §4:
  - repetir os mesmos pedidos contra o E1 e o E4;
  - comparar os corpos, ignorando `coletado_em` e `url_fonte` quando a base diferir;
  - registrar data e latências.
- [X] T042 [P] Atualizar `docs/adr/0001-convencoes-comuns-de-api.md` para "aceita no E1 e confirmada no E4", com os achados:
  - o sufixo de unidade do Micrometer;
  - o `casefold` sem equivalente direto em Java;
  - o `ProblemDetail` nativo;
  - o *relaxed binding* das variáveis de ambiente.

  Atualizar também o comando do E4 em `contracts/localidades/README.md`.
- [X] T043 Escrever `specs/003-localidades-java/RESULTS.md` a partir de `docs/templates/RESULTS.md`, com:
  - a resposta à pergunta;
  - a tabela comparativa (T038) e a avaliação qualitativa (T039);
  - o que funcionou e o que surpreendeu;
  - as limitações;
  - os próximos passos: E2, e a decisão de se o serviço "se gradua" para `services/` e em qual linguagem.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 vem antes de tudo e depende da confirmação do usuário para instalar o JDK.
- **Foundational (Phase 2)**: depende do Setup e bloqueia as histórias. T016 (paridade na suíte) não depende do Java e pode ser feita em paralelo.
- **US1 e US2**: dependem da fundação, e a US2 vem depois da US1, porque mexe nos mesmos arquivos.
- **US3**: depende da fundação. T028 altera o `obter` do serviço.
- **US4**: estende a rota da US1 e usa a cópia guardada da US3.
- **US5**: T034 é independente. T035 integra no filtro e depende do `resultado` da cópia (T028).
- **US6**: depende da US1 à US5, porque a comparação só faz sentido com o serviço completo.
- **Polish**: depende da US6.

### Ordem de entrega (uma branch e um PR por fase, esperando cada merge)

Setup e fundação → US1 → US2 → US3 → US4 → US5 → US6 → Fechamento.

### Parallel Opportunities

- **Phase 1:** T003 e T004 em paralelo.
- **Phase 2:** T006 a T009 e T010 em paralelo, e T016 independente do Java.
- **Histórias:** em cada uma, o teste [P] pode ser escrito em paralelo ao teste da suíte, quando houver.
- **US5:** T033 e T034 em paralelo.
- **Polish:** T042 em paralelo com T040 e T041.

---

## Parallel Example: Foundational

```bash
Task: "T007 DominioTest.java em TEST/dominio/"
Task: "T008 ConfiguracaoTest.java em TEST/config/"
Task: "T009 ClienteIbgeTest.java em TEST/fonte/"
Task: "T016 test_paridade_ordenacao.py em contracts/localidades/verificacao/tests/"
```

---

## Implementation Strategy

### MVP First

1. Setup, com o JDK confirmado pelo usuário, e a fundação.
2. US1.
3. **Parar e validar**: os cenários da US1 e da paridade passam contra o jar. A comparação já começa a ter dados, pelo diário de ergonomia.

### Incremental Delivery

Cada fase é um PR com `Closes` só da sua issue. A próxima fase começa depois do merge, numa branch nova saída da `develop`.

---

## Notes

- O contrato e a suíte compartilhada só mudam com cenários novos que **também passem contra o E1** (FR-002).
- O E1 é a referência executável: se o Java divergir num detalhe, a suíte decide, e a divergência vai para o diário.
- Os testes nunca chamam o IBGE real. Chamadas reais acontecem só em T041, com data registrada.
- O diário de ergonomia é escrito **durante** cada fase, e não de memória no fim (R13).

## Phase 10: Convergence

- [ ] T044 Fazer com que os pedidos recusados pelo Tomcat antes do Spring (codificação inválida como `/v1/municipios/%ZZ` e barra codificada como `/v1/ufs/%2F`) respondam em `application/problem+json` com `X-Correlation-Id` (no cabeçalho e em `correlacao_id`), em vez da página HTML do Tomcat, por exemplo com um `ErrorReportValve` próprio registrado num `WebServerFactoryCustomizer` em `experiments/java/localidades/src/main/java/io/github/danhenriquex/brasilaberto/localidades/operacao/`; cobrir com o cenário de caixa-preta `test_entrada_mal_codificada_e_problema` em `contracts/localidades/verificacao/tests/test_us5_operacao.py` (`%ZZ` → 400 `entrada-invalida` em problem+json com correlação), que precisa passar também contra o E1 per FR-001 do E4 → FR-010 e FR-024 do E1 (partial)
- [ ] T045 Alinhar a leitura de `pagina` e `itens` ao E1 e ao contrato em `experiments/java/localidades/src/main/java/io/github/danhenriquex/brasilaberto/localidades/api/UfsController.java`: um inteiro grande demais para `int` em `pagina` vale como página além do fim (200 com `dados` vazio), e um parâmetro repetido usa o último valor; cobrir com testes em `ApiUfsTest.java` e com cenários em `contracts/localidades/verificacao/tests/test_us1_ufs_municipios.py` (`pagina=99999999999` → 200 vazio com o total; `itens=10&itens=20` → `itens` 20), que precisam passar também contra o E1 per FR-001 e FR-002 do E4 e o schema de `pagina` no contrato (partial)

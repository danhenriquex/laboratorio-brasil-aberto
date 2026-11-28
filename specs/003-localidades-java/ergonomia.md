# Diário de ergonomia: E1 (Python) × E4 (Java)

Anotações feitas **durante** a implementação do E4, para a avaliação qualitativa do FR-007 não ser escrita de memória no fim (research R13). O lado do E1 vem do `RESULTS.md` e do histórico do E1. Cada entrada leva a data.

## Setup

- **2026-11-27, JDK:** a máquina não tinha Java. O `brew install --cask temurin@25` baixou o pacote em 12 s, mas a instalação parou: o pacote é um `.pkg` que pede senha de administrador, e o assistente não consegue digitá-la. É um passo manual a mais em relação ao Python, onde o `uv` traz o interpretador sem privilégio de administrador.
- **2026-11-27, esqueleto:** o Spring Initializr (`curl start.spring.io/starter.zip`) gerou o projeto em 3 s, com o Maven Wrapper já apontando para o Maven 3.10.2. O Maven não precisa ser instalado. No E1, o equivalente foi escrever o `pyproject.toml` à mão e rodar `uv sync`.
- **2026-11-27, nomes:** no Spring Boot 4, o starter web passou a se chamar `spring-boot-starter-webmvc`, e há starters de teste por módulo (`…-webmvc-test`, `…-actuator-test`). Tutoriais anteriores ao Boot 4 citam `spring-boot-starter-web`.
- **2026-11-27, JDK instalado pelo usuário** no próprio terminal, por causa da senha de administrador. Depois disso, o primeiro `./mvnw package` (que baixa o próprio Maven e as dependências) levou 4 s, e o serviço vazio sobe em cerca de 1 s.
- **2026-11-27, `-o` (offline):** o `./mvnw -o test` falhou na primeira vez porque o plugin de testes (`surefire-junit-platform`) só é baixado quando os testes rodam pela primeira vez. É preciso um `./mvnw test` com rede antes de usar o modo offline. No `uv`, o `uv sync` já baixa tudo.
- **2026-11-27, ajustes no pom:**
  - o `micrometer-registry-prometheus` veio com escopo `runtime` e precisou passar a compilação, porque o `/metrics` próprio usa a classe diretamente;
  - o `spring-boot-starter-validation` precisou ser acrescentado para validar a configuração (`@Positive`). O plano listava só web e actuator.

## Testes

- **2026-11-27, fundação:** 71 testes (domínio, configuração, cliente do IBGE, `meta` e base da API) em cerca de 3 s com o Spring subindo. O WireMock fez o papel do `respx` sem atrito, e simular atraso (`withFixedDelay`) e conexão recusada (servidor parado) foi direto.
- **Testes parametrizados:** `@ParameterizedTest` com `@CsvSource` e `@ValueSource` cobrem as mesmas tabelas do `pytest.mark.parametrize`, com mais cerimônia.
- **Configuração:** testar a configuração pede o `ApplicationContextRunner`, o `ConfigDataApplicationContextInitializer` e a autoconfiguração de validação. São três peças de framework para o que no E1 foi chamar `Configuracao.do_ambiente({...})`.
- **2026-11-27, US3, isolamento entre testes:** no E1, cada teste criava um app novo. No Spring, o contexto é reaproveitado entre os testes da mesma configuração (é o que deixa a suíte rápida), e a cópia guardada vazaria de um teste para o outro. Foi preciso tornar o cache um bean e limpá-lo num `@BeforeEach`. Para controlar o relógio, um `@TestConfiguration` com um `RelogioFalso` marcado como `@Primary`, que por isso ganha um contexto próprio.
- **Jackson 3:** o Spring Boot 4 traz o Jackson 3 (pacote `tools.jackson`). A API mudou (`isString`/`asString` no lugar de `isTextual`/`asText`), e exemplos antigos da internet não compilam.

## Cumprir o contrato escrito à mão

- **2026-11-27, US1:** os 21 cenários da US1 e da paridade passaram contra o jar **na primeira execução**, sem ajuste no código para o contrato.
  - **O que ajudou:** `record`s com a ordem dos campos igual à do contrato, `spring.jackson.property-naming-strategy=SNAKE_CASE` (sem anotação por campo) e `@JsonInclude(NON_NULL)` para a `paginacao` aparecer só nas listas.
  - **Paridade:** a ordem dos 645 municípios de SP saiu idêntica à do E1 com `Normalizer` NFKD + `\p{Mn}` + `toLowerCase(Locale.ROOT)`. A falta de `casefold` não fez diferença nos nomes reais.
- **2026-11-27, US2:** os cenários da US2 passaram contra o jar na primeira execução. Com o domínio e o envelope prontos, a história inteira foi um método no serviço e um controller de 15 linhas, como no E1 (um método e uma rota). O `SNAKE_CASE` global já transformou `regiaoImediata` em `regiao_imediata`, sem anotação.
- **2026-11-27, US4:** a busca por nome entrou com um parâmetro a mais no controller e um filtro no serviço. As 4 buscas da paridade (`são`, `SAO`, `d'oeste` e `ITÁ` em SP) deram o mesmo conjunto e a mesma ordem do E1 na primeira execução, o que confirma que a falta de `casefold` não pesa para nomes brasileiros.
- **Armadilha de teste:** `MockMvc.get(String)` trata o caminho como *template* de URI e codifica o `%` de novo, então `/v1/ufs/%20RJ%20` virou `%2520`. O teste precisou de `get(URI.create(...))`. No E1, o `TestClient` não tinha esse problema.

## Convergência

- **2026-11-27, entradas mal formadas:** a convergência pegou o que só aparece fora do Spring.
  - **Caminhos mal codificados:** `%ZZ` e `%2F` são recusados pelo **Tomcat** antes de o pedido chegar ao Spring. A resposta saía na página HTML do Tomcat (com a versão do servidor), sem `X-Correlation-Id`.
  - **A correção:** uma `ErrorReportValve` própria. Ela precisou ser registrada como **classe** do host (`setErrorReportValveClass`), porque, nos erros anteriores ao roteamento, o Tomcat cria a válvula pela classe e ignora a instância que o Spring Boot põe no pipeline. Descobrir isso exigiu ler o bytecode do `CoyoteAdapter`.
  - **No E1:** o uvicorn entregou o mesmo erro ao FastAPI, e o formato saiu certo sem nada especial.
- **2026-11-27, números grandes e parâmetro repetido:** o `Integer.parseInt` estourava com `pagina=99999999999` (o Python não tem esse limite), e o Spring juntava `itens=10&itens=20` em `"10,20"`. Foi resolvido lendo com `BigInteger` e pegando o último valor.
- **2026-11-27, segunda convergência (query mal codificada e TRACE):** de novo, o que quebrou estava entre o Tomcat e o Spring.
  - **Query mal codificada:** o Tomcat decodifica a *query* de forma preguiçosa, só quando alguém lê o primeiro parâmetro. Então `?nome=%ZZ` não falha na entrada: falha dentro do controller, com uma `InvalidParameterException` (filha de `IllegalStateException`) que caía no tratador genérico e virava 500. Resolveu um `@ExceptionHandler` específico. O E1 nem percebe: o Starlette decodifica de forma tolerante e devolve 200.
  - **TRACE:** o conector do Tomcat recusa o `TRACE` por padrão (405), e o erro caía na página `/error` do Spring Boot. A propriedade `spring.mvc.dispatch-trace-request=true` parecia a saída, mas o `FrameworkServlet` só considera o `TRACE` atendido se a resposta for `message/http`. Fora isso, ele chama o `HttpServlet.doTrace`, que **ecoa o pedido inteiro, cookies inclusive**, logo depois do nosso `problem+json`. Só deu para ver com um pedido cru no socket. Resolveu um `DispatcherServlet` próprio, que sobrescreve o `doTrace`.
  - **Testes:** o MockMvc não passa pela decodificação da *query* nem pelo conector. Os dois casos exigiram subir o Tomcat numa porta livre (`RANDOM_PORT`) e escrever o pedido HTTP à mão, porque o `HttpClient` da JDK recusa um `%` inválido na URI. No E1, os mesmos casos foram testados com o `http.client` da biblioteca padrão, também cru.
- **2026-11-27, terceira convergência (cabeçalho Accept):** a negociação de conteúdo do Spring MVC vem ligada e é silenciosa. Sem conversor para XML, um `Accept: application/xml` gera uma `HttpMediaTypeNotAcceptableException`, que o tratador genérico de erros transformava em 500. E, como o `ProblemDetail` é JSON, um `Accept: application/problem+json` fazia o Jackson servir até a lista de UFs com esse tipo. Resolveram duas linhas num `WebMvcConfigurer` (`ignoreAcceptHeader(true)` e `defaultContentType(APPLICATION_JSON)`), mais o tipo explícito no `TratadorDeErros`. O FastAPI do E1 não negocia nada: a resposta sai no tipo que a rota declara, e pronto. É mais um caso em que o Spring faz por padrão o que ninguém pediu e o contrato não prevê.
- **2026-11-27, quarta convergência (configuração extrema):** o `@Positive` aceita `Infinity`, porque infinito é maior que zero, e aceita `0.0001`, que vira 0 ms ao passar para `Duration`. Bastaram `@DecimalMin` e `@DecimalMax` no *record* de configuração, e a mensagem saiu no mesmo relatório do Spring. Foi um ponto positivo do Java: a validação declarativa, com mensagem e origem da variável (*System Environment Property*), sai de graça. No E1, as mesmas regras foram escritas à mão, e lá o `float("inf")` e o `float("nan")` passam, porque `inf > 0` é verdadeiro e `nan <= 0` é falso.
- **2026-11-27, quinta convergência (`;` no caminho):** os parâmetros de caminho são uma herança da especificação de Servlet (o `;jsessionid=` das sessões sem cookie). O Tomcat os separa do caminho, e o Spring casa a rota ignorando o que vem depois do `;`. Nenhuma configuração desliga isso para o `PathPatternParser`. A correção mais limpa foi sobrescrever o `getHandler` do `DispatcherServlet` próprio, que já existia por causa do TRACE, para não achar rota quando o caminho cru tem `;`. Assim o pedido segue o caminho normal até o `TratadorDeErros`, com correlação, métricas e registro. O Starlette, no E1, trata o caminho como texto: `ufs;jsessionid=x` simplesmente não é `ufs`.

## Consulta compartilhada e concorrência

- **2026-11-27, US3:** a consulta única com falha compartilhada (a lição da T050 do E1) saiu em cerca de 30 linhas: `ConcurrentHashMap.putIfAbsent` de um `CompletableFuture`, e quem chega depois faz `join()` no mesmo futuro.
  - **Diferença para o E1:** no Python, a primeira versão (com `asyncio.Lock`) enfileirava os pedidos e só a 3ª convergência pegou. Aqui, o desenho certo veio desde o início porque a lição já existia. A comparação de "qual linguagem induz o erro" fica prejudicada por isso, e convém registrar no `RESULTS`.
  - **Threads virtuais:** o `join()` bloqueante é barato, então o código ficou sequencial, sem `async`/`await`. No E1, cada camada até o cliente HTTP precisou ser `async`.
  - **Verificação:** os cenários da US3 na caixa-preta, inclusive "não fazem fila", passaram na primeira execução.

## Tratamento de erros

- **2026-11-27:** o `ProblemDetail` nativo deu o `application/problem+json` sem código próprio; no E1, o formato foi montado à mão. Rotas inexistentes viram `NoResourceFoundException`, e o `@RestControllerAdvice` trata tudo num lugar. Para o `X-Correlation-Id` aparecer até nos erros, bastou o filtro definir o cabeçalho antes da cadeia, mais simples que no E1, onde o middleware precisou capturar a exceção.

## Métricas e registro

- **2026-11-27, US5, nomes:** com o Micrometer, os nomes do contrato saíram exatos (`localidades_pedidos_total`, `localidades_fonte_duracao_segundos_count` etc.). Para a duração da fonte foi usado um `DistributionSummary` sem unidade, como previsto no R8, porque um `Timer` acrescentaria `_seconds`. O teste confere que nenhum nome ganhou sufixo.
- **Três tropeços de framework, sem equivalente no E1:**
  1. **Exportação desligada nos testes:** o Spring Boot desliga a exportação de métricas nos testes, e o `PrometheusMeterRegistry` some do contexto. A propriedade `management.defaults.metrics.export.enabled=true` **não** resolveu; foi preciso a anotação `@AutoConfigureMetrics`, que no Boot 4 mudou de pacote (`org.springframework.boot.micrometer.metrics.test.autoconfigure`).
  2. **Rotas inexistentes:** elas casavam com o tratador de arquivos estáticos (`/**`), então o rótulo saía `rota="/**"`. Resolvido com `spring.web.resources.add-mappings=false` e tratando o `NoHandlerFoundException`.
  3. **Aviso duplicado:** o Spring escrevia um `WARN PageNotFound` a cada rota inexistente, poluindo a saída. Silenciado por configuração.
- **Registro JSON:** foi preciso um `logback-spring.xml` com um logger dedicado (`%msg%n`). No E1, foi um `logging.Formatter` de 15 linhas.
- **Tempo da fonte por pedido:** saiu pelo `RequestContextHolder` (atributos do pedido presos à thread). Funciona porque a consulta roda na thread do pedido que a iniciou. No E1, foi uma `ContextVar`.
- **Resultado:** a suíte inteira de caixa-preta (53 cenários) passou contra o jar.

## Avaliação (FR-007)

Notas de 1 (difícil) a 5 (fácil) para a experiência de construir o mesmo serviço, a partir das anotações acima e do histórico do E1. As medidas citadas estão em [medicao/resultado-2026-11-27.md](medicao/resultado-2026-11-27.md).

| Ponto | E1 (Python) | E4 (Java) | Por quê |
|---|---|---|---|
| **Setup** | 5 | 3 | No E1, o `uv` trouxe o interpretador e as dependências sem privilégio de administrador; do clone à primeira resposta, 1,0 s. No E4, o JDK exigiu senha de administrador, os starters mudaram de nome no Boot 4 e o modo offline do Maven só funciona depois de os testes rodarem uma vez com rede. O Initializr e o Maven Wrapper compensam em parte; do clone à primeira resposta, 2,9 s. |
| **Escrita de testes** | 4 | 3 | Os dois ecossistemas têm boas ferramentas: `pytest` e `respx` de um lado, JUnit, AssertJ e WireMock do outro. No E4, o contexto reaproveitado do Spring exigiu limpar o cache entre os testes, a exportação de métricas vem desligada nos testes e o `MockMvc` recodifica `%` no caminho. A suíte do E1 roda em 1,0 s, e a do E4, em 5,9 s. O E1 teve o seu tropeço: da raiz, o `pytest` coletava testes de todo o repositório. |
| **Cumprir o contrato escrito à mão** | 4 | 4 | Nos dois, o contrato passou praticamente sem retrabalho. No E1, foi preciso desligar o OpenAPI automático e converter o 422 do FastAPI em 400. No E4, `record`s com `SNAKE_CASE` global passaram de primeira, mas o *relaxed binding* exigiu mapear as variáveis `LOCALIDADES_*` à mão. A paridade de ordenação saiu igual sem esforço. |
| **Tratamento de erros** | 3 | 4 | No E1, o `problem+json` foi montado à mão, e o middleware precisou capturar a exceção para o 500 levar a correlação. No E4, o `ProblemDetail` nativo e o `@RestControllerAdvice` resolveram quase tudo. Só as rotas inexistentes pediram um tratamento extra (`NoHandlerFoundException`). |
| **Métricas e registro** | 4 | 3 | No E1, o `prometheus-client` expôs os nomes exatos, e o registro JSON foi um `Formatter` de 15 linhas. No E4, o Micrometer pede cuidado com o sufixo de unidade, e houve três tropeços de framework: exportação desligada nos testes, rótulo `/**` em rota inexistente e aviso duplicado do Spring. |

**Cuidados de leitura (FR-008):**
- **Ordem de construção:** o E4 foi feito **depois** do E1, com as decisões e as três correções das convergências já conhecidas. Por exemplo, a consulta compartilhada acertou de primeira no Java porque a lição já existia. Isso favorece o E4 em "acertar o desenho", e não diz nada sobre a linguagem.
- **Mesmo autor:** as duas implementações foram escritas pelo mesmo assistente, com o mesmo estilo e o mesmo nível de familiaridade. Uma equipe com experiência maior em um dos ecossistemas teria outras notas.
- **Números do contexto, não do serviço:** a memória (55 MB × 261 MB) e a partida (0,14 s × 1,01 s) refletem o custo fixo da JVM e do Spring. A latência depois do aquecimento empata (0,37 ms × 0,41 ms), porque o serviço só repassa dados e a pilha HTTP domina. O tamanho do artefato favorece o Java (26 MB, com o servidor embutido, contra 81 MB da `.venv`).

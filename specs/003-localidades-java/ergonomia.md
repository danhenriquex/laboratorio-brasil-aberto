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
- **Jackson 3:** o Spring Boot 4 traz o Jackson 3 (pacote `tools.jackson`). A API mudou (`isString`/`asString` no lugar de `isTextual`/`asText`), e exemplos antigos da internet não compilam.

## Cumprir o contrato escrito à mão

_(a preencher)_

## Tratamento de erros

- **2026-11-27:** o `ProblemDetail` nativo deu o `application/problem+json` sem código próprio; no E1, o formato foi montado à mão. Rotas inexistentes viram `NoResourceFoundException`, e o `@RestControllerAdvice` trata tudo num lugar. Para o `X-Correlation-Id` aparecer até nos erros, bastou o filtro definir o cabeçalho antes da cadeia, mais simples que no E1, onde o middleware precisou capturar a exceção.

## Métricas

_(a preencher)_

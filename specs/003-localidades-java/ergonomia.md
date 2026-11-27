# Diário de ergonomia: E1 (Python) × E4 (Java)

Anotações feitas **durante** a implementação do E4, para a avaliação qualitativa do FR-007 não ser escrita de memória no fim (research R13). O lado do E1 vem do `RESULTS.md` e do histórico do E1. Cada entrada leva a data.

## Setup

- **2026-11-27, JDK:** a máquina não tinha Java. O `brew install --cask temurin@25` baixou o pacote em 12 s, mas a instalação parou: o pacote é um `.pkg` que pede senha de administrador, e o assistente não consegue digitá-la. É um passo manual a mais em relação ao Python, onde o `uv` traz o interpretador sem privilégio de administrador.
- **2026-11-27, esqueleto:** o Spring Initializr (`curl start.spring.io/starter.zip`) gerou o projeto em 3 s, com o Maven Wrapper já apontando para o Maven 3.10.2. O Maven não precisa ser instalado. No E1, o equivalente foi escrever o `pyproject.toml` à mão e rodar `uv sync`.
- **2026-11-27, nomes:** no Spring Boot 4, o starter web passou a se chamar `spring-boot-starter-webmvc`, e há starters de teste por módulo (`…-webmvc-test`, `…-actuator-test`). Tutoriais anteriores ao Boot 4 citam `spring-boot-starter-web`.
- **2026-11-27, ajustes no pom:**
  - o `micrometer-registry-prometheus` veio com escopo `runtime` e precisou passar a compilação, porque o `/metrics` próprio usa a classe diretamente;
  - o `spring-boot-starter-validation` precisou ser acrescentado para validar a configuração (`@Positive`). O plano listava só web e actuator.

## Testes

_(a preencher durante as fases)_

## Cumprir o contrato escrito à mão

_(a preencher)_

## Tratamento de erros

_(a preencher)_

## Métricas

_(a preencher)_

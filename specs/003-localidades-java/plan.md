# Implementation Plan: E4 — Serviço de localidades (IBGE), em Java

**Branch**: `003-localidades-java` | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-localidades-java/spec.md`, que reaproveita o comportamento de [specs/002-servico-localidades/spec.md](../002-servico-localidades/spec.md)

## Summary

Reimplementar o serviço de localidades do E1 em **Java 25 (LTS) com Spring Boot 4.1**, cumprindo o mesmo contrato ([contracts/localidades/openapi.yaml](../../contracts/localidades/openapi.yaml)) e passando na mesma suíte de caixa-preta. Depois, comparar as duas implementações com 9 medidas e uma avaliação qualitativa.

O desenho reproduz as decisões já validadas do E1:

- prazo total por consulta;
- cópia com validade e cópia vencida em caso de falha;
- consulta compartilhada **inclusive na falha**, a lição da T050;
- códigos e siglas validados contra o data-model (T048 e T049);
- problem+json com URNs;
- métricas e registro com os mesmos nomes.

O que muda é o "como" de cada ecossistema. Detalhes em [research.md](research.md).

## Technical Context

**Language/Version**: Java 25 (LTS; Eclipse Temurin 25.0.5 via Homebrew). Confirma a "versão a confirmar no E4" da constituição

**Primary Dependencies**:

- **Framework:** Spring Boot 4.1.3, com `spring-boot-starter-web` (Spring MVC em threads virtuais) e `spring-boot-starter-actuator`, usado só para a autoconfiguração do Micrometer;
- **Métricas:** `micrometer-registry-prometheus`;
- **Cliente HTTP:** `java.net.http.HttpClient`, da própria JDK;
- **JSON:** Jackson, que vem com o Spring.

**Storage**: nenhum. A cópia guardada fica em memória (`ConcurrentHashMap`), e as fixtures são as mesmas do E1, em `contracts/localidades/fixtures-ibge/`

**Testing**:

- JUnit 5, AssertJ, Spring Boot Test (`MockMvc`) e WireMock 3.13.2, que simula o IBGE, como o `respx` no E1;
- suíte de caixa-preta compartilhada (`contracts/localidades/verificacao/`), via `verificar.sh "java -jar …"`.

**Build**: Maven 3.10 pelo Maven Wrapper (`./mvnw`), que fixa a versão do Maven sem exigir instalação

**Target Platform**: máquina local (macOS, arm64). Escuta em `127.0.0.1`

**Project Type**: web service (API HTTP somente leitura)

**Performance Goals**:

- os mesmos do E1, com pedido atendido pela cópia guardada abaixo de 500 ms (SC-003 do E1);
- partida até o `/health` responder bem abaixo dos 30 s que o `verificar.sh` espera. O tempo real é uma das medidas da comparação.

**Constraints**:

- as do E1: prazo total de 10 s, no máximo uma consulta por pedido, validade de 24 h, página de até 500 itens e nenhuma credencial;
- além disso, a mesma configuração `LOCALIDADES_*` (FR-003) e a mesma ordem de nomes do E1 (FR-004).

**Scale/Scope**: o do E1: 27 UFs e 5.571 municípios

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Como o plano atende | Situação |
|---|---|---|
| I. Fontes oficiais primeiro | Mesma fonte e mesma procedência do E1 | ✅ |
| II. Rastreabilidade | `meta` idêntico ao do E1, com `coletado_em` da consulta original no mesmo formato. O formato da data é conferido pela suíte (regex do contrato) | ✅ |
| III. Verificar antes de afirmar | A comparação só afirma o que mede, com método e data (FR-006 e FR-008). As versões escolhidas foram conferidas no Homebrew e no Maven Central em 2026-11-27 | ✅ |
| IV. Testes sem rede | WireMock em loopback, fixtures do repositório e verificação em sandbox sem rede externa (`./mvnw -o`) | ✅ |
| V. Resiliência | Prazo total com `orTimeout`, erros de domínio, cópia vencida e consulta compartilhada inclusive na falha | ✅ |
| VI. Contrato como fronteira | Mesmo `openapi.yaml`. Nenhum código é compartilhado com o E1, só o contrato, as fixtures e a suíte. Sem geração de OpenAPI pelo framework | ✅ |
| VII. Privacidade | Sem dados pessoais. O registro não guarda IP | ✅ |
| VIII. Cautela jurídica e financeira | Não se aplica | n/a |
| IX. Segredos fora do código | Nenhuma credencial | ✅ |
| X. Simplicidade | Um serviço e uma dependência de framework. Sem banco, Redis nem Docker. O actuator entra só para as métricas, com todos os endpoints dele desligados | ✅ (ver Complexity Tracking) |

**Linguagens (Additional Constraints)**: a constituição pede "JDK de suporte longo, versão a confirmar no E4". Escolha: **JDK 25**, o LTS mais recente (R1).

**Reavaliação pós-design (Fase 1)**: o desenho não acrescenta comportamento nem dependência além das listadas, e o contrato não muda. A única mudança na suíte compartilhada é um cenário novo de paridade de ordenação, que também precisa passar contra o E1 (FR-002). **Gate: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/003-localidades-java/
├── spec.md              # E4: referência à spec do E1 + US6 (comparação)
├── plan.md              # este arquivo
├── research.md          # decisões R1–R14 do Java e método de comparação
├── data-model.md        # mapeamento das entidades do E1 para tipos Java
├── quickstart.md        # setup do JDK, testes, verificação, comparação
├── contracts/
│   └── README.md        # aponta para o contrato compartilhado
├── checklists/
│   └── requirements.md
├── tasks.md             # /speckit-tasks
└── RESULTS.md           # fechamento e comparação com o E1
```

### Source Code (repository root)

```text
experiments/java/localidades/                          # E4
├── pom.xml                                            # Spring Boot 4.1.3, Java 25, finalName "localidades"
├── mvnw, mvnw.cmd, .mvn/wrapper/                      # Maven Wrapper (Maven 3.10)
├── .java-version                                      # 25
├── README.md
└── src/
    ├── main/
    │   ├── java/io/github/danhenriquex/brasilaberto/localidades/
    │   │   ├── LocalidadesApplication.java            # main
    │   │   ├── config/Configuracao.java               # record @ConfigurationProperties("localidades"), validado
    │   │   ├── dominio/                               # records (Uf, Municipio, ...), Dobra, Paginacao, Validacao, UfsOficiais — sem Spring
    │   │   ├── erros/                                 # ErroDominio e subclasses (tipo, título, status)
    │   │   ├── fonte/ClienteIbge.java                 # HttpClient.sendAsync + orTimeout, classificação, normalização
    │   │   ├── cache/CacheComValidade.java            # ConcurrentHashMap + consulta compartilhada (CompletableFuture)
    │   │   ├── servico/ServicoLocalidades.java        # casos de uso — sem Spring Web
    │   │   ├── api/                                   # controllers v1, envelope, ProblemDetail (@RestControllerAdvice)
    │   │   └── operacao/                              # /health, /metrics, filtro de correlação, registro JSON, métricas
    │   └── resources/application.properties           # LOCALIDADES_* → localidades.*, server.*, logs
    └── test/java/io/github/danhenriquex/brasilaberto/localidades/
        ├── dominio/ ...                               # unidade
        ├── fonte/ ...                                 # WireMock
        ├── cache/ ...                                 # concorrência, cópia vencida
        └── api/ ...                                   # MockMvc + WireMock (integração)

contracts/localidades/verificacao/tests/              # compartilhado: + cenário de paridade de ordenação (passa no E1 e no E4)
docs/roteiro.md                                       # E4 antecipado para logo depois do E1
```

**Structure Decision**:

- **Onde fica:** um projeto Maven em `experiments/java/localidades/`, ao lado do E1, conforme a estrutura do repositório.
- **Pacotes:** espelham as camadas do E1 (`dominio`, `fonte`, `cache`, `servico`, `api`, `operacao`). Assim a comparação de código é direta, e `dominio` e `servico` não dependem do Spring Web (portas e adaptadores, como no E1).
- **Nome do pacote:** usa o domínio do GitHub (`io.github.danhenriquex`), a convenção Java para projetos sem domínio próprio.
- **Recursos compartilhados:** fixtures e contrato são lidos de `contracts/localidades/`, sem cópia.

## Complexity Tracking

| Item | Por que é necessário | Alternativa mais simples rejeitada porque |
|---|---|---|
| `spring-boot-starter-actuator`, com todos os endpoints dele desligados | Dá a autoconfiguração do Micrometer com o registro do Prometheus. O `/metrics` e o `/health` são controllers próprios, para cumprir o contrato (o `/health` do actuator responde `{"status":"UP"}`, e o contrato exige `{"status":"ok"}`) | Montar o `PrometheusMeterRegistry` à mão é possível, mas foge do uso comum do Spring, que é justamente o que o E4 quer avaliar |
| Spring Boot como framework | O E4 mede a ergonomia do caminho mais comum no mercado Java, assim como o FastAPI no Python | Javalin ou JDK puro dariam um serviço menor, mas a comparação perderia relevância prática (R2) |

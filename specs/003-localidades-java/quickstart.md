# Quickstart: E4 — Serviço de localidades (IBGE), em Java

Guia de validação ponta a ponta. As rotas e os formatos estão em [contracts/localidades/openapi.yaml](../../contracts/localidades/openapi.yaml), e o mapeamento para Java, em [data-model.md](data-model.md). Todos os comandos partem da raiz do repositório.

## Pré-requisitos

- **JDK 25** (Temurin): `brew install --cask temurin@25`. Confira com `java -version`; deve aparecer `25.0.x`.
- **Maven:** não precisa instalar, vem pelo wrapper `./mvnw`.
- **Suíte de caixa-preta:** usa o `uv`, como no E1 (`uv sync --project contracts/localidades/verificacao`).

```bash
cd experiments/java/localidades && ./mvnw -q package && cd -
```

A primeira execução baixa as dependências para `~/.m2`.

## 1. Testes da implementação (sem rede externa)

```bash
(cd experiments/java/localidades && ./mvnw -q test)
```

**Esperado**: todos passam. O IBGE é simulado com WireMock em loopback.

## 2. Verificação de caixa-preta (o mesmo critério do E1)

```bash
contracts/localidades/verificacao/verificar.sh "java -jar experiments/java/localidades/target/localidades.jar"
```

**Esperado**: todos os cenários passam, os mesmos que passam no E1, mais o de paridade de ordenação.

Rode também contra o E1 para conferir a paridade:

```bash
contracts/localidades/verificacao/verificar.sh "uv run --project experiments/python/localidades localidades"
```

## 3. Sem rede externa (SC-004)

```bash
P='(version 1)(allow default)(deny network*)(allow network* (local ip "localhost:*"))(allow network* (remote ip "localhost:*"))'
sandbox-exec -p "$P" sh -c 'cd experiments/java/localidades && ./mvnw -o -q test'
UV_OFFLINE=1 sandbox-exec -p "$P" contracts/localidades/verificacao/verificar.sh "java -jar experiments/java/localidades/target/localidades.jar"
```

**Esperado**: as duas execuções passam, e um `curl` ao IBGE dentro do mesmo sandbox falha.

## 4. Execução real contra o IBGE (manual)

```bash
java -jar experiments/java/localidades/target/localidades.jar   # 127.0.0.1:8000
```

Use os mesmos `curl` do [quickstart do E1, §4](../002-servico-localidades/quickstart.md). As respostas devem ser equivalentes. Só o `coletado_em` e o `X-Correlation-Id` mudam.

## 5. Comparação com o E1 (US6)

Siga o método do [research.md, R13](research.md):

- mesma máquina e mesmo dia;
- cache de dependências populado;
- mediana de 3 execuções.

Preencha a tabela do `RESULTS.md` do E4 com as 9 medidas para as duas implementações. A nota qualitativa (FR-007) é escrita durante a implementação.

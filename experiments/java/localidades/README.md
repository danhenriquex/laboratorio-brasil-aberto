# E4 — Serviço de localidades (IBGE), em Java

**Pergunta do experimento:** como é construir e operar o mesmo serviço de localidades em Java, do setup aos testes e ao cumprimento do mesmo contrato, comparado ao E1 em Python?

É o mesmo serviço do E1 (`experiments/python/localidades/`), com o mesmo contrato: [`contracts/localidades/openapi.yaml`](../../../contracts/localidades/openapi.yaml). Foi feito com Java 25 (LTS), Spring Boot 4.1 (Spring MVC em threads virtuais), o `HttpClient` da JDK e o Micrometer.

## Pré-requisitos

- JDK 25: `brew install --cask temurin@25`. O instalador pede a senha de administrador.
- O Maven vem pelo wrapper (`./mvnw`), então não precisa instalar.

## Como rodar

Todos os comandos partem da raiz do repositório.

```bash
# testes da implementação (sem rede externa; o IBGE é simulado com WireMock)
(cd experiments/java/localidades && ./mvnw -q test)

# empacotar e verificar o contrato com a mesma suíte de caixa-preta do E1
(cd experiments/java/localidades && ./mvnw -q package -DskipTests)
contracts/localidades/verificacao/verificar.sh "java -jar experiments/java/localidades/target/localidades.jar"

# execução real contra o IBGE, em 127.0.0.1:8000
java -jar experiments/java/localidades/target/localidades.jar
```

As variáveis `LOCALIDADES_*` são as mesmas do E1 ([contracts/localidades/README.md](../../../contracts/localidades/README.md)). O roteiro completo está em [`specs/003-localidades-java/quickstart.md`](../../../specs/003-localidades-java/quickstart.md).

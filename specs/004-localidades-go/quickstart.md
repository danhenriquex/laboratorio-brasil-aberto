# Quickstart: E7 — Serviço de localidades (IBGE), em Go

Guia de validação ponta a ponta. As rotas e os formatos estão em [contracts/localidades/openapi.yaml](../../contracts/localidades/openapi.yaml), e o mapeamento para Go, em [data-model.md](data-model.md). Todos os comandos partem da raiz do repositório.

## Pré-requisitos

- **Go 1.27:** `brew install go`. Confira com `go version`; deve aparecer `go1.27.x`.
- **Suíte de caixa-preta:** usa o `uv`, como no E1 e no E4 (`uv sync --project contracts/localidades/verificacao`).

```bash
(cd experiments/go/localidades && go build -o localidades ./cmd/localidades)
```

A primeira execução baixa os módulos para o cache do Go (`go env GOMODCACHE`).

## 1. Testes da implementação (sem rede externa)

```bash
(cd experiments/go/localidades && go vet ./... && go test ./...)
```

**Esperado**: todos passam. O IBGE é simulado com `httptest.Server` em loopback.

## 2. Verificação de caixa-preta (o mesmo critério do E1 e do E4)

```bash
contracts/localidades/verificacao/verificar.sh "experiments/go/localidades/localidades"
```

**Esperado**: os 82 cenários passam, os mesmos do E1 e do E4.

Rode também contra o E1 e o E4 para conferir a paridade, sobretudo se a suíte ganhar algum cenário:

```bash
contracts/localidades/verificacao/verificar.sh "uv run --project experiments/python/localidades localidades"
contracts/localidades/verificacao/verificar.sh "java -jar experiments/java/localidades/target/localidades.jar"
```

## 3. Sem rede externa (SC-004)

```bash
P='(version 1)(allow default)(deny network*)(allow network* (local ip "localhost:*"))(allow network* (remote ip "localhost:*"))'
sandbox-exec -p "$P" sh -c 'cd experiments/go/localidades && GOFLAGS=-mod=mod GOPROXY=off go test -count=1 ./...'
UV_OFFLINE=1 sandbox-exec -p "$P" contracts/localidades/verificacao/verificar.sh "experiments/go/localidades/localidades"
```

**Esperado**: as duas execuções passam, e um `curl` ao IBGE dentro do mesmo sandbox falha. O `-count=1` impede que o Go reaproveite resultados guardados de testes anteriores.

## 4. Configuração inválida (FR-003)

```bash
LOCALIDADES_PRAZO_FONTE_S=Inf experiments/go/localidades/localidades; echo "saída=$?"
```

**Esperado**: o serviço não sobe, mostra `configuração inválida: LOCALIDADES_PRAZO_FONTE_S …` e sai com código diferente de zero. O mesmo vale para `NaN`, `0`, `-1`, `0.0001`, `abc` e URL que não começa com `http`.

## 5. Execução real contra o IBGE (manual)

```bash
experiments/go/localidades/localidades   # 127.0.0.1:8000
```

Use os mesmos `curl` do [quickstart do E1, §4](../002-servico-localidades/quickstart.md). As respostas devem ser equivalentes às do E1 e do E4. Só o `coletado_em` e o `X-Correlation-Id` mudam.

## 6. Comparação entre as três (US6)

Siga o método do [research.md, R15](research.md):

- mesma máquina e mesmo dia, com o E1 e o E4 medidos de novo junto;
- cache de dependências de cada ecossistema já populado;
- mediana de 3 execuções.

Preencha a tabela do `RESULTS.md` do E7 com as 9 medidas para as três implementações. A nota qualitativa (FR-007) é escrita no `ergonomia.md` durante a implementação. A tabela das lições T044 a T050 (FR-009) também vai no `RESULTS.md`.

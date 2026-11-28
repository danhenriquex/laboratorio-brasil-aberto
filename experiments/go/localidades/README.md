# E7 — Serviço de localidades (IBGE), em Go

**Pergunta do experimento:** como é construir e operar o mesmo serviço de localidades em Go, do setup aos testes e ao cumprimento do mesmo contrato, comparado ao E1 (Python) e ao E4 (Java)?

É o mesmo serviço do E1 (`experiments/python/localidades/`) e do E4 (`experiments/java/localidades/`), com o mesmo contrato: [`contracts/localidades/openapi.yaml`](../../../contracts/localidades/openapi.yaml). Foi feito com Go 1.27, quase só com a biblioteca padrão (`net/http`, `encoding/json`, `log/slog`, `testing`). Os únicos módulos externos são o cliente do Prometheus, o `golang.org/x/text` (dobra de texto) e o `golang.org/x/sync` (consulta compartilhada).

## Pré-requisitos

- Go 1.27: `brew install go`. Confira com `go version`.
- Para a suíte de caixa-preta, o `uv`, como no E1 e no E4.

## Como rodar

Todos os comandos partem da raiz do repositório.

```bash
# testes da implementação (sem rede externa; o IBGE é simulado com httptest)
(cd experiments/go/localidades && go vet ./... && go test ./...)

# gerar o binário e verificar o contrato com a mesma suíte de caixa-preta do E1 e do E4
(cd experiments/go/localidades && go build -o localidades ./cmd/localidades)
contracts/localidades/verificacao/verificar.sh "experiments/go/localidades/localidades"

# execução real contra o IBGE, em 127.0.0.1:8000
experiments/go/localidades/localidades
```

As variáveis `LOCALIDADES_*` são as mesmas do E1 e do E4 ([contracts/localidades/README.md](../../../contracts/localidades/README.md)). O roteiro completo está em [`specs/004-localidades-go/quickstart.md`](../../../specs/004-localidades-go/quickstart.md).

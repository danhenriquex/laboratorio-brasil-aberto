# Implementation Plan: E7 — Serviço de localidades (IBGE), em Go

**Branch**: `004-localidades-go` | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-localidades-go/spec.md`, que reaproveita o comportamento de [specs/002-servico-localidades/spec.md](../002-servico-localidades/spec.md)

## Summary

Reimplementar o serviço de localidades do E1 e do E4 em **Go 1.27, quase só com a biblioteca padrão**, cumprindo o mesmo contrato ([contracts/localidades/openapi.yaml](../../contracts/localidades/openapi.yaml)) e passando na mesma suíte de caixa-preta (82 cenários). Depois, comparar as três implementações com as 9 medidas do E4 e a mesma avaliação qualitativa.

O desenho reproduz as decisões já validadas no E1 e no E4:

- prazo total por consulta;
- cópia com validade e cópia vencida em caso de falha;
- consulta compartilhada **inclusive na falha**;
- códigos e siglas validados contra o data-model;
- problem+json com URNs;
- métricas e registro com os mesmos nomes.

Desta vez, as lições das convergências do E4 (T044 a T050) entram **no desenho**, e não como correção depois. O FR-009 pede justamente registrar como cada uma se comportou em Go. Detalhes em [research.md](research.md).

## Technical Context

**Language/Version**: Go 1.27.4, a estável mais recente, de 2026-11-10, conferida em go.dev/dl e go.dev/doc/devel/release em 2026-11-27. Instalação com `brew install go`, que traz a mesma 1.27.4. O `go.mod` declara `go 1.27`.

**Primary Dependencies**:

- **HTTP (servidor e cliente):** `net/http`, da biblioteca padrão. Sem framework (R2);
- **JSON:** `encoding/json`, da biblioteca padrão;
- **Registro:** `log/slog`, da biblioteca padrão, com saída JSON;
- **Métricas:** `github.com/prometheus/client_golang` v1.25.0, o cliente oficial do Prometheus;
- **Dobra de texto:** `golang.org/x/text` v0.44.0 (normalização Unicode e *casefold*);
- **Consulta compartilhada:** `golang.org/x/sync` v0.25.0 (`singleflight`).

As versões dos módulos foram conferidas em proxy.golang.org em 2026-11-27.

**Storage**: nenhum. A cópia guardada fica em memória (mapa protegido por `sync.Mutex`), e as fixtures são as mesmas do E1, em `contracts/localidades/fixtures-ibge/`

**Testing**:

- `testing` e `net/http/httptest`, da biblioteca padrão. O `httptest.Server` simula o IBGE em loopback, como o `respx` no E1 e o WireMock no E4. Nenhuma biblioteca de testes externa;
- suíte de caixa-preta compartilhada (`contracts/localidades/verificacao/`), via `verificar.sh "experiments/go/localidades/localidades"`.

**Build**: `go build -o localidades ./cmd/localidades`, que gera um binário único, sem runtime à parte

**Target Platform**: máquina local (macOS, arm64). Escuta em `127.0.0.1`

**Project Type**: web service (API HTTP somente leitura)

**Performance Goals**:

- os mesmos do E1, com pedido atendido pela cópia guardada abaixo de 500 ms (SC-003 do E1);
- partida até o `/health` bem abaixo dos 30 s do `verificar.sh`. O tempo real é uma das medidas da comparação.

**Constraints**:

- as do E1: prazo total de 10 s, no máximo uma consulta por pedido, validade de 24 h, página de até 500 itens e nenhuma credencial;
- a mesma configuração `LOCALIDADES_*`, com as mesmas regras de validação do E4 depois da T049 (FR-003);
- a mesma ordem de nomes do E1 e do E4 (FR-004).

**Scale/Scope**: o do E1: 27 UFs e 5.571 municípios

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Como o plano atende | Situação |
|---|---|---|
| I. Fontes oficiais primeiro | Mesma fonte e mesma procedência do E1 | ✅ |
| II. Rastreabilidade | `meta` idêntico ao do E1, com `coletado_em` da consulta original no mesmo formato, conferido pela suíte | ✅ |
| III. Verificar antes de afirmar | Versões conferidas em go.dev e proxy.golang.org em 2026-11-27. O comportamento do `ServeMux` que importa ao contrato (redirecionamentos) foi lido na documentação oficial e será conferido por teste. A comparação só afirma o que mede | ✅ |
| IV. Testes sem rede | `httptest.Server` em loopback, fixtures do repositório e verificação em sandbox sem rede externa, com `GOFLAGS=-mod=mod GOPROXY=off` depois de popular o cache de módulos | ✅ |
| V. Resiliência | Prazo total com `context.WithTimeout`, erros de domínio, cópia vencida e consulta compartilhada inclusive na falha | ✅ |
| VI. Contrato como fronteira | Mesmo `openapi.yaml`. Nenhum código compartilhado com o E1 nem com o E4, só o contrato, as fixtures e a suíte | ✅ |
| VII. Privacidade | Sem dados pessoais. O registro não guarda IP | ✅ |
| VIII. Cautela jurídica e financeira | Não se aplica | n/a |
| IX. Segredos fora do código | Nenhuma credencial | ✅ |
| X. Simplicidade | Um binário, biblioteca padrão para HTTP, JSON, registro e testes, e três módulos externos pequenos e mantidos pelos próprios projetos Go e Prometheus. Sem banco, Redis nem Docker | ✅ (ver Complexity Tracking) |

**Linguagens (Additional Constraints, constituição 1.1.0)**: Go é permitido, "na versão estável vigente, confirmada na documentação oficial no início de cada experimento e registrada no plano". Escolha: **Go 1.27.4** (R1). É a primeira vez de Go no projeto, e ela entra como experimento, com pergunta, timebox e `RESULTS.md`, reimplementando um serviço que já tem contrato e suíte, como pede a constituição.

**Reavaliação pós-design (Fase 1)**: o desenho não acrescenta comportamento nem dependência além das listadas, e o contrato não muda. A suíte compartilhada só ganha cenários se o E7 revelar um caso novo, e eles precisam passar também no E1 e no E4 (FR-002). **Gate: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/004-localidades-go/
├── spec.md              # E7: referência à spec do E1 + US6 (comparação entre três)
├── plan.md              # este arquivo
├── research.md          # decisões R1–R15 do Go e método de comparação
├── data-model.md        # mapeamento das entidades do E1 para tipos Go
├── quickstart.md        # setup do Go, testes, verificação, comparação
├── contracts/
│   └── README.md        # aponta para o contrato compartilhado
├── checklists/
│   └── requirements.md
├── ergonomia.md         # diário de ergonomia, escrito durante a implementação
├── tasks.md             # /speckit-tasks
└── RESULTS.md           # fechamento e comparação com o E1 e o E4
```

### Source Code (repository root)

```text
experiments/go/localidades/                 # E7
├── go.mod, go.sum                          # módulo; go 1.27
├── README.md
├── cmd/localidades/main.go                 # lê a configuração, monta as peças, sobe o servidor
└── internal/
    ├── config/                             # LOCALIDADES_* lidas e validadas à mão (R11)
    ├── dominio/                            # structs, Dobrar, paginação, validação, UFs oficiais — sem net/http
    ├── erros/                              # ErroDominio (tipo, título, status) e os seis tipos
    ├── fonte/                              # cliente do IBGE: prazo total, classificação, normalização
    ├── cache/                              # cópia com validade + singleflight (consulta compartilhada)
    ├── servico/                            # casos de uso — sem net/http
    ├── api/                                # roteador, handlers v1, envelope, problem+json
    ├── transporte/                         # Ouvinte: saneia a linha do pedido antes do net/http (US2; research R3)
    └── operacao/                           # /health, /metrics, correlação, registro JSON, métricas
    (cada pacote com os seus *_test.go ao lado, como é o costume em Go)

contracts/localidades/verificacao/          # compartilhado: só muda se o E7 revelar caso novo (passa nos três)
specs/003-localidades-java/medicao/         # medir.py estendido para o E7 (US6), ou movido para um lugar comum
```

**Structure Decision**:

- **Onde fica:** um módulo Go em `experiments/go/localidades/`, ao lado do E1 e do E4, conforme a estrutura do repositório (`experiments/<linguagem>/`).
- **Pacotes:** espelham as camadas do E1 e do E4 (`dominio`, `fonte`, `cache`, `servico`, `api`, `operacao`). Ficam em `internal/`, a convenção Go para código que não é biblioteca pública. `dominio` e `servico` não importam `net/http`.
- **Testes:** ficam ao lado do código (`*_test.go`), o costume da linguagem, em vez de uma árvore de testes separada como no E1 e no E4.
- **Módulo:** `github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades`, o caminho do repositório.
- **Recursos compartilhados:** fixtures e contrato são lidos de `contracts/localidades/`, sem cópia.

## Complexity Tracking

| Item | Por que é necessário | Alternativa mais simples rejeitada porque |
|---|---|---|
| `prometheus/client_golang` | É o cliente oficial do Prometheus em Go e dá o formato de exposição correto, com histograma e rótulos | Escrever o formato de texto à mão é possível para 4 métricas, mas foge do caminho comum do ecossistema, que é o que o experimento compara (como o `prometheus-client` no E1 e o Micrometer no E4) |
| `golang.org/x/text` | A biblioteca padrão não tem normalização NFKD nem *casefold*. O `x/text` tem os dois e é mantido pelo projeto Go | Uma tabela manual de acentos daria divergência em casos raros. Com o `cases.Fold()`, o Go fica mais perto do `casefold()` do E1 do que o Java ficou |
| `golang.org/x/sync` (`singleflight`) | Dá a consulta compartilhada por chave, entregando o mesmo resultado, **inclusive o erro**, a todos os pedidos simultâneos | Um mapa de canais com `sync.Mutex` resolve em umas 30 linhas, mas o `singleflight` é a solução idiomática. Usá-lo mostra o ecossistema como ele é, como o `CompletableFuture` no E4 |

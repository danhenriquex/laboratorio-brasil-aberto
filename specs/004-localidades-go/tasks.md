---
description: "Lista de tarefas do E7 — Serviço de localidades (IBGE), em Go"
---

# Tasks: E7 — Serviço de localidades (IBGE), em Go

**Input**: Documentos de design em `specs/004-localidades-go/`. O comportamento vem de `specs/002-servico-localidades/`.

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/localidades/openapi.yaml](../../contracts/localidades/openapi.yaml), [quickstart.md](quickstart.md)

**Tests**: incluídos. O critério de pronto é a suíte de caixa-preta (FR-002), e a constituição (princípio IV) proíbe rede nos testes. Em cada história:

1. escreva os testes da implementação primeiro e confirme que falham;
2. implemente;
3. rode os cenários da história na suíte de caixa-preta contra o binário.

**Referência de comportamento**: o código do E1 (`experiments/python/localidades/src/localidades/`) e o do E4 (`experiments/java/localidades/`) são a referência executável de cada regra. Na dúvida, o comportamento do E1 e a suíte decidem.

**Lições do E4**: as lacunas achadas nas convergências do E4 (T044 a T050) entram aqui como tarefa desde o início, e cada uma é registrada no `RESULTS.md` (FR-009).

**Organization**: tarefas agrupadas por história de usuário. Cada fase vira **uma branch e um PR**, e a próxima só começa depois do merge da anterior.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: história de usuário: US1 a US5, as do E1, e US6, a comparação

## Path Conventions

- **Projeto:** `experiments/go/localidades/`, chamado de **`G/`** abaixo.
- **Pacotes:** `G/internal/<pacote>/`, com os testes ao lado (`*_test.go`).
- **Módulo:** `github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades`.
- **Comandos:**
  - testes: `(cd experiments/go/localidades && go vet ./... && go test ./...)`;
  - binário: `(cd experiments/go/localidades && go build -o localidades ./cmd/localidades)`;
  - caixa-preta: `contracts/localidades/verificacao/verificar.sh "experiments/go/localidades/localidades" [-k filtro]`, a partir da raiz.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Go, módulo, dependências fixadas e diário de ergonomia.

- [ ] T001 Instalar o Go com `brew install go`, **depois de confirmação do usuário** (é uma mudança no sistema). Conferir com `go version`, que deve mostrar `go1.27.x`, e registrar a versão exata e o tempo gasto em `specs/004-localidades-go/ergonomia.md`.
- [ ] T002 Criar o módulo em `G/` com `go mod init github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades`, declarar `go 1.27` no `G/go.mod` e fixar as dependências do research com `go get`:
  - `github.com/prometheus/client_golang@v1.25.0`;
  - `golang.org/x/text@v0.44.0`;
  - `golang.org/x/sync@v0.25.0`.

  Versionar `G/go.mod` e `G/go.sum`. Acrescentar ao `.gitignore` da raiz o binário `experiments/go/localidades/localidades`.
- [ ] T003 [P] Criar `G/README.md`, espelhando o README do E4: pergunta do E7, pré-requisitos (Go 1.27), comandos de teste, de verificação e de execução, e links para o quickstart e o contrato. Criar também `specs/004-localidades-go/ergonomia.md`, o diário do FR-007, com uma seção por ponto (setup, testes, contrato, erros e métricas) e uma seção "Lições do E4" para anotar, à medida que aparecerem, os comportamentos das convergências T044 a T050.
- [ ] T004 Criar `G/cmd/localidades/main.go` mínimo, que sobe um `http.Server` em `127.0.0.1:8000` com `GET /health` devolvendo `{"status":"ok"}`. Rodar `go build` e confirmar que compila e responde. Esse arquivo é substituído pela montagem completa na T015.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: domínio, configuração, erros, cliente do IBGE e base HTTP, já com as regras de caminho, método e formato que no E4 custaram convergências.

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

### Testes da fundação (escrever primeiro)

- [ ] T005 [P] Criar o apoio de testes em `G/internal/testeapoio/`:
  - `fixtures.go`: localiza a raiz do repositório subindo até achar `contracts/localidades` e lê `contracts/localidades/fixtures-ibge/*.json`;
  - `relogio.go`: um relógio falso com instante inicial `2026-11-26T12:00:00.123Z`, uma fonte monotônica e `Avancar(time.Duration)`;
  - `ibge.go`: um `httptest.NewServer` em `127.0.0.1`, que serve as fixtures por caminho, conta os pedidos por caminho e permite simular atraso, status e corpo. Nenhum teste fala com host externo.
- [ ] T006 [P] Escrever `G/internal/dominio/dominio_test.go`, em tabela, com os mesmos casos do `test_dominio.py` do E1 e do `DominioTest.java` do E4:
  - **`Dobrar`:** `"Niterói"` dá `"niteroi"`, `"SÃO"` dá `"sao"`, e o apóstrofo é mantido;
  - **ordenação** por `(Dobrar(nome), codigo)`;
  - **`FiltrarPorNome`;**
  - **`Paginar`:** `paginas = ceil(total/itens)`, total 0 dá `paginas` 0, e página além do fim devolve vazio com o total;
  - **`ResolverUF`:** `" rj "` e `"33"` resolvem para `"33"`; `"XX"` e `"99"` dão `NaoEncontrado`; `"R1"`, `"123"` e `""` dão `EntradaInvalida`;
  - **`ValidarCodigoMunicipio`:** exige "`^\d{7}$`" só com dígitos ASCII, e `"330455７"` é recusado;
  - **`ValidarPaginacao`:** "inteiro de 1 a `ITENS_MAX` (padrão 500)" para `itens`, com o limite citado na mensagem, e `pagina` como `int64` (data-model);
  - **`ValidarNome`:** "aparado; de 2 a 60 caracteres".
- [ ] T007 [P] Escrever `G/internal/config/config_test.go`, cobrindo:
  - os padrões do R14 do E1: `127.0.0.1`, `8000`, a URL do IBGE, `10`, `86400` e `500`;
  - a leitura pelas variáveis `LOCALIDADES_*` e a URL sem barra final;
  - a recusa, com erro cuja mensagem cita a variável e o valor recebido, de: `abc`, `0`, `-1`, `NaN`, `Inf`, `infinity`, `1e300` e `0.0001` em prazo e validade (lição da **T049**: "número finito entre 0,001 e 10⁹"); `0` e `1.5` em `LOCALIDADES_ITENS_MAX`; `ftp://ibge` em `LOCALIDADES_IBGE_URL`; e `abc` em `LOCALIDADES_PORTA`;
  - a aceitação dos limites `0.001` e `1000000000`.
- [ ] T008 [P] Escrever `G/internal/fonte/fonte_test.go` com o IBGE simulado, espelhando o `test_fonte_ibge.py` do E1:
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
  - **Formato exato (T048 e T049 do E1):** id de 5 dígitos na lista de municípios, UF com id `1` e região imediata com 5 dígitos dão `RespostaInesperadaDaFonte`; siglas `rj`, `Norte` (região) e `R J` também.
  - **Demais garantias:** exatamente 1 pedido por chamada e o `User-Agent` do laboratório.

### Implementação da fundação

- [ ] T009 [P] Implementar `G/internal/erros/erros.go`: `ErroDominio` (`Tipo`, `Titulo`, `Detalhe`, `Status`, método `Error()` e `URN()` = `urn:brasil-aberto:problema:` + tipo), os seis construtores com os títulos e status do E1 (`EntradaInvalida` 400, `NaoEncontrado` 404, `FonteIndisponivel` 502, `FonteLenta` 504, `RespostaInesperadaDaFonte` 502, `ErroInterno` 500) e `DeFonte()`.
- [ ] T010 Implementar `G/internal/dominio/` conforme o `data-model.md` do E7, sem importar `net/http`:
  - as *structs* das entidades com as *tags* JSON do contrato;
  - `UFsOficiais`, com os 27 códigos e siglas;
  - `Dobrar`: cadeia `transform.Chain(norm.NFKD, runes.Remove(runes.In(unicode.Mn)), cases.Fold())` (research R9);
  - `Paginacao` (`Pagina int64`) e `Paginar`;
  - `ResolverUF`, `ValidarCodigoMunicipio`, `ValidarPaginacao` e `ValidarNome`, com expressões só ASCII.

  Ao final, T006 passa.
- [ ] T011 Implementar `G/internal/config/config.go` conforme o research R11: `Carregar(getenv func(string) string) (Configuracao, error)`, com `strconv`, os padrões do E1 e as regras de validação, recusando explicitamente `NaN` e infinito (`math.IsNaN`, `math.IsInf`). A mensagem segue o formato do E1: `configuração inválida: LOCALIDADES_X precisa …, recebi '…'`. Ao final, T007 passa.
- [ ] T012 Implementar `G/internal/fonte/ibge.go`:
  - **Cliente:** `http.Client` sem redirecionamento (`CheckRedirect` que devolve `http.ErrUseLastResponse`) e com o `User-Agent` `laboratorio-brasil-aberto-localidades/0.1.0`;
  - **Prazo total:** `context.WithTimeout(prazo)` cobrindo conexão, cabeçalhos e `io.ReadAll` do corpo;
  - **Classificação:** a do research R6, com `errors.Is(err, context.DeadlineExceeded)` para o prazo;
  - **Normalização:** pelas regras do E1, com quantidade **exata** de dígitos e siglas `^[A-Z]{2}$` e `^[A-Z]{1,2}$`;
  - **Medição:** chama uma função `func(recurso string, segundos float64)` a cada consulta;
  - **Mensagens de erro:** nunca contêm o corpo do IBGE.

  Ao final, T008 passa.
- [ ] T013 Implementar a base HTTP em `G/internal/api/` e `G/internal/operacao/`, e escrever `G/internal/api/base_test.go`, espelhando o `test_api_base.py` do E1 e o `ApiBaseTest.java` do E4:
  - **`operacao/correlacao.go`:** aceita `^[A-Za-z0-9._-]{1,64}$` ou gera um UUID v4 com `crypto/rand`, e guarda o valor no `context.Context` do pedido;
  - **`api/problema.go`:** escreve `application/problem+json` com `type` URN, `title`, `status`, `detail` e `correlacao_id`; um erro que não é `ErroDominio` vira 500 `erro-interno` com `detail` genérico;
  - **`api/roteador.go`, o handler de topo (research R3):**
    1. aplica a correlação e escreve o cabeçalho `X-Correlation-Id` em toda resposta;
    2. recupera `panic` e responde 500 `erro-interno`;
    3. caminho cru (`URL.EscapedPath()`) com `;`, segmentos `.` ou `..` ou barras repetidas → 404 `nao-encontrado` direto, **sem redirecionamento** (lições da **T050** e da normalização do `ServeMux`);
    4. `mux.Handler(pedido)` com padrão vazio ("page not found" ou "method not supported") → 404 `nao-encontrado`, inclusive para `TRACE`, sem ecoar nada (lição da **T047**);
    5. guarda o padrão da rota, sem o método, para o rótulo `rota` das métricas;
  - **`operacao/saude.go`:** `GET /health` devolve `{"status":"ok"}` em `application/json`;
  - **o que o teste cobre:**
    - 404 em problem+json para `/v2/ufs`, `/ufs`, `/nada` e `/v1`;
    - `POST /health`, `TRACE /health` e `DELETE /health` dão 404, e o `TRACE` não ecoa cabeçalhos;
    - `//health`, `/./health`, `/x/../health` e `/health;x` dão 404, e não 301;
    - a correlação volta igual quando válida e é trocada por UUID v4 quando inválida;
    - um `panic` vira 500 sem rastro de execução no corpo;
    - com `Accept: application/xml`, `text/plain` e `application/problem+json`, o `/health` responde 200 em `application/json` (lição da **T048**).
- [ ] T014 Implementar a base de `G/internal/servico/servico.go`, sem importar `net/http`:
  - **`Meta`:** `fonte`, `url_fonte`, `url_documentacao` e `coletado_em`, formatado com o *layout* `2006-01-02T15:04:05.000Z07:00` em UTC (data-model). Um teste em `G/internal/servico/meta_test.go` confere que um instante com 0 ms sai como `.000Z`;
  - **`obter(ctx, chave, buscar)`:** nesta fase, chama a fonte direto. A cópia guardada entra na T027.
- [ ] T015 Substituir o `G/cmd/localidades/main.go` pela montagem completa: carrega a configuração (com erro → mensagem em stderr e `os.Exit(2)`), monta cliente, serviço, métricas e roteador, e sobe o `http.Server` em `LOCALIDADES_HOST:LOCALIDADES_PORTA`, com `ReadHeaderTimeout` definido. Gerar o binário e rodar `verificar.sh "experiments/go/localidades/localidades" -k "contrato_valido or saude or correlacao"`.

**Checkpoint**: `go test ./...` passa (domínio, configuração, cliente e base HTTP), e o binário sobe e responde `/health` pelo `verificar.sh`.

---

## Phase 3: User Story 1 - Listar estados e os municípios de um estado (Priority: P1) 🎯 MVP

**Goal**: `GET /v1/ufs`, `GET /v1/ufs/{uf}` e `GET /v1/ufs/{uf}/municipios` (sem o filtro por nome), como na US1 do E1.

**Independent Test**: os cenários de `test_us1_ufs_municipios.py` e `test_paridade_ordenacao.py` (sem as buscas) passam contra o binário.

- [ ] T016 [P] [US1] Escrever `G/internal/api/ufs_test.go` (`httptest` + IBGE simulado), com os casos do `test_api_ufs.py` do E1:
  - 27 UFs ordenadas, com Acre primeiro;
  - `/v1/ufs/rj`, `/v1/ufs/33` e `/v1/ufs/%20RJ%20`;
  - `XX` e `99` dão 404, e `R1` dá 400, os três sem chamar o IBGE;
  - RJ com 92 municípios, `paginacao {1, 100, 92, 1}` e Angra dos Reis primeiro;
  - `itens=10&pagina=10` devolve 2 itens, e uma página além do fim devolve vazio;
  - `itens=0`, `itens=501` e `pagina=0` dão 400, com o limite citado no `detail`;
  - **lições da T045:** `pagina=99999999999` e `pagina=` com 30 dígitos dão 200 com a lista vazia; `itens=10&itens=20` vale `20`;
  - **lição da T046:** `?itens=%ZZ` e `?pagina=%E3` dão 400 `entrada-invalida`, e nunca 500;
  - **lição da T048:** com `Accept: application/xml`, `/v1/ufs` responde 200 em `application/json`;
  - **lição da T050:** `/v1/ufs;jsessionid=x` e `/v1/ufs/RJ;x=1/municipios` dão 404 sem consultar o IBGE;
  - JSON sem `<` nem `&` (`SetEscapeHTML(false)`) e `paginacao` ausente em `/v1/ufs/{uf}`.
- [ ] T017 [US1] Em `G/internal/servico/servico.go`, implementar `ListarUFs`, `ObterUF` (uma UF da tabela ausente no IBGE vira `RespostaInesperadaDaFonte`) e `ListarMunicipios(ctx, uf, pagina, itens)` (validar, resolver, buscar, ordenar e paginar).
- [ ] T018 [US1] Criar `G/internal/api/ufs.go` com as três rotas e o envelope `Resposta[T]` (data-model), e `G/internal/api/query.go` com a leitura da *query* do research R4: `url.ParseQuery(RawQuery)` com erro → 400; valor que não é UTF-8 válido → 400; parâmetro repetido vale o **último**; `pagina` só com dígitos que estoura `int64` conta como além do fim. Registrar as rotas no `ServeMux` com padrões de método (`GET /v1/ufs/{uf}/municipios`). Ao final, T016 passa.
- [ ] T019 [US1] Rodar `verificar.sh "experiments/go/localidades/localidades" -k "us1 or paridade or contrato_valido"` e registrar no diário de ergonomia o que exigiu ajuste para cumprir o contrato.

**Checkpoint**: US1 verificada pela mesma suíte do E1 e do E4. É o MVP do E7.

---

## Phase 4: User Story 2 - Consultar um município pelo código oficial (Priority: P1)

**Goal**: `GET /v1/municipios/{codigo}`.

**Independent Test**: `test_us2_municipio.py` passa contra o binário.

- [ ] T020 [P] [US2] Escrever `G/internal/api/municipio_test.go`, com os casos do `test_api_municipio.py` do E1: Rio de Janeiro (`3304557`) com UF e regiões; `9999999` dá 404 com o `detail` do E1; `12ab`, `123456`, `12345678` e `330455７` dão 400 sem chamar o IBGE; `3545803` (nome com apóstrofo) sai sem escape; e, como lição da **T044**, `/v1/municipios/%ZZ` e `/v1/municipios/%2F` dão 400 ou 404 em problem+json com correlação, nunca HTML.
- [ ] T021 [US2] Em `G/internal/servico/servico.go`, implementar `ObterMunicipio(ctx, codigo)`.
- [ ] T022 [US2] Criar `G/internal/api/municipios.go` com `GET /v1/municipios/{codigo}`. Ao final, T020 passa.
- [ ] T023 [US2] Rodar `verificar.sh "experiments/go/localidades/localidades" -k us2` e registrar observações no diário.

---

## Phase 5: User Story 3 - Comportamento previsível quando o IBGE falha ou demora (Priority: P2)

**Goal**: cópia guardada com validade, consulta compartilhada **inclusive na falha** e cópia vencida em caso de falha.

**Independent Test**: `test_us3_falhas.py` passa contra o binário, inclusive o cenário "pedidos simultâneos com a fonte travada não fazem fila".

- [ ] T024 [P] [US3] Escrever `G/internal/cache/cache_test.go` com o relógio falso, espelhando o `test_cache.py` do E1: acerto dentro da validade; falta depois dela; cópia vencida devolvida como `desatualizado` quando a fonte falha; "não encontrado" e erros não guardados; e, com `-race`, 20 pedidos simultâneos para a mesma chave geram **uma** consulta e recebem o mesmo resultado, **inclusive o mesmo erro**.
- [ ] T025 [P] [US3] Escrever `G/internal/api/falhas_test.go`, espelhando o `test_api_falhas.py` do E1: fonte fora dá 502 `fonte-indisponivel`; fonte lenta dá 504 `fonte-lenta` dentro do prazo; resposta inválida dá 502 `resposta-inesperada-da-fonte`; com cópia vencida, a resposta é 200 com `desatualizado: true` e o `coletado_em` original; e um pedido cujo cliente desiste não cancela a consulta dos outros (research R7).
- [ ] T026 [US3] Implementar `G/internal/cache/cache.go` conforme o research R7: `map[string]guardada` com `sync.Mutex`, `singleflight.Group` com `DoChan`, consulta num contexto próprio com o prazo da fonte, `select` no contexto de cada pedido, e relógios injetáveis. Ao final, T024 passa com `go test -race`.
- [ ] T027 [US3] Em `G/internal/servico/servico.go`, trocar o `obter` para usar o cache. O `meta` vem da entrada (`coletado_em` original e `desatualizado`), e o resultado da cópia (`acerto`, `falta`, `desatualizado`) fica disponível para as métricas e o registro. Ao final, T025 passa.
- [ ] T028 [US3] Rodar `verificar.sh "experiments/go/localidades/localidades" -k us3` e registrar no diário como foi implementar a consulta compartilhada em Go, comparada ao `asyncio` do E1 e ao `CompletableFuture` do E4.

---

## Phase 6: User Story 4 - Encontrar um município pelo nome dentro de um estado (Priority: P3)

**Goal**: o parâmetro `nome` em `GET /v1/ufs/{uf}/municipios`.

**Independent Test**: `test_us4_busca.py` e as buscas de `test_paridade_ordenacao.py` passam contra o binário.

- [ ] T029 [P] [US4] Escrever `G/internal/api/busca_test.go`, espelhando o `test_api_busca.py` do E1: `niteroi` e `NITERÓI` acham Niterói; `são` em SP traz vários, em ordem e paginados; termo sem resultado dá lista vazia com `paginas` 0; `a`, `"  a  "` e `""` dão 400 sem consultar; 61 caracteres dão 400 citando 60; duas buscas na mesma UF fazem uma consulta só; e, como lição da **T046**, `nome=%ZZ`, `nome=s%E3o` e `nome=%`, enviados crus num `httptest.Server`, dão 400 `entrada-invalida`.
- [ ] T030 [US4] Acrescentar o `nome` opcional a `ListarMunicipios` em `G/internal/servico/servico.go` (validar, filtrar, ordenar e paginar) e ao handler de `G/internal/api/ufs.go`. Ao final, T029 passa.
- [ ] T031 [US4] Rodar `verificar.sh "experiments/go/localidades/localidades" -k "us4 or paridade"`.

---

## Phase 7: User Story 5 - Saber se o serviço está saudável e como está sendo usado (Priority: P3)

**Goal**: métricas com os nomes do contrato, registro JSON por pedido e correlação verificada de fora.

**Independent Test**: `test_us5_operacao.py` passa contra o binário, e a suíte inteira também.

- [ ] T032 [P] [US5] Escrever `G/internal/operacao/operacao_test.go`, espelhando o `test_api_operacao.py` do E1: o `/metrics` expõe `localidades_pedidos_total{rota,status}`, `localidades_erros_total{tipo}`, `localidades_cache_total{resultado}` e `localidades_fonte_duracao_segundos_bucket{recurso}` com as faixas do E1; rota inexistente conta como `rota="nao-encontrado"`; o `/metrics` responde `text/plain` com qualquer `Accept`; e cada pedido gera uma linha JSON com `momento`, `nivel`, `correlacao_id`, `metodo`, `rota`, `status`, `duracao_ms`, `cache` e `fonte_ms`, sem IP.
- [ ] T033 [P] [US5] Implementar `G/internal/operacao/metricas.go` com o `client_golang`, num `prometheus.NewRegistry()` próprio, com as quatro métricas do research R10 e os coletores de runtime do Go, e o `GET /metrics` com `promhttp.HandlerFor`.
- [ ] T034 [US5] Implementar `G/internal/operacao/registro.go` com `log/slog` (`JSONHandler` e `ReplaceAttr` para os nomes do E1) e integrá-lo ao handler de topo, com um `ResponseWriter` que guarda o status e um valor mutável no contexto para o uso da cópia e o tempo da fonte. Ao final, T032 passa.
- [ ] T035 [US5] Rodar a suíte inteira, `verificar.sh "experiments/go/localidades/localidades"`, e confirmar que **todos** os 82 cenários passam, os mesmos do E1 e do E4 (SC-001).

**Checkpoint**: E7 funcionalmente equivalente ao E1 e ao E4, verificado pela mesma suíte.

---

## Phase 8: User Story 6 - Comparar o E1, o E4 e o E7 com medidas (Priority: P2)

**Goal**: as 9 medidas do FR-006 para as três implementações e a avaliação qualitativa do FR-007, pelo método do research R15.

**Independent Test**: a tabela comparativa do `RESULTS.md` fica preenchida para as três implementações, com data e método.

- [ ] T036 [US6] Criar `specs/004-localidades-go/medicao/medir.py` e `medir.sh` a partir dos do E4 (`specs/003-localidades-java/medicao/`), que ficam como registro do E4, acrescentando o E7: build `go build -o localidades ./cmd/localidades`, suíte `go test -count=1 ./...`, subida pelo binário, artefato = tamanho do binário, linhas `.go` de produção e de `*_test.go`, e dependências diretas = linhas `require` sem `// indirect` no `go.mod`. A tabela de saída passa a ter três colunas.
- [ ] T037 [US6] Rodar o `medir.sh` na mesma máquina e no mesmo dia, com os caches dos três ecossistemas populados, e guardar a saída em `specs/004-localidades-go/medicao/resultado-AAAA-MM-DD.md`.
- [ ] T038 [US6] Consolidar o `specs/004-localidades-go/ergonomia.md` numa nota de 1 a 5 com justificativa para cada ponto do FR-007 (setup, testes, contrato, erros e métricas), para o E7, ao lado das notas do E1 e do E4 registradas no `ergonomia.md` do E4. Toda diferença citada traz a medida e o contexto (FR-008).

---

## Phase 9: Polish & Fechamento do experimento

- [ ] T039 Verificar sem rede externa (SC-004), com o perfil do quickstart §3: `go test -count=1 ./...` com `GOFLAGS=-mod=mod GOPROXY=off` e a suíte de caixa-preta, os dois dentro do sandbox, mais um `curl` ao IBGE que precisa falhar no mesmo sandbox.
- [ ] T040 Fazer a execução real contra o IBGE, conforme o quickstart §5, com o E1, o E4 e o E7 lado a lado recebendo os mesmos pedidos, e comparar os corpos ignorando só o `coletado_em` e a correlação.
- [ ] T041 [P] Acrescentar a `docs/adr/0001-convencoes-comuns-de-api.md` uma seção "Confirmação no E7", com o que a terceira implementação mostrou sobre as convenções (formato de erro, métricas, `coletado_em`, configuração).
- [ ] T042 Escrever `specs/004-localidades-go/RESULTS.md` a partir de `docs/templates/RESULTS.md`, com:
  - a resposta curta à pergunta do E7;
  - a tabela das 9 medidas para as três implementações (US6);
  - a tabela das **lições do E4** (FR-009, SC-006): uma linha para cada uma de T044 a T050, dizendo se o comportamento apareceu em Go e como foi tratado;
  - as limitações, inclusive a ordem de construção (o E7 veio depois do E1 e do E4);
  - as decisões e os próximos passos, com o E8 (Rust) na sequência do roteiro.
- [ ] T043 [P] Atualizar `docs/roteiro.md` com a data de conclusão do E7 e conferir que `CLAUDE.md` e o `README.md` da raiz citam `experiments/go/`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1):** sem dependências. A T001 depende da confirmação do usuário.
- **Fundação (Fase 2):** depende do Setup e bloqueia todas as histórias.
- **US1 e US2 (Fases 3 e 4):** dependem da Fundação. A US2 não depende da US1, mas a ordem de entrega segue a prioridade.
- **US3 (Fase 5):** depende da Fundação. Troca o `obter` do serviço, então vem depois da US1 e da US2 para não conflitar no mesmo arquivo.
- **US4 (Fase 6):** depende da US1 (o mesmo handler e o mesmo serviço).
- **US5 (Fase 7):** depende da Fundação. Fecha a suíte inteira, por isso vem depois das outras histórias.
- **US6 (Fase 8):** depende de a suíte inteira passar (T035).
- **Fechamento (Fase 9):** depende de todas.

### Ordem de entrega (uma branch e um PR por fase, esperando cada merge)

1. Setup + Fundação (T001–T015)
2. US1 (T016–T019) — MVP
3. US2 (T020–T023)
4. US3 (T024–T028)
5. US4 (T029–T031)
6. US5 (T032–T035)
7. US6 (T036–T038)
8. Fechamento (T039–T043)

### Parallel Opportunities

- Na Fundação, os testes T005 a T008 e o pacote de erros (T009) tocam arquivos diferentes.
- Em cada história, o teste [P] pode ser escrito enquanto a fase anterior está em revisão, sem commit antes do merge dela.
- Na US5, métricas (T033) e o teste (T032) são independentes.
- No Fechamento, ADR (T041) e roteiro (T043) são independentes.

## Parallel Example: Foundational

```text
T006 dominio_test.go   T007 config_test.go   T008 fonte_test.go   T009 erros.go
        ↓                      ↓                     ↓
T010 dominio           T011 config           T012 fonte
                         ↓
              T013 base HTTP → T014 serviço → T015 main.go
```

## Implementation Strategy

### MVP First

Setup, Fundação e US1 entregam um serviço que lista UFs e municípios e passa nos cenários da US1 e da paridade. Já é comparável com o E1 e o E4 nesse recorte.

### Incremental Delivery

Cada história acrescenta um grupo de cenários da suíte. A US5 fecha os 82 cenários (SC-001), a US6 entrega a comparação entre as três, e o Fechamento confirma sem rede, contra o IBGE real, e registra as lições do E4 (FR-009).

## Notes

- O `tasks.md` é a fonte da verdade. As issues do board espelham as fases.
- Nenhum teste fala com a rede externa: o IBGE é sempre o `httptest.Server` em loopback ou o IBGE falso da suíte.
- `go vet ./...` e `gofmt -l .` sem saída fazem parte do "testes passam" de cada fase.
- Se a implementação em Go revelar um caso novo que a suíte não cobre, o cenário entra na suíte compartilhada e precisa passar no E1 e no E4 (FR-002).

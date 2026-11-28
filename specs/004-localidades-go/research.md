# Research: E7 — Serviço de localidades (IBGE), em Go

**Data**: 2026-11-27 | **Spec**: [spec.md](spec.md) | **Plano**: [plan.md](plan.md)

As decisões de **comportamento** e de contrato são as do E1 ([specs/002-servico-localidades/research.md](../002-servico-localidades/research.md)), e estas não as repetem:

| Decisão do E1 | Assunto |
|---|---|
| R1 | comportamento real do IBGE |
| R4 | caixa-preta e IBGE falso |
| R5 | cópia guardada |
| R6 | prazo e classificação das falhas |
| R7 | códigos como texto |
| R8 | dobra e ordenação |
| R9 | paginação |
| R10 | envelope e `meta` |
| R11 | erros |
| R12 | observabilidade |
| R14 | configuração |

O método de comparação é o do E4 ([specs/003-localidades-java/research.md](../003-localidades-java/research.md), R13), estendido para três implementações.

Abaixo está o "como" em Go. As versões foram conferidas em 2026-11-27 em go.dev/dl, go.dev/doc/devel/release e proxy.golang.org.

## R1. Versão do Go

- **Decision**: **Go 1.27.4**, instalado com `brew install go`. O `go.mod` declara `go 1.27`.
- **Rationale**:
  - go.dev/dl lista como estáveis a `go1.27.4` e a `go1.26.11`. A 1.27.0 saiu em 2026-08-19, e a 1.27.4 em 2026-11-10;
  - a política oficial diz: "Each major Go release is supported until there are two newer major releases". A 1.27 tem o maior tempo de suporte pela frente;
  - a constituição 1.1.0 pede a versão estável vigente, confirmada na documentação oficial.
- **Alternatives considered**: Go 1.26, também suportada, mas sem motivo para começar um projeto novo numa versão mais velha.
- **Situação do ambiente**: a máquina não tem Go. A instalação é a primeira tarefa e pede confirmação do usuário, como foi com o JDK no E4.

## R2. Servidor HTTP: biblioteca padrão, sem framework

- **Decision**: `net/http`, com o `ServeMux` da biblioteca padrão e os padrões com método e curinga (`GET /v1/ufs/{uf}/municipios`), existentes desde o Go 1.22. Sem Gin, Echo ou Chi.
- **Rationale**:
  - em Go, o caminho mais comum para um serviço pequeno é a própria biblioteca padrão. Desde o Go 1.22, o roteador dela tem método e curinga, que eram o motivo de usar um framework. É o equivalente, no ecossistema Go, ao FastAPI no Python e ao Spring no Java;
  - cada pedido roda numa *goroutine*, então o código bloqueante fica simples e concorrente sem nada a configurar, como as threads virtuais do E4.
- **Alternatives considered**:
  - Gin ou Echo: populares, mas trazem convenções próprias de erro e de JSON que o contrato teria de contornar. O E4 mostrou o custo disso;
  - Chi: leve e compatível com `net/http`, mas o roteador padrão já cobre as quatro rotas.

## R3. Roteamento e as lições das convergências do E4

O `ServeMux` tem comportamentos padrão que divergem do contrato. Pela documentação oficial (pkg.go.dev/net/http#ServeMux):

- "redirecting any request containing . or .. segments or repeated slashes to an equivalent, cleaner URL";
- o redirecionamento da barra no fim só existe para padrões registrados com barra no fim. As rotas do contrato não têm barra no fim;
- "If there is no registered handler that applies to the request, Handler returns a "page not found" or "method not supported" handler and an empty pattern". A documentação não diz o status do "method not supported". O comportamento conhecido é 405 com `Allow`, que **será conferido por teste**;
- "A pattern with the method GET matches both GET and HEAD requests".

- **Decision**: um handler de topo, escrito por nós, decide antes do `ServeMux`:
  1. caminho com `;`, segmentos `.` ou `..`, ou barras repetidas → 404 `nao-encontrado` direto, sem passar pelo `ServeMux`. Isso evita o redirecionamento e já cobre a lição da **T050** (parâmetros de caminho);
  2. senão, `mux.Handler(pedido)`. Se o padrão vier vazio ("page not found" ou "method not supported"), a resposta é o 404 `nao-encontrado` em problem+json, como no E1. Isso cobre a lição da **T047**: `TRACE` e qualquer método não suportado caem aqui, e nada é ecoado;
  3. senão, o handler da rota, com o padrão guardado para o rótulo `rota` das métricas.
- **HEAD:** fica como no E4 (aceito, pela regra do `ServeMux`), uma divergência já registrada no RESULTS do E4.
- **Rationale**: no E4, cada uma dessas lições custou uma rodada de convergência. Aqui elas viram regra explícita, num lugar só, e a suíte (que já tem os cenários) confere.
- **Alternatives considered**: deixar o `ServeMux` responder e reescrever as respostas dele com um *wrapper* do `ResponseWriter`. É mais frágil e esconde a regra.

## R4. Parâmetros da *query*

O `URL.Query()` do Go descarta em silêncio os pares mal codificados, e o `Get` devolve o **primeiro** valor de um parâmetro repetido.

- **Decision**:
  - ler com `url.ParseQuery(pedido.URL.RawQuery)`. Se der erro, ou se algum valor não for UTF-8 válido (`utf8.ValidString`), a resposta é 400 `entrada-invalida`. Essa é a lição da **T046**: no E4, `?nome=%ZZ` virava 500;
  - parâmetro repetido vale pelo **último** valor, como no E1 e no E4 (lição da **T045**);
  - `pagina` com só dígitos, mas grande demais para `int64` (`strconv.ErrRange`), conta como página além do fim: 200 com a lista vazia, como no E4 com `BigInteger` (lição da **T045**).
- **Rationale**: a suíte aceita 200 ou 400 para *query* mal codificada e proíbe o 500. Seguir o E4 (400) deixa a regra explícita, em vez de depender do descarte silencioso.

## R5. Formato da resposta e cabeçalho `Accept`

- **Decision**: os handlers escrevem sempre `Content-Type: application/json` no sucesso e `application/problem+json` no erro, e o `Accept` é ignorado. O `net/http` não negocia conteúdo, então a lição da **T048** sai de graça. Um teste fixa isso mesmo assim.
- **JSON:** `json.NewEncoder` com `SetEscapeHTML(false)`. O padrão do Go escaparia `<`, `>` e `&` como `<`, o que dá o mesmo valor JSON, mas texto diferente do E1 e do E4. Os campos saem na ordem das *structs*, e o `paginacao` some quando não se aplica (`omitempty` num ponteiro).

## R6. Cliente do IBGE e prazo total

- **Decision**:
  - **Cliente:** `http.Client` da biblioteca padrão, sem nova tentativa (ele não refaz pedidos sozinho);
  - **Prazo total:** `context.WithTimeout(prazo)` no pedido. O prazo cobre conexão, cabeçalhos e leitura do corpo, porque o `io.ReadAll` também respeita o contexto. É o mesmo efeito do `asyncio.timeout` do E1 e do `orTimeout` do E4;
  - **Leitura do JSON:** para `any` ou `json.RawMessage`, com a mesma normalização manual do E1 e do E4 ("não encontrado" é `[]`, objeto ou lista de 1 item, `microrregiao` opcional, código com a quantidade exata de dígitos, siglas `^[A-Z]{2}$` e `^[A-Z]{1,2}$`);
  - **Classificação, a mesma do R6 do E1:**

    | Erro ou status | Erro de domínio |
    |---|---|
    | `context.DeadlineExceeded` (inclusive dentro de `*url.Error`) | `FonteLenta` |
    | outro erro de rede (`*net.OpError`, conexão recusada) | `FonteIndisponivel` |
    | 5xx e 429 | `FonteIndisponivel` |
    | outro status diferente de 200, JSON inválido ou fora da forma | `RespostaInesperadaDaFonte` |

- **Rationale**: a biblioteca padrão faz tudo. O `errors.Is(err, context.DeadlineExceeded)` separa o prazo das outras falhas sem inspecionar texto.

## R7. Cópia guardada e consulta compartilhada

- **Decision**:
  - **Cópia guardada:** `map[string]guardada` protegido por `sync.Mutex`;
  - **Consulta compartilhada:** `singleflight.Group` (`golang.org/x/sync` v0.25.0). Pela documentação: "If a duplicate comes in, the duplicate caller waits for the original to complete and receives the same results", **inclusive o erro**, que é a lição da T050 do E1;
  - **Prazo de cada pedido e consulta:** cada pedido espera com `DoChan` e um `select` no próprio contexto. A consulta roda com um contexto próprio, com o prazo da fonte, e não com o do primeiro pedido. Assim, um cliente que desiste não derruba a consulta dos outros, como o `shield` no E1;
  - **Falha com cópia vencida:** cada pedido que esperava devolve a cópia marcada como desatualizada;
  - **Não guardados:** "não encontrado" e erros não entram na cópia;
  - **Relógio:** injetável (uma função `agora()` para o `coletado_em` e outra monotônica para a validade), para os testes não esperarem de verdade.
- **Rationale**: o `singleflight` é a forma idiomática de consulta única em Go. Ele compartilha o resultado e o erro, que é exatamente a regra.
- **Alternatives considered**:
  - mapa de canais escrito à mão: umas 30 linhas a mais para o mesmo resultado;
  - bibliotecas de cache (`ristretto`, `groupcache`): não servem a cópia vencida em caso de falha sem adaptação, e escondem a lógica que o experimento compara.

## R8. Erros

- **Decision**:
  - um tipo `ErroDominio` com `Tipo`, `Titulo`, `Status` e `Detalhe`, e seis construtores com os mesmos tipos, títulos e status do E1;
  - os handlers devolvem `error`, e um adaptador único converte em problem+json: `type` igual à URN, `title`, `status`, `detail` e `correlacao_id`;
  - qualquer erro que não seja `ErroDominio`, e qualquer `panic` (recuperado no handler de topo), vira 500 `erro-interno`, com `detail` genérico e sem rastro de execução.
- **Rationale**: Go não tem exceções. O erro como valor deixa explícito, em cada função, o que pode falhar. É um dos pontos a observar na comparação (FR-007, tratamento de erros).

## R9. Dobra, ordenação e paridade

- **Decision**: uma cadeia de `transform` do `x/text`: `norm.NFKD`, depois `runes.Remove(runes.In(unicode.Mn))` e depois `cases.Fold()`. Ordenação com `slices.SortFunc`, pela chave (nome dobrado, código).
- **Rationale**:
  - é a mesma regra do E1 (NFKD, sem marcas, *casefold*), e o `cases.Fold()` é um *casefold* de verdade, ao contrário do `toLowerCase` do E4;
  - a paridade não é presumida: o cenário de paridade de ordenação que o E4 acrescentou à suíte (os 645 municípios de SP) confere (FR-004, SC-005).

## R10. Métricas com os nomes do contrato

- **Decision**: `prometheus/client_golang` v1.25.0, num **registro próprio** (`prometheus.NewRegistry()`), e não no registro global.

  | Métrica | Tipo | Rótulos |
  |---|---|---|
  | `localidades_pedidos_total` | `CounterVec` | `rota`, `status` |
  | `localidades_erros_total` | `CounterVec` | `tipo` |
  | `localidades_cache_total` | `CounterVec` | `resultado` |
  | `localidades_fonte_duracao_segundos` | `HistogramVec`, com as mesmas faixas do E1 | `recurso` |

  O `/metrics` usa `promhttp.HandlerFor(registro, ...)`, com `Content-Type` `text/plain; version=0.0.4`. Os coletores de runtime do Go (`go_*` e `process_*`) também são registrados, como o E4 expõe os da JVM. O rótulo `rota` é o padrão do `ServeMux` sem o método (`/v1/municipios/{codigo}`), ou `nao-encontrado`.
- **Rationale**: o cliente Go não impõe sufixos de unidade, então o nome do contrato sai direto. É o ponto que no E4 exigiu trocar `Timer` por `DistributionSummary`.

## R11. Configuração `LOCALIDADES_*`

- **Decision**: leitura à mão com `os.Getenv` e `strconv`, com os mesmos padrões do E1 e as mesmas regras de validação do E4 depois da T049:
  - `LOCALIDADES_PRAZO_FONTE_S` e `LOCALIDADES_VALIDADE_S`: número finito entre 0,001 e 10⁹. O `strconv.ParseFloat` aceita `NaN`, `Inf` e `infinity`, que são recusados explicitamente com `math.IsNaN` e `math.IsInf`. Essa é a lição da **T049**;
  - `LOCALIDADES_ITENS_MAX`: inteiro positivo;
  - `LOCALIDADES_IBGE_URL`: começa com `http://` ou `https://`;
  - `LOCALIDADES_HOST` e `LOCALIDADES_PORTA`.

  Valor inválido impede a partida com uma mensagem clara, no formato do E1 (`configuração inválida: LOCALIDADES_X precisa …, recebi '…'`), e código de saída diferente de zero.
- **Rationale**: sem framework, a validação é explícita e curta. A mensagem fica igual à do E1, o que o Spring não permitia.

## R12. Correlação e registro

- **Decision**:
  - **Correlação:** no handler de topo, com a regra do R12 do E1 (1 a 64 caracteres em `[A-Za-z0-9._-]`, senão UUID v4). O UUID v4 é gerado com `crypto/rand`, sem dependência. O valor vai num `context.Context` do pedido e no cabeçalho de toda resposta;
  - **Registro:** `log/slog` com `JSONHandler` e `ReplaceAttr`, para os campos saírem com os nomes do E1: `momento`, `nivel`, `correlacao_id`, `metodo`, `rota`, `status`, `duracao_ms`, `cache` e `fonte_ms`, numa linha por pedido;
  - **Status, uso da cópia e tempo da fonte:** um `ResponseWriter` que guarda o status, e um valor mutável no contexto do pedido, preenchido pelo serviço e pelo cliente.
- **Rationale**: o `slog` entrou na biblioteca padrão no Go 1.21 e cobre registro estruturado sem dependência.

## R13. Testes

- **Decision**:
  - **Ferramentas:** `testing` e `net/http/httptest`, com tabelas de casos (*table-driven tests*), o costume da linguagem;
  - **IBGE simulado:** `httptest.NewServer` em loopback, servindo as fixtures de `contracts/localidades/fixtures-ibge/` e contando os pedidos;
  - **Testes de API:** `httptest.NewRecorder` contra o handler de topo e, nos casos que dependem do pedido cru (caminho e *query* mal codificados), um `httptest.Server` com pedido escrito à mão no socket, como no E4;
  - **SC-004 (sem rede):** `go test ./...` dentro do mesmo sandbox do E1 e do E4, com `GOFLAGS=-mod=mod GOPROXY=off`, depois de popular o cache de módulos.
- **Rationale**: a biblioteca padrão já traz o equivalente do `respx`, do `TestClient`, do WireMock e do MockMvc.

## R14. Caixa-preta e paridade

- **Decision**: o binário é gerado em `experiments/go/localidades/localidades` (ignorado pelo git) e verificado com `contracts/localidades/verificacao/verificar.sh "experiments/go/localidades/localidades"`. O contrato não muda. Se o E7 revelar um caso novo, o cenário entra na suíte e precisa passar no E1 e no E4 (FR-002).
- **Rationale**: é o critério de pronto do E1 e do E4.

## R15. Comparação entre três (FR-006, FR-007 e FR-009)

- **Decision**:
  - o `medir.py` do E4 ganha a terceira implementação, com o mesmo método (R13 do E4): mediana de 3 execuções, mesma máquina, mesmo dia e o E1 e o E4 medidos de novo junto;
  - para o E7, o build é `go build`, a suíte é `go test ./...`, o artefato é o binário, e as dependências diretas são as linhas `require` sem `// indirect` no `go.mod`;
  - a nota qualitativa (FR-007) é escrita num `ergonomia.md` durante a implementação, nos mesmos cinco pontos;
  - o `RESULTS.md` tem uma tabela das lições T044 a T050, uma linha por lição, dizendo se o comportamento apareceu em Go e como foi tratado (FR-009, SC-006).
- **Rationale**: números iguais em forma permitem comparar sem declarar vencedor sem medida (FR-008).

# Diário de ergonomia: E7 (Go), comparado ao E1 (Python) e ao E4 (Java)

Escrito durante a implementação, e não de memória no fim (FR-007; research R15). Cada seção registra o que foi fácil ou difícil e por quê. As notas de 1 a 5 entram na consolidação da US6 (T038).

## Setup

- **2026-11-27, instalação:** `brew install go` instalou o Go 1.27.4 (`go version go1.27.4 darwin/arm64`), a mesma versão listada como estável em go.dev/dl. O usuário instalou no próprio terminal. Não precisou de senha de administrador, ao contrário do JDK no E4.
- **2026-11-27, módulo e dependências:** `go mod init` e `go get` das três dependências levaram 2 s, com o cache de módulos vazio. O `go.mod` e o `go.sum` são o *lockfile*. Não há *wrapper*, gerador de projeto nem arquivo de build: o esqueleto é um `main.go` de 15 linhas.
- **2026-11-27, primeiro build:** `go build` levou 3 s e gerou um binário de 7,9 MB, que já sobe e responde `/health`. Não há runtime separado: o binário é o artefato.
- **2026-11-27, `go mod tidy`:** no fim da fundação, o `tidy` tirou do `go.mod` o `client_golang` e o `x/sync`, porque nenhum código os importava ainda. Só ficou o `x/text`, usado pela dobra. As duas dependências voltam, nas versões fixadas no research, quando a US3 e a US5 passarem a usá-las. O `go.mod` só declara o que o código usa de fato, o que o `pom.xml` e o `pyproject.toml` não garantem sozinhos.

## Testes

- **2026-11-27, fundação:** tudo com a biblioteca padrão. Para o IBGE simulado, foi usado o `httptest.NewServer`; para os testes de API, o `httptest.NewRecorder`; e os casos ficaram em tabela (*table-driven*). Nenhuma biblioteca de testes externa, enquanto o E1 usou `respx` e o E4, WireMock e AssertJ. O preço é escrever as asserções à mão (`if obtido != esperado { t.Errorf(...) }`), mais verboso que o `assert` do pytest ou o AssertJ.
- **Pedido cru:** como no E4, os casos de caminho irregular e o `TRACE` precisaram de um pedido escrito à mão no socket (`testeapoio.PedidoCru`), porque um cliente HTTP comum limparia o caminho antes de enviar. Em Go, o `http.ReadResponse` da biblioteca padrão lê a resposta crua, então o apoio ficou com 40 linhas.
- **Velocidade:** `go test -count=1 ./...` leva 0,8 s para os 36 testes da fundação, compilando tudo. O E4 levava alguns segundos só para subir o contexto do Spring nos testes de integração.

## Cumprir o contrato escrito à mão

- **2026-11-27, configuração:** o `strconv.ParseFloat` aceita `NaN`, `Inf`, `infinity` e devolve infinito para `1e400` (com `ErrRange`). Sem a checagem explícita do research R11, o Go teria a mesma lacuna da T049 do E4. Com a validação escrita à mão, a mensagem sai igual à do E1 (`configuração inválida: LOCALIDADES_PRAZO_FONTE_S precisa ser um número finito, recebi 'Inf'`), o que o relatório do Spring não permitia.
- **2026-11-27, JSON:** o `encoding/json` escapa `<`, `>` e `&` por padrão, e o `Encoder` acrescenta uma quebra de linha no fim. Os dois exigiram um ajuste (`SetEscapeHTML(false)` e cortar o `\n`), para o corpo sair igual ao do E1 e do E4.
- **2026-11-28, US1:** os 27 cenários da US1, da paridade de ordenação (os 645 municípios de SP) e de contrato passaram de primeira contra o binário. A paridade com o E1 veio do `cases.Fold()`, sem ajuste. Duas armadilhas da biblioteca padrão foram evitadas porque estavam previstas no research R4: o `URL.Query()` descartaria em silêncio um `?itens=%ZZ` (o pedido seguiria com o padrão, sem erro) e o `Get` pegaria o **primeiro** valor de um parâmetro repetido. A leitura usa `url.ParseQuery` e o último valor.
- **Rotas com método e curinga:** os padrões `GET /v1/ufs/{uf}/municipios` e o `r.PathValue("uf")` do Go 1.22 deixaram as rotas tão curtas quanto no FastAPI. Um detalhe: o `mux.Handler(r)`, usado no handler de topo para decidir, não preenche o `PathValue`. Por isso, o handler de topo chama o `ServeMux` de novo para despachar.
- **2026-11-28, US4:** a busca por nome entrou junto com a US1, porque usa o mesmo serviço e o mesmo handler. Nesta fase, os 6 testes da busca e os 16 cenários da suíte (US4 e paridade) passaram de primeira. A ordem do TDD ficou invertida nesta fase: os testes vieram depois do código e servem como verificação. A busca acentuada (`NITERÓI`, `são`/`SAO`) bateu com o E1 sem ajuste, pela mesma dobra do `cases.Fold()`.
- **2026-11-28, US2 e a lição da T044:** a única lição do E4 que custou caro em Go. Com `/v1/municipios/%ZZ`, o `net/http` recusa o pedido ao ler a linha, antes de qualquer handler, com `400 Bad Request` em texto puro e sem correlação. É o mesmo que o Tomcat fazia no E4, mas sem nem uma válvula de erro para trocar: a biblioteca padrão não tem gancho. A saída foi descer um nível e embrulhar o `net.Listener` (`internal/transporte`, cerca de 150 linhas com o teste), saneando a linha do pedido antes do `net/http`. Funciona e está testado (com *keep-alive* e com corpo no meio da conexão), mas é a parte do E7 que mais se afasta do caminho comum do ecossistema.
- **2026-11-28, convergência (`OPTIONS *`):** o `http.Server` responde sozinho ao `OPTIONS *` com 200 vazio, antes de qualquer handler. Ao contrário do `%ZZ` no caminho (T044 do E4), este tem uma opção pronta: `DisableGeneralOptionsHandler`. Bastou uma linha.
- **2026-11-27, primeiras sondagens no esqueleto:** o `ServeMux` da biblioteca padrão responde **405** para método não suportado (`POST /health` e `TRACE /health`) e **307** para `//health`. O contrato pede 404 em `problem+json` nos dois casos. É o equivalente, no Go, das convenções do Tomcat e do Spring que custaram convergências no E4. Aqui elas foram previstas no plano (research R3) e ficam num handler de topo.

## Consulta compartilhada e concorrência

- **2026-11-28, US3:** o `singleflight` resolveu a consulta única em uma chamada (`grupo.DoChan`). Ele já compartilha o resultado **e o erro** com quem chega durante a consulta, que é a lição da T050 do E1, sem nada a acrescentar.
  - **Pedido que desiste:** o `context.WithoutCancel(ctx)` deixa a consulta seguir quando o pedido que a iniciou desiste, guardando os valores do contexto (o tempo da fonte continua anotado no pedido certo). Cada pedido espera no próprio contexto, com um `select`. É o `asyncio.shield` do E1, sem a sutileza de cancelamento de tarefas.
  - **Detectar quem iniciou:** o `singleflight` informa `Shared`, mas não quem iniciou, e só quem iniciou conta como "falta" nas métricas. A saída foi uma variável capturada pela função, que só o iniciador executa. A sincronização vem do próprio canal.
  - **Comparação:** no E1, foram 3 convergências até a consulta compartilhada ficar certa (fila com `asyncio.Lock`, depois falha compartilhada). No E4, o `CompletableFuture` com `computeIfAbsent` acertou de primeira porque a lição já existia. No E7, o desenho também veio pronto, e o `go test -race` deu uma garantia que os outros dois não tinham: o detector de corrida roda junto com os testes de concorrência.
- **Cliente que desiste:** sem tratamento, um pedido cancelado viraria 500 `erro-interno` nas métricas. Agora ele é registrado com 499 (a convenção do nginx), sem corpo, e não conta como erro do serviço.
- **Os 8 cenários da US3 passaram de primeira contra o binário,** inclusive "pedidos simultâneos com a fonte travada não fazem fila".

## Tratamento de erros

- **2026-11-27, fundação:** sem exceções, cada função devolve `error`, e o handler devolve o erro em vez de escrevê-lo (`HandlerComErro`). Um único ponto (`EscreverProblema`) converte em problem+json, e o `errors.As` reconhece o `ErroDominio`. É mais explícito que o `@RestControllerAdvice` do E4 e que os *exception handlers* do FastAPI: o caminho do erro aparece em cada assinatura. O custo apareceu na leitura do JSON do IBGE, em que cada campo pode falhar; um pequeno acumulador de erro (`leitor`) evitou um `if err != nil` por linha.
- **Panic:** um `recover` no handler de topo transforma qualquer `panic` em 500 `erro-interno`, sem rastro. Sem ele, o `net/http` derrubaria só a conexão, sem resposta no formato do contrato.

## Métricas e registro

- **2026-11-28, métricas:** o `client_golang` não impõe sufixo de unidade, então `localidades_fonte_duracao_segundos` saiu com o nome do contrato sem ajuste. No E4, foi preciso trocar o `Timer` do Micrometer por um `DistributionSummary` para escapar do `_seconds`. Num registro próprio (`prometheus.NewRegistry()`), cada montagem de teste tem as suas séries, sem o estado global que o E1 também evitou.
- **O preço do `client_golang`:** a única dependência pesada do E7. Ele trouxe 8 módulos indiretos (protobuf, `prometheus/common`, `procfs`, compressão etc.), e o binário passou de 7,9 MB para 14 MB. Um formato de texto escrito à mão para 4 métricas teria evitado isso. Fica registrado como contrapartida do caminho comum do ecossistema.
- **Negociação no `/metrics`:** o `promhttp` negocia pelo `Accept` e devolveria protobuf ou OpenMetrics a quem pedisse. É o mesmo tipo de comportamento da T048 do E4, aqui no endpoint de métricas. O handler retira o `Accept` antes, e o `/metrics` sai sempre em texto. Um teste fixa isso com 4 valores de `Accept`.
- **Registro:** o `log/slog` com `JSONHandler` e um `ReplaceAttr` de 20 linhas deu os campos do E1 na mesma ordem (`momento`, `nivel`, `correlacao_id`...), sem mensagem e sem dependência. No E4, foi preciso um *logger* dedicado com padrão `%m%n` e o Jackson montando a linha.
- **Resultado:** com a US5, os **82 de 82 cenários** da suíte passaram contra o binário (SC-001).

## Avaliação (FR-007)

Notas de 1 (difícil) a 5 (fácil) para a experiência de construir o mesmo serviço. As notas do E1 e do E4 são as do [diário do E4](../003-localidades-java/ergonomia.md), e as medidas estão em [medicao/resultado-2026-11-28.md](medicao/resultado-2026-11-28.md), tiradas no mesmo dia para as três.

| Ponto | E1 (Python) | E4 (Java) | E7 (Go) | Por quê (E7) |
|---|---|---|---|---|
| **Setup** | 5 | 3 | 5 | `brew install go` sem senha de administrador, `go mod init` e três `go get` em 2 s, sem *wrapper*, gerador de projeto nem arquivo de build. Do clone à primeira resposta, 1,2 s (E1: 1,1 s; E4: 3,0 s). |
| **Escrita de testes** | 4 | 3 | 4 | Tudo com a biblioteca padrão (`testing` e `httptest`), sem biblioteca de testes externa, e com o detector de corrida (`-race`) de graça. A suíte roda em 1,0 s (E1: 0,9 s; E4: 6,6 s). Perde um ponto pelas asserções escritas à mão, mais verbosas que o `assert` do pytest ou o AssertJ, e pelo apoio de pedido cru, que também foi preciso no E4. |
| **Cumprir o contrato escrito à mão** | 4 | 4 | 3 | A biblioteca padrão tem os seus próprios comportamentos fora do contrato: o `ServeMux` redireciona `//`, `.` e `..` e responde 405; o `net/http` recusa um `%ZZ` no caminho com 400 em texto puro, antes de qualquer handler; o `URL.Query()` descarta pares mal codificados em silêncio; e o JSON escapa `<>&`. Tudo foi previsto ou contornado, mas um deles exigiu embrulhar o `net.Listener`. É também o E7 com mais linhas de produção (1.758, contra 1.279 do E4 e 799 do E1): o que os outros ganham do framework, aqui é escrito à mão. |
| **Tratamento de erros** | 3 | 4 | 4 | Erro como valor deixa o caminho de cada falha explícito, e um adaptador único converte em problem+json. O `recover` resolve o 500 sem rastro. Perde para o ideal pela verbosidade do `if err != nil`, contida na leitura do JSON do IBGE com um pequeno acumulador. |
| **Métricas e registro** | 4 | 3 | 4 | O `client_golang` expõe os nomes exatos, sem sufixo de unidade, e o `log/slog` deu o registro do E1 com um `ReplaceAttr` de 20 linhas. Perde um ponto pelo peso do `client_golang` (8 módulos indiretos; o binário foi de 7,9 MB para 14 MB) e pela negociação de formato do `promhttp`, que precisou ser desligada. |

**Cuidados de leitura (FR-008):**
- **Ordem de construção:** o E7 foi feito **depois** do E1 e do E4, com as decisões e as lições das 5 convergências do E4 já conhecidas. As lições viraram tarefas desde o início, o que favorece o E7 em "acertar o desenho" e não diz nada sobre a linguagem.
- **Mesmo autor:** as três implementações foram escritas pelo mesmo assistente. Uma equipe com experiência maior em um dos ecossistemas daria outras notas.
- **Números do contexto:** a partida (0,03 s), a memória (15 MB) e o artefato (14,9 MB) do E7 refletem a ausência de runtime separado: o binário é compilado e já traz o servidor. A latência aquecida do E7 (0,09 ms) é menor que a do E1 e do E4 (0,37 e 0,38 ms), mas as três ficam bem abaixo de 1 ms num pedido atendido pela cópia, em loopback. Num pedido real ao IBGE, a rede (dezenas a centenas de milissegundos) domina, e a diferença deixa de importar.
- **Linhas de código:** o E7 tem mais linhas porque escreve à mão o que o FastAPI e o Spring dão: leitura e validação da *query* e da configuração, normalização do JSON do IBGE campo a campo, o handler de topo e o `Ouvinte`. Os testes também são mais longos, pelas asserções manuais.
- **Dependências:** as 3 diretas do E7 escondem 8 indiretas, todas do `client_golang`. Sem ele, o E7 dependeria só de dois módulos do próprio projeto Go.

## Lições do E4

Uma linha por lacuna das convergências do E4, preenchida à medida que cada uma aparecer (FR-009). A tabela final vai para o `RESULTS.md`.

| Lição do E4 | Apareceu em Go? | Como foi tratada |
|---|---|---|
| T044 — caminho mal codificado fora do formato | Sim, e pior: o `net/http` responde `400 Bad Request` em texto puro, sem correlação, antes de qualquer handler, e não tem gancho para mudar | Um `net.Listener` próprio (`internal/transporte`) troca, só no caminho, o `%` inválido por `%25`; o texto literal chega ao handler e vira 400 `entrada-invalida` em problem+json. Testes com pedido cru e o cenário da suíte conferem |
| T045 — `pagina` grande demais e parâmetro repetido | Em parte: `pagina=99999999999` cabe em `int64`, mas 30 dígitos estouram, e o `Get` da *query* pega o primeiro valor repetido | `strconv.ErrRange` com só dígitos vale como página além do fim, e a leitura usa o último valor. Testes e o cenário da suíte conferem |
| T046 — *query* mal codificada virando 500 | Não viraria 500, mas seria pior: o `URL.Query()` descarta o par mal codificado em silêncio, e o pedido seguiria com o padrão | `url.ParseQuery` com erro, ou valor que não é UTF-8 válido → 400 `entrada-invalida`, sem consultar o IBGE |
| T047 — `TRACE` fora do formato e ecoando o pedido | Sim, em parte: o `ServeMux` responde 405 em texto para `TRACE` (e qualquer método não registrado). Não há eco, porque o `net/http` não implementa o `TRACE` | Padrão vazio no `mux.Handler` → 404 `nao-encontrado`, no handler de topo. Teste com pedido cru confere que nada é ecoado |
| T048 — `Accept` mudando o formato da resposta | Não: o `net/http` não negocia conteúdo | Os handlers escrevem o `Content-Type` sempre. Um teste fixa isso para `/health` e para os erros |
| T049 — configuração infinita ou arredondada para zero | Sim: o `ParseFloat` aceita `NaN`, `Inf` e `infinity` | Recusa explícita com `math.IsNaN` e `math.IsInf`, mais os limites de 0,001 e 10⁹ s, com a mensagem do E1 |
| T050 — parâmetros de caminho (`;`) ignorados | Não: o `ServeMux` trata o `;` como texto. Mas ele **redireciona** (307) caminhos com `//`, `.` e `..`, um comportamento parecido de normalização | O handler de topo responde 404 para `;`, `//`, `.` e `..` antes do `ServeMux`, sem redirecionar |

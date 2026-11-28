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
- **2026-11-27, primeiras sondagens no esqueleto:** o `ServeMux` da biblioteca padrão responde **405** para método não suportado (`POST /health` e `TRACE /health`) e **307** para `//health`. O contrato pede 404 em `problem+json` nos dois casos. É o equivalente, no Go, das convenções do Tomcat e do Spring que custaram convergências no E4. Aqui elas foram previstas no plano (research R3) e ficam num handler de topo.

## Tratamento de erros

- **2026-11-27, fundação:** sem exceções, cada função devolve `error`, e o handler devolve o erro em vez de escrevê-lo (`HandlerComErro`). Um único ponto (`EscreverProblema`) converte em problem+json, e o `errors.As` reconhece o `ErroDominio`. É mais explícito que o `@RestControllerAdvice` do E4 e que os *exception handlers* do FastAPI: o caminho do erro aparece em cada assinatura. O custo apareceu na leitura do JSON do IBGE, em que cada campo pode falhar; um pequeno acumulador de erro (`leitor`) evitou um `if err != nil` por linha.
- **Panic:** um `recover` no handler de topo transforma qualquer `panic` em 500 `erro-interno`, sem rastro. Sem ele, o `net/http` derrubaria só a conexão, sem resposta no formato do contrato.

## Métricas e registro

## Lições do E4

Uma linha por lacuna das convergências do E4, preenchida à medida que cada uma aparecer (FR-009). A tabela final vai para o `RESULTS.md`.

| Lição do E4 | Apareceu em Go? | Como foi tratada |
|---|---|---|
| T044 — caminho mal codificado fora do formato | | |
| T045 — `pagina` grande demais e parâmetro repetido | Em parte: `pagina=99999999999` cabe em `int64`, mas 30 dígitos estouram, e o `Get` da *query* pega o primeiro valor repetido | `strconv.ErrRange` com só dígitos vale como página além do fim, e a leitura usa o último valor. Testes e o cenário da suíte conferem |
| T046 — *query* mal codificada virando 500 | Não viraria 500, mas seria pior: o `URL.Query()` descarta o par mal codificado em silêncio, e o pedido seguiria com o padrão | `url.ParseQuery` com erro, ou valor que não é UTF-8 válido → 400 `entrada-invalida`, sem consultar o IBGE |
| T047 — `TRACE` fora do formato e ecoando o pedido | Sim, em parte: o `ServeMux` responde 405 em texto para `TRACE` (e qualquer método não registrado). Não há eco, porque o `net/http` não implementa o `TRACE` | Padrão vazio no `mux.Handler` → 404 `nao-encontrado`, no handler de topo. Teste com pedido cru confere que nada é ecoado |
| T048 — `Accept` mudando o formato da resposta | Não: o `net/http` não negocia conteúdo | Os handlers escrevem o `Content-Type` sempre. Um teste fixa isso para `/health` e para os erros |
| T049 — configuração infinita ou arredondada para zero | Sim: o `ParseFloat` aceita `NaN`, `Inf` e `infinity` | Recusa explícita com `math.IsNaN` e `math.IsInf`, mais os limites de 0,001 e 10⁹ s, com a mensagem do E1 |
| T050 — parâmetros de caminho (`;`) ignorados | Não: o `ServeMux` trata o `;` como texto. Mas ele **redireciona** (307) caminhos com `//`, `.` e `..`, um comportamento parecido de normalização | O handler de topo responde 404 para `;`, `//`, `.` e `..` antes do `ServeMux`, sem redirecionar |

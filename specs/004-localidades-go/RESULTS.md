# Resultados: E7 — Serviço de localidades (IBGE), em Go

- **Pergunta que o experimento respondia:** como é construir e operar o mesmo serviço de localidades em Go, do setup aos testes e ao cumprimento do mesmo contrato, comparado ao E1 (Python) e ao E4 (Java)?
- **Timebox previsto / usado:** 2 a 3 sessões curtas / 2 sessões (2026-11-27 e 2026-11-28), em 9 PRs: spec e plano (#74), fundação (#75), US1 a US6 (#76 a #81) e este fechamento.
- **Linguagem e ferramentas:** Go 1.27.4; biblioteca padrão para HTTP (`net/http`), JSON, registro (`log/slog`) e testes (`testing`, `httptest`); `prometheus/client_golang` v1.25.0, `golang.org/x/text` v0.44.0 e `golang.org/x/sync` v0.25.0.
- **Data de conclusão:** 2026-11-28

## Resposta curta
**O mesmo serviço em Go cumpriu o mesmo contrato sem mudar uma linha dele.** Passou nos 82 cenários de caixa-preta, os mesmos do E1 e do E4, e devolveu, contra o IBGE real, respostas idênticas às das outras duas implementações.

- **Onde o Go se destacou:** no custo de operar. Partida em 0,03 s, 15 MB de memória e um binário de 14,9 MB, sem runtime à parte. No setup e no ciclo de testes, ficou tão rápido quanto o Python (1,2 s do clone à primeira resposta; 1,0 s na suíte).
- **Onde cobrou:** no custo de construir. Sem framework, foi preciso escrever à mão o que o FastAPI e o Spring dão de graça (leitura da *query*, validação da configuração, normalização do JSON, `problem+json`), e o E7 terminou com mais código que os outros dois (1.758 linhas de produção, contra 1.279 do E4 e 799 do E1). A biblioteca padrão também tem os seus comportamentos fora do contrato, e um deles (o `%ZZ` no caminho) exigiu descer até o `net.Listener`.
- **Latência:** a do E7 foi a menor (0,09 ms com a cópia guardada, contra 0,37 e 0,38 ms). Mas as três ficam bem abaixo de 1 ms, e num pedido real ao IBGE a rede domina. Num serviço que só repassa dados, a linguagem continua não sendo o gargalo.

## O que foi feito
Serviço em `experiments/go/localidades/`, com as mesmas rotas, regras e configuração `LOCALIDADES_*` do E1 e do E4, nas mesmas camadas (`dominio`, `fonte`, `cache`, `servico`, `api`, `operacao`), mais `transporte`, que saneia a linha do pedido. O trabalho seguiu as histórias US1 a US5 do E1 e a US6 de comparação, agora entre três implementações. As lições das 5 convergências do E4 entraram como tarefas desde o início (FR-009), e o diário de ergonomia ([ergonomia.md](ergonomia.md)) foi escrito durante cada fase.

## Fontes e documentação oficial
As mesmas do E1: a API de localidades do IBGE e a [ficha da fonte](../../discovery/fichas/ibge-localidades.md). Versões conferidas em 2026-11-27 em go.dev/dl, go.dev/doc/devel/release e proxy.golang.org. O comportamento do `ServeMux` foi lido em pkg.go.dev/net/http e conferido na prática (405 para método não suportado e 307 para `//`).

## Como executar localmente
A partir da raiz do repositório, com o Go 1.27 instalado:

```bash
(cd experiments/go/localidades && go vet ./... && go test ./...)          # 78 testes
(cd experiments/go/localidades && go build -o localidades ./cmd/localidades)
contracts/localidades/verificacao/verificar.sh "experiments/go/localidades/localidades"   # 82 cenários
specs/004-localidades-go/medicao/medir.sh                                  # comparação E1 × E4 × E7
```

## Exemplos de requisição e resposta
Execução real contra o IBGE em **2026-11-28 15:53 UTC**, com o E1, o E4 e o E7 lado a lado recebendo os mesmos pedidos. O corpo foi comparado ignorando só o `coletado_em`, a correlação e o `instance` que o Spring acrescenta:

```text
/v1/ufs                                  E1 200 177 ms | E4 200 258 ms | E7 200 341 ms | corpo igual
/v1/ufs/RJ                               E1 200   5 ms | E4 200  13 ms | E7 200   1 ms | corpo igual
/v1/ufs/rj/municipios?nome=niteroi       E1 200  97 ms | E4 200 149 ms | E7 200 105 ms | corpo igual
/v1/municipios/3304557                   E1 200  98 ms | E4 200 128 ms | E7 200 109 ms | corpo igual
/v1/municipios/9999999                   E1 404  95 ms | E4 404 110 ms | E7 404  89 ms | corpo igual
/v1/ufs/MG/municipios?itens=500&pagina=2 E1 200 124 ms | E4 200 157 ms | E7 200 110 ms | corpo igual
/v1/municipios/12ab                      E1 400   1 ms | E4 400   3 ms | E7 400   1 ms | corpo igual
/v1/ufs (repetido, cópia guardada)       E1 200   1 ms | E4 200   2 ms | E7 200   1 ms | corpo igual
```

As latências da primeira consulta são, sobretudo, as do IBGE em cada momento.

## Comparação medida (US6)
Na mesma máquina e no mesmo dia, com mediana de 3 execuções e contra o IBGE falso, sem rede. Detalhes e método em [medicao/resultado-2026-11-28.md](medicao/resultado-2026-11-28.md):

| Medida | E1 (Python) | E4 (Java) | E7 (Go) |
|---|---|---|---|
| Do clone local à primeira resposta (`/v1/ufs`) | 1.1 s | 3.0 s | 1.2 s |
| Build (dentro do clone) | 0.2 s | 1.9 s | 0.8 s |
| Suíte de testes da implementação | 0.9 s | 6.6 s | 1.0 s |
| Partida até o `/health` responder | 0.17 s | 1.04 s | 0.03 s |
| Memória (RSS) depois de 10 pedidos | 55 MB | 251 MB | 15 MB |
| Tamanho do artefato | 80.9 MB | 26.3 MB | 14.9 MB |
| Linhas de código (produção / testes, sem linhas em branco) | 799 / 817 | 1279 / 1513 | 1758 / 1996 |
| Dependências diretas (runtime + teste) | 4 + 2 | 4 + 3 | 3 + 0 |
| Latência mediana com a cópia guardada (20 pedidos) | 0.40 ms | 0.76 ms | 0.13 ms |
| _Contexto:_ a mesma latência depois de 500 pedidos de aquecimento | 0.37 ms | 0.38 ms | 0.09 ms |

A avaliação qualitativa (notas de 1 a 5 em setup, testes, contrato, erros e métricas) está no [diário de ergonomia](ergonomia.md#avaliação-fr-007): E7 com 5, 4, 3, 4 e 4.

## Lições do E4 em Go (FR-009, SC-006)
Para cada lacuna achada nas convergências do E4, se o mesmo comportamento apareceu em Go e como foi tratado:

| Lição do E4 | Apareceu em Go? | Como foi tratada |
|---|---|---|
| T044 — caminho mal codificado fora do formato | Sim, e pior: o `net/http` responde `400 Bad Request` em texto puro, sem correlação, antes de qualquer handler, e não tem gancho para mudar | Um `net.Listener` próprio (`internal/transporte`) troca, só no caminho, o `%` inválido por `%25`; o texto literal chega ao handler e vira 400 `entrada-invalida` em problem+json. Testes com pedido cru e o cenário da suíte conferem |
| T045 — `pagina` grande demais e parâmetro repetido | Em parte: `pagina=99999999999` cabe em `int64`, mas 30 dígitos estouram, e o `Get` da *query* pega o primeiro valor repetido | `strconv.ErrRange` com só dígitos vale como página além do fim, e a leitura usa o último valor. Testes e o cenário da suíte conferem |
| T046 — *query* mal codificada virando 500 | Não viraria 500, mas seria pior: o `URL.Query()` descarta o par mal codificado em silêncio, e o pedido seguiria com o padrão | `url.ParseQuery` com erro, ou valor que não é UTF-8 válido → 400 `entrada-invalida`, sem consultar o IBGE |
| T047 — `TRACE` fora do formato e ecoando o pedido | Sim, em parte: o `ServeMux` responde 405 em texto para `TRACE` (e qualquer método não registrado). Não há eco, porque o `net/http` não implementa o `TRACE` | Padrão vazio no `mux.Handler` → 404 `nao-encontrado`, no handler de topo. Teste com pedido cru confere que nada é ecoado |
| T048 — `Accept` mudando o formato da resposta | Não: o `net/http` não negocia conteúdo | Os handlers escrevem o `Content-Type` sempre. Um teste fixa isso para `/health` e para os erros |
| T049 — configuração infinita ou arredondada para zero | Sim: o `ParseFloat` aceita `NaN`, `Inf` e `infinity` | Recusa explícita com `math.IsNaN` e `math.IsInf`, mais os limites de 0,001 e 10⁹ s, com a mensagem do E1 |
| T050 — parâmetros de caminho (`;`) ignorados | Não: o `ServeMux` trata o `;` como texto. Mas ele **redireciona** (307) caminhos com `//`, `.` e `..`, um comportamento parecido de normalização | O handler de topo responde 404 para `;`, `//`, `.` e `..` antes do `ServeMux`, sem redirecionar |

**Leitura:** das 7 lacunas, 2 não apareceram em Go (T048 e T050, embora a T050 tenha um parente, o redirecionamento de `//`, `.` e `..`), 3 apareceram de outra forma (T045, T046 e T047) e 2 apareceram de fato (T044 e T049). Como já eram tarefas desde o início, nenhuma virou convergência. A T044 foi a mais cara: o `net/http`, como o Tomcat, recusa o caminho mal codificado antes da aplicação, e sem nenhum gancho.

## Critérios de sucesso
- **SC-001, contrato sem mudança:** os 82 cenários passaram contra o E7, os mesmos do E1 e do E4.
- **SC-002, critérios do E1:** valem para o E7, medidos pela mesma suíte (cópia em menos de 0,5 s, falha sem cópia dentro do prazo, consulta única com pedidos simultâneos).
- **SC-003, tabela comparativa:** as 9 medidas preenchidas para as três implementações, com data e método.
- **SC-004, testes sem rede:** em 2026-11-28, dentro do sandbox sem rede externa, passaram os 78 testes do E7 (`GOFLAGS=-mod=mod GOPROXY=off go test -count=1 ./...`) e os 82 cenários, e um `curl` ao IBGE falhou no mesmo sandbox.
- **SC-005, paridade de ordenação:** a ordem dos 645 municípios de SP e as buscas da suíte deram o mesmo resultado nas três.
- **SC-006, lições do E4:** as 7 têm registro (tabela acima).

## O que funcionou
- **Biblioteca padrão:** HTTP com rotas de método e curinga, JSON, registro estruturado e testes, sem framework e sem biblioteca de testes externa.
- **`singleflight`:** a consulta compartilhada inclusive na falha saiu em uma chamada, e o `go test -race` verificou a concorrência junto com os testes.
- **Lições como tarefas:** levar as convergências do E4 para o plano evitou novas convergências do mesmo tipo.
- **`cases.Fold()`:** paridade de ordenação com o Python sem ajuste.

## O que falhou ou surpreendeu
- **`%ZZ` no caminho:** o `net/http` responde 400 em texto puro antes de qualquer handler, e não oferece gancho. A solução (`internal/transporte`) funciona e está testada, mas é a parte que mais se afasta do caminho comum do ecossistema.
- **Armadilhas silenciosas:** o `URL.Query()` descarta pares mal codificados em silêncio e pega o primeiro valor repetido; o `ParseFloat` aceita `NaN` e `Inf`; o JSON escapa `<>&`; o `RFC3339Nano` corta os milissegundos. Nenhuma quebra a compilação; todas quebrariam o contrato.
- **Mais código:** o E7 tem mais linhas de produção e de teste que o E1 e o E4.
- **Peso do `client_golang`:** 8 módulos indiretos, e o binário foi de 7,9 MB para 14 MB.
- **Ordem do TDD na US4:** a busca entrou junto com a US1, e os testes dela vieram depois do código.

## Limitações
- **Ordem de construção:** o E7 foi feito depois do E1 e do E4, já com as decisões e as lições conhecidas. Isso favorece o E7 em acertar o desenho e não diz nada sobre a linguagem.
- **Mesmo autor:** as três implementações têm o mesmo autor (o assistente). Uma equipe com mais experiência num dos ecossistemas daria outras notas.
- **Medição:** feita numa única máquina (macOS, arm64), com os caches de dependências e de build quentes. A medida "do clone à primeira resposta" não inclui baixar as dependências pela primeira vez.
- **Linhas de código:** a contagem do E7 trata `*_test.go` e o pacote `testeapoio` como testes. A do E4 inclui `.properties` e `.xml`.
- **Divergências que continuam fora da spec:** `HEAD` (aceito pelo E4 e pelo E7, recusado pelo E1) e barra no fim do caminho (o E1 redireciona; o E4 e o E7 dão 404), as mesmas registradas no E4.

## Checklist de conclusão
- [x] A fonte foi identificada e documentada (a mesma do E1)
- [x] As condições de acesso foram verificadas (execução real em 2026-11-28)
- [x] O dado foi consumido ou baixado (fixtures do E1 e execução real)
- [x] A estrutura dos dados foi inspecionada (corpos idênticos aos do E1 e do E4)
- [x] Os casos de erro foram testados (os 82 cenários e os 78 testes)
- [x] O resultado pode ser reproduzido (comandos acima e `medir.sh`)
- [x] As limitações estão registradas
- [x] A utilidade do experimento foi avaliada (abaixo)

## Decisões e próximos passos
- **Utilidade:** alta, para o método. A régua do E1 e do E4 (contrato escrito à mão, suíte de caixa-preta e medição) funcionou numa terceira linguagem sem mudança. E a tabela das lições do E4 mostrou que os desvios de contrato vêm da pilha HTTP de cada ecossistema, e não da linguagem.
- **ADR:** a [ADR 0001](../../docs/adr/0001-convencoes-comuns-de-api.md) ganhou a seção "Confirmação no E7", com uma regra nova: a suíte deve sempre ter cenários de entrada mal formada. A [ADR 0002](../../docs/adr/0002-go-e-rust-como-linguagens.md) previu este experimento.
- **Qual implementação "se gradua" para `services/`:** continua em aberto, por decisão do usuário. As medidas sugerem o E7 se o critério for o custo de operar (partida, memória, artefato único), e o E1 se for o custo de construir e manter (menos código).
- **Próximo experimento:** o **E8**, o mesmo serviço em Rust, com a mesma régua, conforme o roteiro. As lições do E4 e do E7 entram como tarefas desde o início.
- **Ideias que ficaram de fora:**
  - um `/metrics` escrito à mão, para medir o peso do `client_golang` no binário e na memória;
  - generalizar o `medir.py` para N implementações antes do E8;
  - um cenário na suíte para `HEAD`, se a spec decidir o comportamento.

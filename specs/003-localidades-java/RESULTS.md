# Resultados: E4 — Serviço de localidades (IBGE), em Java

- **Pergunta que o experimento respondia:** como é construir e operar o mesmo serviço de localidades em Java, do setup aos testes e ao cumprimento do mesmo contrato, comparado ao E1 em Python?
- **Timebox previsto / usado:** 2 a 3 sessões curtas / 1 sessão (2026-11-27), em 8 PRs, um por fase (#44 a #51 e o do fechamento).
- **Linguagem e ferramentas:** Java 25 (LTS, Temurin 25.0.5), Spring Boot 4.1.3 (Spring MVC em threads virtuais), `HttpClient` da JDK, Jackson 3, Micrometer 1.17; JUnit 5, AssertJ, MockMvc e WireMock 3.13.2; Maven 3.10.2 pelo wrapper.
- **Data de conclusão:** 2026-11-27

## Resposta curta
**O mesmo serviço em Java cumpriu o mesmo contrato sem mudar uma linha dele.** Passou nos mesmos 53 cenários de caixa-preta e devolveu, contra o IBGE real, respostas idênticas às do Python. O que muda entre as linguagens é o custo de entrar no ecossistema, e não o resultado:

- **Python (E1):** setup e ciclo de testes mais rápidos (1,0 s contra 5,9 s na suíte), partida em 0,14 s e 55 MB de memória. A desvantagem foi montar à mão o que o Spring já traz pronto, como o `problem+json`.
- **Java (E4):** o `ProblemDetail`, os `record`s e as threads virtuais deixaram o código direto e sequencial. Mas o framework cobrou em configurações e convenções que só aparecem quando quebram: exportação de métricas desligada nos testes, rota `/**`, *relaxed binding*, Jackson 3. A JVM custa 1,0 s de partida e 261 MB.
- **Latência:** depois do aquecimento, empata (0,37 ms contra 0,41 ms com a cópia guardada). Num serviço que só repassa dados, a linguagem não é o gargalo, como o roteiro previa.

## O que foi feito
Serviço em `experiments/java/localidades/`, com as mesmas rotas, regras e configuração `LOCALIDADES_*` do E1, organizado nas mesmas camadas (`dominio`, `fonte`, `cache`, `servico`, `api`, `operacao`). O trabalho seguiu as histórias US1 a US5 do E1 e acrescentou a **US6, comparação medida**. Pelo caminho:
- a suíte compartilhada ganhou um **cenário de paridade de ordenação**, que passa nas duas implementações;
- o **diário de ergonomia** ([ergonomia.md](ergonomia.md)) foi escrito durante cada fase;
- o **script de medição** ([medicao/medir.sh](medicao/medir.sh)) mede as duas implementações pelo mesmo método.

## Fontes e documentação oficial
As mesmas do E1: a API de localidades do IBGE e a [ficha da fonte](../../discovery/fichas/ibge-localidades.md). As fixtures são as de `contracts/localidades/fixtures-ibge/`, gravadas em 2026-11-26.

## Como executar localmente
A partir da raiz do repositório, com o JDK 25 instalado:

```bash
(cd experiments/java/localidades && ./mvnw -q test)                       # 141 testes
(cd experiments/java/localidades && ./mvnw -q package -DskipTests)
contracts/localidades/verificacao/verificar.sh "java -jar experiments/java/localidades/target/localidades.jar"   # 53 cenários
specs/003-localidades-java/medicao/medir.sh                                # comparação E1 × E4
```

A suíte tinha 53 cenários no fechamento; com as duas convergências, passou a 65 (veja abaixo).

```text
```

## Exemplos de requisição e resposta
Execução real contra o IBGE em **2026-11-27 19:48 UTC**, com o E1 e o E4 lado a lado, recebendo os mesmos pedidos. O corpo foi comparado ignorando só o `coletado_em` e a correlação:

```text
/v1/ufs                                   E1 200 164 ms | E4 200 282 ms | corpo igual
/v1/ufs/RJ                                E1 200   7 ms | E4 200  16 ms | corpo igual
/v1/ufs/rj/municipios?nome=niteroi        E1 200 330 ms | E4 200 126 ms | corpo igual
/v1/municipios/3304557                    E1 200 118 ms | E4 200 109 ms | corpo igual
/v1/municipios/9999999                    E1 404 109 ms | E4 404 111 ms | corpo igual (inclusive o detail)
/v1/ufs/MG/municipios?itens=500&pagina=2  E1 200 132 ms | E4 200 169 ms | corpo igual
/v1/municipios/12ab                       E1 400   3 ms | E4 400   8 ms | corpo igual
/v1/ufs (repetido, cópia guardada)        E1 200   3 ms | E4 200   5 ms
```

As latências da primeira consulta são, sobretudo, as do IBGE em cada momento.

## Comparação medida (US6)
Na mesma máquina e no mesmo dia, com mediana de 3 execuções e contra o IBGE falso, sem rede. Detalhes e método em [medicao/resultado-2026-11-27.md](medicao/resultado-2026-11-27.md):

| Medida | E1 (Python) | E4 (Java) |
|---|---|---|
| Do clone local à primeira resposta | 1,0 s | 2,9 s |
| Build | 0,2 s | 1,7 s |
| Suíte de testes da implementação | 1,0 s | 5,9 s |
| Partida até o `/health` | 0,14 s | 1,01 s |
| Memória depois de 10 pedidos | 55 MB | 261 MB |
| Tamanho do artefato | 81 MB (`.venv` + código) | 26 MB (jar com servidor) |
| Linhas (produção / testes) | 799 / 817 | 1093 / 1331 |
| Dependências diretas (runtime + teste) | 4 + 2 | 4 + 3 |
| Latência com a cópia guardada (fria) | 0,39 ms | 0,80 ms |
| A mesma latência, depois de 500 pedidos | 0,37 ms | 0,41 ms |

Avaliação qualitativa (FR-007), com nota de 1 (difícil) a 5 (fácil). As justificativas estão em [ergonomia.md](ergonomia.md):

| Ponto | E1 | E4 |
|---|---|---|
| Setup | 5 | 3 |
| Escrita de testes | 4 | 3 |
| Cumprir o contrato escrito à mão | 4 | 4 |
| Tratamento de erros | 3 | 4 |
| Métricas e registro | 4 | 3 |

## O que funcionou
- **SC-001, contrato sem mudança:** os 53 cenários passaram contra o E4, e a última história fechou a suíte inteira.
- **SC-005, paridade:** a ordem dos 645 municípios de SP e o resultado de 4 buscas saíram idênticos aos do E1, mesmo sem `casefold` no Java. O cenário de paridade passou a proteger as duas implementações.
- **SC-002:** a execução real deu corpos idênticos ao E1 nos 7 pedidos, inclusive as mensagens de erro.
- **SC-004, testes sem rede:** em 2026-11-27, dentro do sandbox sem rede externa, passaram os 133 testes do E4 (`./mvnw -o`) e os 53 cenários. Como regressão, também passaram os 140 testes e 53 cenários do E1 e os 161 testes do E0.
- **Lições do E1 aplicadas:** prazo total, formato exato dos códigos e siglas, e consulta compartilhada inclusive na falha entraram no desenho desde o começo. Nenhuma convergência foi necessária para chegar ao contrato.
- **Infraestrutura de verificação:** a suíte, as fixtures e o IBGE falso, construídos no E1, foram reaproveitados sem mudança, exceto pelo cenário novo de paridade. O investimento do E1 se pagou aqui.

## O que falhou ou surpreendeu
- **JDK:** a instalação exigiu senha de administrador, um passo manual que o `uv` não pede.
- **Spring Boot 4:**
  - os starters mudaram de nome (`spring-boot-starter-webmvc`);
  - o Jackson passou a ser o 3, com outra API (`isString`/`asString`);
  - a anotação de métricas nos testes mudou de pacote.

  Exemplos da internet anteriores ao Boot 4 não compilam.
- **Exportação de métricas desligada nos testes:** a propriedade `management.defaults.metrics.export.enabled=true` não bastou; foi preciso a anotação `@AutoConfigureMetrics`.
- **Rotas inexistentes:** elas casavam com o tratador de arquivos estáticos (`/**`), e a métrica saía com esse rótulo. Os arquivos estáticos foram desligados.
- **Relaxed binding:** `LOCALIDADES_PRAZO_FONTE_S` não liga sozinha a `prazo-fonte-s`. Foi feito o mapeamento explícito no `application.properties`.
- **Modo offline do Maven:** ele só funciona depois de os testes rodarem uma vez com rede, porque o plugin de testes é baixado sob demanda.
- **Contexto reaproveitado do Spring:** acelera os testes, mas o estado (a cópia guardada e as métricas) vaza entre eles. Foi preciso limpar o cache e isolar os testes de métricas com `@DirtiesContext`.

## Convergência
O `/speckit-converge` rodou depois do fechamento. As combinações de falha que acharam problemas no E1 (cópia vencida com a fonte travada, pedidos simultâneos, rotas diferentes sobre o mesmo recurso) passaram de primeira no E4. Duas lacunas apareceram em **entradas mal formadas**, e as duas foram corrigidas na issue #53:
- **T044 (MEDIUM):** caminhos com codificação inválida (`%ZZ`) ou barra codificada (`%2F`) eram recusados pelo Tomcat com uma página HTML, sem `X-Correlation-Id`. Agora uma válvula de erros própria responde em `problem+json`, com correlação.
- **T045 (LOW):** `pagina=99999999999` dava 400, por estouro de `int`, e o contrato pede 200 com a lista vazia. Com `itens` repetido, também dava 400. Agora `pagina` é `long`, e o parâmetro repetido vale pelo último valor, como no E1.

A suíte compartilhada ganhou 3 cenários que fixam esses comportamentos e passam nas duas implementações (56 no total).

A **segunda convergência** sondou o que passa pelo Tomcat antes do controller e achou mais duas lacunas, corrigidas na issue #55:
- **T046 (MEDIUM):** uma *query* com codificação inválida (`?nome=%ZZ`, `?nome=s%E3o`) dava **500 `erro-interno`**. O Tomcat só decodifica a *query* quando o controller lê o primeiro parâmetro, e a exceção dele (`InvalidParameterException`) caía no tratador genérico. Agora é 400 `entrada-invalida`, sem consultar o IBGE. O E1 aceita o texto como veio e responde 200; as duas respostas seguem o contrato, e a suíte só proíbe o 500.
- **T047 (LOW):** `TRACE` dava 405 no JSON padrão do Spring Boot, sem `problem+json` e sem `X-Correlation-Id`. Agora dá o mesmo 404 `nao-encontrado` dos outros métodos não suportados. O caminho óbvio (`spring.mvc.dispatch-trace-request=true`) não bastava: o `DispatcherServlet` despachava o pedido, mas depois chamava o `HttpServlet.doTrace`, que **ecoava o pedido inteiro, cookies inclusive**, depois do corpo. Isso é a porta do *cross-site tracing*. A solução foi um `DispatcherServlet` próprio (`DespachanteSemEco`) e o conector do Tomcat com `allowTrace`. Mais uma convenção do framework que só aparece quando quebra (ver [ergonomia.md](ergonomia.md)).

A suíte ganhou 9 cenários (`test_query_mal_codificada_nunca_e_500` com 4 variações e `test_metodo_trace_e_problema` com 5 métodos), que passam nas duas implementações: 65 no total. Os testes do E4 que dependem do Tomcat de verdade agora sobem o servidor numa porta livre, porque o MockMvc não passa pela decodificação da *query* nem pelo conector.

**Divergências que ficaram, porque a spec não as define:** `HEAD` e `OPTIONS` (o E4 aceita, e o E1 dá 404), barra no fim do caminho (o E1 redireciona, e o E4 dá 404) e `/v1/ufs/%2F` no E1, que responde 200 e merece uma olhada própria.

## Limitações
- **Ordem de construção:** o E4 foi feito depois do E1, já com as decisões e as correções conhecidas. Isso favorece o E4 em acertar o desenho e não diz nada sobre a linguagem.
- **Mesmo autor:** as duas implementações têm o mesmo autor (o assistente). Uma equipe com mais experiência num dos ecossistemas daria outras notas.
- **Medição:** foi feita numa única máquina (macOS, arm64), com caches de dependências quentes. A medida "do clone à primeira resposta" não inclui baixar as dependências pela primeira vez.
- **Memória da JVM:** os 261 MB são os da configuração padrão. Ajustes de heap ou compilação nativa (GraalVM) mudariam o número, mas não foram testados.
- **Linhas de código:** a contagem do E4 inclui `.properties` e `.xml` de configuração, que no E1 ficam no próprio código Python.

## Checklist de conclusão
- [x] A fonte foi identificada e documentada (a mesma do E1)
- [x] As condições de acesso foram verificadas (execução real em 2026-11-27)
- [x] O dado foi consumido ou baixado (fixtures do E1 e execução real)
- [x] A estrutura dos dados foi inspecionada (paridade com o E1 no formato de cada campo)
- [x] Os casos de erro foram testados (os mesmos 53 cenários e 133 testes)
- [x] O resultado pode ser reproduzido (comandos acima e `medir.sh`)
- [x] As limitações estão registradas
- [x] A utilidade do experimento foi avaliada (abaixo)

## Decisões e próximos passos
- **Utilidade:** alta, para o método. O experimento mostrou que um contrato escrito à mão mais uma suíte de caixa-preta permitem trocar a linguagem de um serviço sem que o consumidor perceba, e mediu o que cada ecossistema custa.
- **ADR:** a [ADR 0001](../../docs/adr/0001-convencoes-comuns-de-api.md) foi confirmada no E4, com a seção "Confirmação no E4", que registra os pontos práticos: métricas, `coletado_em`, *relaxed binding* e paridade.
- **Qual implementação "se gradua" para `services/`:** fica em aberto, por decisão do usuário. As medidas sugerem o E1 se o critério for leveza e ciclo rápido, e o E4 se o critério for um artefato único com o servidor embutido. Nenhuma das duas precisa de mudança para isso.
- **Próximo experimento:** o E2 (séries do BCB), em Python, conforme o roteiro. O método do E1 se mantém: contrato, fixtures, IBGE falso adaptado para o BCB e suíte de caixa-preta.
- **Ideias que ficaram de fora:**
  - compilação nativa com GraalVM, para comparar partida e memória;
  - gerar os DTOs a partir do OpenAPI (`openapi-generator`);
  - medir com as dependências sendo baixadas pela primeira vez.

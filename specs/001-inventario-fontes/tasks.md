---

description: "Lista de tarefas do E0 — Inventário e conectividade das fontes"
---

# Tasks: E0 — Inventário e conectividade das fontes

**Input**: Documentos de design em `specs/001-inventario-fontes/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/cli.md](contracts/cli.md), [contracts/relatorio.schema.json](contracts/relatorio.schema.json), [quickstart.md](quickstart.md)

**Tests**: incluídos. A spec exige verificação com respostas simuladas (SC-003, SC-004, SC-005, SC-007), e a constituição (princípio IV) proíbe rede nos testes. Em cada história, escreva os testes primeiro e confirme que falham.

**Organization**: tarefas agrupadas por história de usuário; cada história é um incremento testável.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: história de usuário da spec (US1 a US4)

## Path Conventions

- Projeto único em `experiments/python/discovery/`. Os caminhos abaixo são completos, a partir da raiz do repositório (não confundir com a pasta `discovery/` da raiz, que guarda catálogo, fichas e relatórios).
- Código: `experiments/python/discovery/src/inventario_fontes/`
- Testes: `experiments/python/discovery/tests/`
- Comandos: rodar a partir da raiz do repositório com `uv run --project experiments/python/discovery ...`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: criar o projeto `uv` e o esqueleto do pacote.

- [X] T001 Criar `experiments/python/discovery/pyproject.toml`: projeto `inventario-fontes` versão `0.1.0`, `requires-python = ">=3.11"`, build backend `hatchling` com layout `src/`, dependência de runtime `httpx`, grupo de dev (`[dependency-groups] dev`) com `pytest`, `respx` e `jsonschema`, script `inventario = "inventario_fontes.cli:main"` e `[tool.pytest.ini_options]` com `testpaths = ["tests"]`
- [X] T002 Criar o esqueleto do pacote e dos testes: `experiments/python/discovery/src/inventario_fontes/__init__.py` (com `__version__ = "0.1.0"`), `src/inventario_fontes/__main__.py` (chama `cli.main()` e repassa o código de saída a `sys.exit`), `src/inventario_fontes/relatorio/__init__.py` e as pastas `tests/unit/`, `tests/integration/`, `tests/contract/` e `tests/fixtures/`, todas em `experiments/python/discovery/`
- [X] T003 [P] Criar `experiments/python/discovery/README.md` com propósito (pergunta do E0), comando de testes, comando de execução real e link para `specs/001-inventario-fontes/quickstart.md`
- [X] T004 Rodar `uv sync --project experiments/python/discovery` e versionar o `experiments/python/discovery/uv.lock` gerado

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: modelos, catálogo, infraestrutura de teste e fixtures que todas as histórias usam.

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

- [X] T005 Implementar os modelos em `experiments/python/discovery/src/inventario_fontes/modelos.py`, conforme `data-model.md`, como `@dataclass(frozen=True)`:
  - **Enums (`StrEnum`)**:
    - `Grau` (`confirmado` | `parcial` | `nao_verificado`)
    - `Situacao` (`respondeu` | `falhou` | `sem_teste` | `nao_executada`)
    - `Causa` (`tempo_esgotado`, `indisponivel`, `erro_tls`, `exige_autenticacao`, `acesso_negado`, `limite_requisicoes`, `erro_fonte`, `erro_requisicao`, `resposta_invalida`)
    - `Formato` (`json` | `csv` | `xml` | `html` | `texto` | `vazio` | `outro`)
    - `Auth` (`exige` | `nao_exige` | `indeterminado`)
    - `TipoCampo` (`texto`, `inteiro`, `decimal`, `booleano`, `nulo`, `data`, `objeto`, `lista`)
    - `Aspecto` (`autenticacao` | `disponibilidade` | `formato`)
  - **Dataclasses**: `Fonte`, `Redirecionamento(status, url)`, `CampoAmostra(caminho, tipos)`, `EstruturaAmostra`, `Divergencia`, `ResultadoSondagem` (todos os atributos da tabela do data-model, com `amostra: EstruturaAmostra | None = None` e `divergencias: tuple[Divergencia, ...] = ()`), `Resumo`, `Execucao`.
  - **`Configuracao`**: `intervalo_s=2.0`, `tempo_limite_s=15.0`, `teto_bytes=1_048_576`, `max_redirecionamentos=5`. Valida "intervalo mínimo aceito `1`" e tempo limite "entre `1` e `60`", lançando `ValueError`.
  - **Regras do data-model a respeitar à risca**:
    - `CampoAmostra` tem **somente** `caminho` e `tipos`: "Não há atributo para valor, exemplo ou enumeração".
    - `Fonte` expõe a propriedade `hipotese_auth`: "`nao_exige` se `auth_esperada` começa com 'nenhuma' (sem diferenciar maiúsculas); senão `exige`".
    - `Resumo.de_resultados(resultados)` calcula os contadores e garante "`total = responderam + falharam + sem_teste + nao_executadas`".
- [X] T006 [P] Criar `experiments/python/discovery/tests/conftest.py` com:
  - fixture `autouse` que bloqueia rede real, fazendo `monkeypatch` de `socket.socket.connect` e `socket.create_connection` para lançar `RuntimeError("rede bloqueada nos testes")`;
  - fixture `relogio`: objeto `RelogioFalso` com `agora()` (datetime UTC controlável), `monotonic()` e `esperar(segundos)`, que avança o relógio e registra cada espera em `esperas: list[float]`;
  - fixture `catalogo_tmp`: fábrica que recebe uma lista de dicts de fonte e grava `sources.json` (`schema_version: 1`) em `tmp_path`, devolvendo o caminho;
  - função auxiliar `fonte_dict(**overrides)`, com uma fonte válida padrão.
- [X] T007 [P] Criar as fixtures em `experiments/python/discovery/tests/fixtures/`. Todos os dados pessoais são **fictícios**.
  - `ibge_estados.json`: lista com 3 estados no formato da API de localidades: `id`, `sigla`, `nome`, `regiao{id,sigla,nome}`.
  - `bcb_sgs_432.json`: `[{"data": "dd/mm/aaaa", "valor": "..."}]`.
  - `camara_deputados.json`: objeto com `dados` (2 deputados fictícios, com `id`, `nome`, `siglaPartido`, `siglaUf`, `email`, `urlFoto`) e `links`.
  - `pessoas_ficticias.json`: lista com nomes, e-mails e CPFs inventados, como `"Fulana Exemplo Teste"`, `"fulana.exemplo@teste.invalid"` e `"000.111.222-33"`.
  - `erro.html` (página de erro com `<!DOCTYPE html>`), `dados.csv` (cabeçalho e 6 linhas; colunas texto, inteiro, decimal e data), `dados.xml` (raiz com 6 elementos repetidos), `json_quebrado.txt` (`{"a": [1, 2`) e `vazia.json` (`[]`).
- [X] T008 [P] Escrever `experiments/python/discovery/tests/unit/test_catalogo.py`:
  - leitura do formato real (copiar 3 fontes de `discovery/sources.json`), com `probe_url: null` virando `url_teste=None`;
  - erros reportados no formato "`fonte[i] (id): campo X ...`", cobrindo `id` duplicado ou fora de `[a-z0-9-]+`, campo obrigatório ausente, `docs_url`/`probe_url` sem `http(s)://`, `data_type` vazio, `verification` fora do enum e `round` < 1;
  - vários problemas reportados de uma vez;
  - arquivo ausente e JSON inválido;
  - campos desconhecidos ignorados;
  - `hipotese_auth` de `"nenhuma (hipótese)"` dá `nao_exige`, e de `"chave de API..."` dá `exige`.
- [X] T009 Implementar `experiments/python/discovery/src/inventario_fontes/catalogo.py`:
  - `carregar_catalogo(caminho) -> Catalogo(caminho, schema_version, fontes)`, que valida o catálogo inteiro antes de devolver;
  - `ErroCatalogo(problemas: list[str])` para qualquer problema;
  - mapeamento dos campos do catálogo para atributos de `Fonte` conforme a tabela do data-model;
  - nunca escrever no arquivo (FR-003).

  Fazer T008 passar.

**Checkpoint**: modelos e catálogo prontos; as histórias podem começar.

---

## Phase 3: User Story 1 - Sondar as fontes do catálogo e ver o resultado (Priority: P1) 🎯 MVP

**Goal**: `inventario` lê o catálogo, faz uma consulta espaçada a cada fonte com `probe_url`, classifica falhas e grava o relatório JSON (a amostra fica `null` até a US2 e o HTML vem na US3).

**Independent Test**: catálogo com 3 fontes simuladas (normal, fora do ar, exige chave) produz um relatório JSON válido contra o schema, com um resultado por fonte e a causa de cada falha. Ver `quickstart.md` §1.

### Tests for User Story 1 ⚠️

> Escreva estes testes primeiro e confirme que falham.

- [X] T010 [P] [US1] Escrever `experiments/python/discovery/tests/unit/test_formato.py` (R4):
  - `{`/`[` dão `json`, inclusive com BOM UTF-8 e espaços iniciais;
  - `<?xml` e `<raiz>` dão `xml`;
  - `<!DOCTYPE html>` e `<html` dão `html`, sem diferenciar maiúsculas;
  - `dados.csv` dá `csv`, e texto de uma coluna só dá `texto`;
  - bytes vazios dão `vazio`, e bytes binários não decodificáveis dão `outro`;
  - `formato_declarado("application/json; charset=utf-8") == "application/json"`;
  - `divergente` verdadeiro quando o declarado é JSON e o detectado é HTML, e falso para `text/csv` × `csv`.
- [X] T011 [P] [US1] Escrever `experiments/python/discovery/tests/unit/test_sonda.py` com `respx`, um teste por linha da tabela R3:
  - 200 JSON dá `respondeu`, com `status_http`, `latencia_ms` ≥ 0, `coletado_em` em UTC, `tamanho_bytes` e `tamanho_declarado_bytes`;
  - `httpx.ConnectTimeout`/`ReadTimeout` dá `tempo_esgotado`;
  - `httpx.ConnectError` dá `indisponivel`;
  - `ConnectError` com `ssl.SSLCertVerificationError` como causa dá `erro_tls`;
  - 401 dá `exige_autenticacao`, com `indicio_autenticacao` "status 401";
  - 403 com `WWW-Authenticate` dá `exige_autenticacao`;
  - 302 para `https://sso.acesso.gov.br/login` (que responde 200 HTML) dá `exige_autenticacao`, com `redirecionamentos` e `url_final`;
  - 302 para `/v2/dados` que responde 200 JSON dá `respondeu`, com o redirecionamento registrado;
  - 403 dá `acesso_negado`;
  - 429 com `Retry-After: 120` dá `limite_requisicoes`, com `retry_after == "120"`;
  - 503 dá `erro_fonte`, e 404 dá `erro_requisicao`;
  - 6 redirecionamentos encadeados dão `erro_requisicao`;
  - 200 com `json_quebrado.txt` dá `resposta_invalida`;
  - corpo de 2 MiB dá `truncada=True` e `tamanho_bytes <= 1_048_576`, sem `resposta_invalida`;
  - 200 com `erro.html` declarado `application/json` dá `formato_detectado=html` e `formato_divergente=True`;
  - a requisição enviada tem `User-Agent` iniciado por `laboratorio-brasil-aberto-inventario/` e nenhum cabeçalho `Authorization` ou `Cookie`;
  - `route.call_count == 1` em todos os casos (sem nova tentativa);
  - `detalhe_causa` nunca contém o corpo da resposta.
- [X] T012 [P] [US1] Escrever `experiments/python/discovery/tests/unit/test_avaliacao.py`.
  - **Grau sugerido (R11)**: `respondeu` dá `confirmado`, com justificativa mencionando "conectividade e autenticação"; `exige_autenticacao`, `acesso_negado` e `limite_requisicoes` dão `confirmado`; `tempo_esgotado`, `indisponivel`, `erro_fonte`, `erro_tls`, `erro_requisicao` e `resposta_invalida` mantêm o grau do catálogo com justificativa; `sem_teste` e `nao_executada` mantêm o grau do catálogo.
  - **Divergências (R12)**: hipótese `nao_exige` com observado `exige` gera `Divergencia(autenticacao, "nao_exige", "exige (status 401)")`; observado `indeterminado` não gera divergência de autenticação; `falhou` gera `Divergencia(disponibilidade, "responde", "<causa>")`; `formato_divergente` gera `Divergencia(formato, <declarado>, <detectado>)`; `respondeu` sem divergência gera lista vazia.
- [X] T013 [P] [US1] Escrever `experiments/python/discovery/tests/integration/test_execucao.py` com `respx` e a fixture `relogio`:
  - catálogo com 4 fontes (200 JSON, timeout, 401, sem `probe_url`) gera 4 resultados na ordem do catálogo, e a fonte após o timeout é consultada;
  - a fonte sem `probe_url` não gera requisição e não consome intervalo;
  - com 3 sondas, `relogio.esperas` garante intervalo ≥ `intervalo_s` entre o fim de uma consulta e o início da seguinte (SC-005), e cada rota tem `call_count == 1`;
  - `KeyboardInterrupt` lançado pelo mock na 2ª consulta dá `interrompida=True`, 1ª fonte preservada e as demais como `nao_executada`;
  - `Resumo` respeita a invariante e `falhas_por_causa` traz só causas com contagem ≥ 1;
  - todas as fontes falhando ainda gera execução completa.
- [X] T014 [P] [US1] Escrever `experiments/python/discovery/tests/contract/test_relatorio_schema.py`:
  - carregar `specs/001-inventario-fontes/contracts/relatorio.schema.json` a partir de `Path(__file__).resolve().parents[5]`;
  - gerar uma execução com `respx` cobrindo `respondeu`, cada `Causa`, `sem_teste` e `nao_executada`;
  - serializar e validar com `jsonschema.Draft202012Validator`;
  - verificar datas no padrão `...Z`;
  - verificar o nome do arquivo `inventario-AAAAMMDDTHHMMSSZ.json` e o sufixo `-2` quando o arquivo já existe, sem nunca sobrescrever.
- [X] T015 [P] [US1] Escrever `experiments/python/discovery/tests/integration/test_cli.py`, chamando `cli.main([...])` com `respx` e `catalogo_tmp`:
  - código `0` com fontes falhando, e o relatório JSON criado em `--saida`;
  - `stdout` com uma linha por fonte no formato de `contracts/cli.md` (`[i/n] id .... situacao status formato N ms`) e o resumo final com o caminho dos relatórios;
  - catálogo inexistente ou inválido dá código `1`, mensagem no `stderr`, nenhuma requisição e nenhum arquivo em `--saida`;
  - `--intervalo 0.5` e `--tempo-limite 61` dão código `2`;
  - `--versao` imprime `0.1.0`;
  - `KeyboardInterrupt` dá código `130` e relatório com `interrompida: true`;
  - `--saida` inexistente é criada.

### Implementation for User Story 1

- [X] T016 [P] [US1] Implementar `experiments/python/discovery/src/inventario_fontes/formato.py` (R4):
  - `formato_declarado(content_type: str | None) -> str | None`;
  - `detectar_formato(corpo: bytes) -> Formato`, que ignora BOM e espaços, usa `csv.Sniffer` sobre as primeiras linhas e exige mais de uma coluna para dar `csv`;
  - `divergente(declarado, detectado) -> bool`, com o mapa `application/json`/`+json` → json, `text/csv` → csv, `application/xml`/`text/xml`/`+xml` → xml, `text/html` → html e `text/plain` → texto. Tipo declarado ausente ou desconhecido não conta como divergência.

  Fazer T010 passar.
- [X] T017 [US1] Implementar `experiments/python/discovery/src/inventario_fontes/sonda.py`:
  - **Assinatura**: `sondar(fonte: Fonte, cliente: httpx.Client, config: Configuracao, relogio) -> ResultadoSondagem`.
  - **Leitura (R1)**: `cliente.stream("GET", url)` e leitura com `iter_bytes()` até `config.teto_bytes`, fechando a resposta ao atingir o teto e marcando `truncada`.
  - **Redirecionamentos e login (R2)**: `history` vira `redirecionamentos`; há indício de login quando o host da URL final é `sso.acesso.gov.br` ou o caminho contém `login`, `signin`, `auth`, `oauth` ou `sso`.
  - **Classificação (R3)**: inclui `httpx.TooManyRedirects` → `erro_requisicao` e a inspeção da cadeia `__cause__`/`__context__` para identificar `ssl.SSLError` → `erro_tls`.
  - **Medições**: `latencia_ms` medida com `relogio.monotonic()` do envio até o fim da leitura; `coletado_em = relogio.agora()` no início da consulta.
  - **Corpo de 2xx**: JSON não truncado que falha em `json.loads` dá `resposta_invalida`; resposta truncada não é validada (R1).
  - **Fora do escopo aqui**: `amostra=None` (a US2 preenche).
  - **Privacidade**: `detalhe_causa` é uma mensagem curta, sem conteúdo do corpo, e nenhum corpo é gravado em disco (FR-016).

  Fazer T011 passar.
- [X] T018 [P] [US1] Implementar `experiments/python/discovery/src/inventario_fontes/avaliacao.py`: `grau_sugerido(fonte, resultado) -> tuple[Grau, str]` (R11) e `divergencias(fonte, resultado) -> tuple[Divergencia, ...]` (R12). A hipótese textual `hipotese_acesso` não é comparada. Fazer T012 passar.
- [X] T019 [US1] Implementar `experiments/python/discovery/src/inventario_fontes/execucao.py`:
  - **Assinatura**: `executar(catalogo, fontes, config, cliente, relogio, ao_progresso=None, filtros=None) -> Execucao`.
  - **Ritmo**: laço sequencial; antes de cada sonda (exceto a primeira com URL), espera `max(0, intervalo_s - (monotonic() - fim_anterior))` via `relogio.esperar`. Fontes sem `url_teste` viram `sem_teste` sem consulta e sem espera.
  - **Avaliação**: aplica `avaliacao` a cada resultado.
  - **Interrupção (R10)**: captura `KeyboardInterrupt`, marca as fontes restantes como `nao_executada` e devolve `Execucao(interrompida=True)` em vez de propagar. O CLI decide o código 130.
  - **Execução**: preenche `iniciada_em`/`finalizada_em`, `resumo`, `configuracao`, `aviso` (texto da FR-020: "A sondagem mostra a conectividade de um endereço numa data; licença, limites e termos de uso só se confirmam na documentação oficial.") e `ferramenta = "inventario-fontes <versão>"`.

  Fazer T013 passar.
- [X] T020 [P] [US1] Implementar `experiments/python/discovery/src/inventario_fontes/relatorio/json_.py`:
  - `para_dict(execucao) -> dict`, com enums como valor e datas UTC em ISO com milissegundos e sufixo `Z`;
  - `caminho_relatorio(saida: Path, iniciada_em, extensao) -> Path`, no formato `inventario-AAAAMMDDTHHMMSSZ.<ext>` com sufixo `-2`, `-3`... se o arquivo existir;
  - `gravar_json(execucao, caminho)`, com UTF-8, `ensure_ascii=False` e `indent=2`.

  Fazer T014 passar.
- [X] T021 [US1] Implementar `experiments/python/discovery/src/inventario_fontes/cli.py`:
  - **Argumentos**: `main(argv=None) -> int` com `argparse`, seguindo `contracts/cli.md`: `--catalogo`, `--saida`, `--intervalo`, `--tempo-limite` e `--versao`. Os filtros entram na US4.
  - **Erros de entrada**: erro de `Configuracao` dá código 2; `ErroCatalogo` vai para o `stderr` e dá código 1, antes de criar o cliente.
  - **Cliente HTTP**: `httpx.Client(timeout=tempo_limite_s, follow_redirects=True, max_redirects=5, headers={"User-Agent": f"laboratorio-brasil-aberto-inventario/{__version__}"})`, sem retries, usado como context manager.
  - **Saída**: imprime o progresso via `ao_progresso`, grava o JSON e imprime o resumo e os caminhos. Devolve `130` se `interrompida` e `0` nos demais casos.
  - **`__main__.py`**: conferir que chama `sys.exit(main())`.

  Fazer T015 passar.

**Checkpoint**: `uv run --project experiments/python/discovery inventario` gera o relatório JSON; a US1 está completa e testável sozinha.

---

## Phase 4: User Story 2 - Entender a estrutura dos dados sem guardar os dados (Priority: P2)

**Goal**: preencher `amostra` com campos e tipos inferidos de até 5 registros, sem reter nenhum valor.

**Independent Test**: resposta simulada com nomes e e-mails fictícios gera um relatório que lista os campos `nome` e `email` com seus tipos e não contém nenhum dos valores (SC-004).

### Tests for User Story 2 ⚠️

- [X] T022 [P] [US2] Escrever `experiments/python/discovery/tests/unit/test_amostra.py` (R5):
  - **JSON em lista**: `ibge_estados.json` dá `caminho_registros=None`, os campos `id`, `nome`, `sigla`, `regiao`, `regiao.id`, `regiao.nome`, `regiao.sigla` e `registros_inspecionados == 3`.
  - **Limite de registros**: lista de 27 registros dá `registros_inspecionados == 5`.
  - **JSON em objeto**: `camara_deputados.json` dá `caminho_registros == "dados"` e campos como `email` com tipo `texto`.
  - **Tipos**: a união por campo dá `["inteiro", "nulo"]` quando há valor nulo em um registro; `"2026-11-24"` e `"2026-11-24T10:00:00"` dão `data`; `1.5` dá `decimal`; `true` dá `booleano`.
  - **Notação de caminho**: listas aninhadas aparecem como `itens[].id`.
  - **Profundidade**: o limite de 5 níveis é respeitado.
  - **Amostras vazias ou indisponíveis**: `vazia.json` dá `vazia=True` e `campos=[]`; `truncada=True` com JSON dá `indisponivel_motivo == "resposta truncada"`.
  - **CSV e XML**: `dados.csv` dá as colunas com os tipos inferidos; `dados.xml` dá o caminho dos elementos filhos.
  - **Entrada malformada**: JSON quebrado lança `ErroAmostra`.
  - **Sem valores**: nenhuma string do resultado (`repr` da estrutura) contém valores da fixture.
- [X] T023 [P] [US2] Escrever `experiments/python/discovery/tests/integration/test_privacidade.py` (SC-004): `respx` serve `pessoas_ficticias.json` e `camara_deputados.json`; roda `executar` e `para_dict`. Coleta todos os valores folha (strings com 4 ou mais caracteres e números) das fixtures que não são nomes de chave, e verifica que nenhum aparece no JSON serializado.

### Implementation for User Story 2

- [X] T024 [US2] Implementar `experiments/python/discovery/src/inventario_fontes/amostra.py`:
  - **Assinatura**: `inferir_estrutura(corpo: bytes, formato: Formato, truncada: bool) -> EstruturaAmostra | None` (devolve `None` para `html`, `texto`, `vazio` e `outro`).
  - **JSON**: lista, ou objeto com chave cujo valor é lista de objetos (registrar `caminho_registros`).
  - **CSV**: `csv.reader` com o dialeto do `Sniffer`, cabeçalho e 5 linhas; o tipo de cada coluna é inferido do texto.
  - **XML**: `xml.etree.ElementTree.fromstring`, a raiz e os filhos dos 5 primeiros elementos repetidos.
  - **Tipos (R5)**: `bool` antes de `int`; `data` por regex ISO `^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2})?.*)?$`.
  - **Limites**: profundidade 5; campos ordenados por caminho.
  - **Falhas**: lança `ErroAmostra` se o conteúdo não se interpreta.

  Fazer T022 passar.
- [X] T025 [US2] Integrar a amostra em `experiments/python/discovery/src/inventario_fontes/sonda.py`. Para 2xx com formato `json`, `csv` ou `xml`, chamar `inferir_estrutura`; `ErroAmostra` dá `falhou/resposta_invalida`, substituindo a checagem de JSON da T017. Para resposta truncada, a amostra traz `indisponivel_motivo`, sem falha. Depois, rodar de novo T011, T014 e T023.

**Checkpoint**: relatório JSON com a estrutura da amostra; as US1 e US2 funcionam.

---

## Phase 5: User Story 3 - Relatório legível com hipótese versus observado (Priority: P3)

**Goal**: gerar o HTML autocontido ao lado do JSON, destacando as divergências.

**Independent Test**: a partir de uma `Execucao` de exemplo em que uma fonte tinha hipótese "nenhuma autenticação" e foi observada exigindo chave, o HTML destaca a divergência.

### Tests for User Story 3 ⚠️

- [X] T026 [P] [US3] Escrever `experiments/python/discovery/tests/unit/test_relatorio_html.py`, com uma `Execucao` montada à mão:
  - cada fonte vira uma linha com `data-fonte="<id>"`, contendo nome, domínio, grau do catálogo, grau sugerido, hipótese de acesso, resultado observado e link da documentação;
  - a linha com divergência de autenticação tem a classe `divergente` e mostra hipótese e observado;
  - `coletado_em` aparece em UTC e em horário de Brasília (`America/Sao_Paulo`);
  - o aviso da FR-020 e o resumo aparecem;
  - `nome` com `<script>alert(1)</script>` aparece escapado;
  - não há `<script` nem `<link`, e nenhum `src=` ou `href=` aponta para fora, exceto os links de documentação e URLs de teste;
  - `sem_teste` mostra "sem teste automatizado";
  - a amostra aparece como lista de `caminho: tipos`;
  - a contagem de linhas é igual a `len(resultados)`, e os mesmos `fonte_id` estão no JSON e no HTML (US3, cenário 3).

### Implementation for User Story 3

- [X] T027 [US3] Implementar `experiments/python/discovery/src/inventario_fontes/relatorio/html.py` (R7):
  - `renderizar_html(execucao) -> str` com `string.Template`, CSS inline e sem JavaScript;
  - uma função `_e()` centralizando o `html.escape` de todo texto vindo do catálogo ou da observação;
  - uma tabela por fonte, com destaque visual para `falhou` e `divergente` e um bloco expansível `<details>` para a amostra;
  - `gravar_html(execucao, caminho)`.

  Fazer T026 passar.
- [X] T028 [US3] Atualizar `experiments/python/discovery/src/inventario_fontes/cli.py` para gravar também o HTML, com o mesmo nome-base do JSON (FR-017, usando `caminho_relatorio` com a extensão `html` e o mesmo sufixo, se houver), e imprimir os dois caminhos (FR-021). Atualizar `tests/integration/test_cli.py` para exigir os dois arquivos e `tests/integration/test_privacidade.py` para checar também o HTML.

**Checkpoint**: execução gera JSON e HTML; as US1, US2 e US3 funcionam.

---

## Phase 6: User Story 4 - Rodar só uma parte do catálogo (Priority: P3)

**Goal**: filtros `--rodada` e `--fonte` (repetíveis, com interseção).

**Independent Test**: catálogo com rodadas 1 e 2 e `--rodada 1` consulta só a rodada 1; as rotas da rodada 2 têm `call_count == 0`.

### Tests for User Story 4 ⚠️

- [X] T029 [P] [US4] Escrever `experiments/python/discovery/tests/integration/test_filtros.py`, via `cli.main`, com `respx` e `catalogo_tmp`:
  - `--rodada 1` consulta só a rodada 1, sem chamadas às rotas da rodada 2;
  - `--rodada 1 --rodada 2` consulta as duas;
  - `--fonte a --fonte b` consulta só `a` e `b`;
  - `--rodada 1 --fonte x` usa a interseção;
  - `--fonte nao-existe` dá código `2`, mensagem no `stderr` e nenhuma requisição;
  - um filtro sem nenhuma fonte dá código `2`;
  - `filtros.rodadas` e `filtros.fontes` aparecem no relatório;
  - o resumo conta só as fontes filtradas.

### Implementation for User Story 4

- [X] T030 [US4] Adicionar `filtrar(fontes, rodadas: list[int], ids: list[str]) -> list[Fonte]` em `experiments/python/discovery/src/inventario_fontes/catalogo.py`, lançando `ValueError` com os ids inexistentes. Adicionar `--rodada` (`action="append"`, `type=int`) e `--fonte` (`action="append"`) em `experiments/python/discovery/src/inventario_fontes/cli.py`, repassando `filtros` a `executar`. Fazer T029 passar.

**Checkpoint**: todas as histórias funcionam de forma independente.

---

## Phase 7: Polish & Fechamento do experimento

**Purpose**: validar de ponta a ponta, rodar contra as fontes reais e fechar o E0.

- [ ] T031 Rodar `uv run --project experiments/python/discovery pytest` com a rede desligada (Wi-Fi off) e confirmar que todos os testes passam (SC-007). Registrar o resultado no `RESULTS.md` (T036).
- [ ] T032 Execução real manual (quickstart §2): `uv run --project experiments/python/discovery inventario --rodada 1`. Medir o tempo total (SC-001, < 1 min), confirmar as 4 fontes no relatório (SC-002) e versionar o JSON gerado em `discovery/reports/` (o HTML é ignorado pelo `.gitignore`).
- [ ] T033 Validar o relatório real conforme o quickstart §3 e §4: SC-006 (responder as 4 perguntas lendo só o HTML), ausência de nomes de deputados na amostra da Câmara e os comandos de filtro e de erro com seus códigos de saída. Anotar no `RESULTS.md` o que divergir do esperado.
- [ ] T034 [P] Preencher as fichas a partir de `discovery/fichas/_TEMPLATE.md`: `discovery/fichas/ibge-localidades.md`, `discovery/fichas/bcb-sgs.md`, `discovery/fichas/bcb-ifdata.md` e `discovery/fichas/camara-dados-abertos.md`. Em cada uma, a seção "Resultado do teste de conectividade" vem do relatório. As demais respostas vêm da documentação oficial, marcadas como confirmado, parcial ou não verificado.
- [ ] T035 Propor ao usuário as atualizações de `verification` em `discovery/sources.json`, seguindo o `verificacao_sugerida` e a sua justificativa no relatório (FR-003: alteração manual, com escopo "conectividade e autenticação" anotado em `notes`), e aplicar só as aprovadas.
- [ ] T036 Copiar `docs/templates/RESULTS.md` para `specs/001-inventario-fontes/RESULTS.md` e preencher com a resposta à pergunta do experimento, as dificuldades, os resultados (com o link para o relatório JSON), as limitações (heurística de login, teto de 1 MiB, XML sem `defusedxml`) e os próximos passos (decisão do E1). Marcar o checklist de conclusão da constituição.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup e bloqueia todas as histórias.
- **US1 (Phase 3)**: depende da Phase 2. É o MVP.
- **US2 (Phase 4)**: depende da Phase 2. T024 é independente, mas T025 altera `sonda.py`, então exige T017 concluída.
- **US3 (Phase 5)**: T026 e T027 dependem só dos modelos (Phase 2). T028 altera `cli.py`, então exige T021.
- **US4 (Phase 6)**: T030 altera `cli.py` e `catalogo.py`, então exige T021 e T009.
- **Polish (Phase 7)**: depende das histórias desejadas. T032 a T036 exigem a ferramenta funcionando.

### User Story Dependencies

- **US1 (P1)**: independente após a fundação.
- **US2 (P2)**: lógica independente (`amostra.py`); a integração usa o `sonda.py` da US1.
- **US3 (P3)**: renderização independente; a integração usa o `cli.py` da US1.
- **US4 (P3)**: estende o `cli.py` da US1.

### Within Each User Story

- Testes antes da implementação, falhando primeiro.
- Modelos (Phase 2) → módulos puros (`formato`, `avaliacao`, `amostra`, `relatorio`) → `sonda` → `execucao` → `cli`.

### Parallel Opportunities

- **Phase 1**: T003 em paralelo com T001/T002.
- **Phase 2**: T006, T007 e T008 em paralelo, depois de T005.
- **US1**: T010 a T015 (testes) em paralelo; T016, T018 e T020 em paralelo; T017 → T019 → T021 em sequência.
- **Entre histórias**: depois da Phase 2, T022/T024 (US2) e T026/T027 (US3) podem avançar em paralelo à US1.
- **Polish**: T034 em paralelo com T035.

---

## Parallel Example: User Story 1

```bash
# Testes da US1 juntos:
Task: "T010 test_formato.py em experiments/python/discovery/tests/unit/"
Task: "T011 test_sonda.py em experiments/python/discovery/tests/unit/"
Task: "T012 test_avaliacao.py em experiments/python/discovery/tests/unit/"
Task: "T013 test_execucao.py em experiments/python/discovery/tests/integration/"
Task: "T014 test_relatorio_schema.py em experiments/python/discovery/tests/contract/"
Task: "T015 test_cli.py em experiments/python/discovery/tests/integration/"

# Módulos puros da US1 juntos:
Task: "T016 formato.py"
Task: "T018 avaliacao.py"
Task: "T020 relatorio/json_.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 e Phase 2.
2. Phase 3 (US1).
3. **Parar e validar**: `pytest` passa e a execução real da rodada 1 gera um JSON válido. Isso já responde "quem responde, com que autenticação e em que formato".

### Incremental Delivery

1. Setup + fundação.
2. US1: relatório JSON (MVP).
3. US2: estrutura da amostra.
4. US3: HTML legível com divergências.
5. US4: filtros.
6. Fechamento (T031 a T036): relatório real, fichas, `RESULTS.md` e decisão do E1.

---

## Notes

- `[P]` = arquivos diferentes, sem dependência pendente.
- Testes nunca acessam a rede: o `conftest.py` bloqueia sockets, e toda resposta vem do `respx`.
- Fixtures só com dados sintéticos ou respostas reais reduzidas, sem dados pessoais reais.
- O `tasks.md` é a fonte da verdade. As issues do GitHub Project nº 6 espelham as fases (uma issue por fase/história) e são sincronizadas após cada `/speckit-implement` ou `/speckit-converge`.
- Faça commit após cada tarefa ou grupo lógico, sem atribuição ao Claude nas mensagens.

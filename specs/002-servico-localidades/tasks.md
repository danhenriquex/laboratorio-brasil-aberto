---

description: "Lista de tarefas do E1 — Serviço de localidades (IBGE)"
---

# Tasks: E1 — Serviço de localidades (IBGE)

**Input**: Documentos de design em `specs/002-servico-localidades/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/localidades/openapi.yaml](../../contracts/localidades/openapi.yaml), [quickstart.md](quickstart.md)

**Tests**: incluídos. A spec exige verificação sem rede (FR-021, FR-027, SC-002, SC-004 a SC-006, SC-008), e a constituição (princípio IV) proíbe rede nos testes. Há duas camadas:
- testes da implementação, em `experiments/python/localidades/tests/` (`TestClient` + `respx`);
- a suíte de caixa-preta, em `contracts/localidades/verificacao/tests/`, que valida cada resposta contra o `openapi.yaml` e será reaproveitada no E4.

Em cada história, escreva os testes primeiro e confirme que falham.

**Organization**: tarefas agrupadas por história de usuário; cada história é um incremento testável.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: história de usuário da spec (US1 a US5)

## Path Conventions

- **Serviço (E1):** `experiments/python/localidades/`.
  - Código: `src/localidades/`
  - Testes: `tests/`
  - Comandos: `uv run --project experiments/python/localidades ...`
- **Contrato e suíte de caixa-preta (compartilhados com o E4):** `contracts/localidades/`.
  - Contrato: `openapi.yaml`
  - Fixtures: `fixtures-ibge/`
  - Suíte: `verificacao/`, com comandos `uv run --project contracts/localidades/verificacao ...`
- Todos os caminhos abaixo partem da raiz do repositório.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: criar os dois projetos `uv` e os esqueletos.

- [X] T001 Criar `experiments/python/localidades/pyproject.toml`:
  - projeto `localidades-ibge`, versão `0.1.0`, `requires-python = ">=3.11"`, build `hatchling` com layout `src/`;
  - dependências de runtime: `fastapi`, `uvicorn`, `httpx` e `prometheus-client`;
  - grupo `dev`: `pytest` e `respx`;
  - script `localidades = "localidades.__main__:main"`;
  - `[tool.pytest.ini_options]` com `testpaths = ["tests"]` e `addopts = "-q"`.
- [X] T002 Criar o esqueleto em `experiments/python/localidades/`:
  - `src/localidades/__init__.py` com `__version__ = "0.1.0"`;
  - `src/localidades/__main__.py` com `main()`, que lê a configuração e chama `uvicorn.run(criar_app(config), host=config.host, port=config.porta)`. Fica como esboço até T011 e T015;
  - as pastas `tests/unit/` e `tests/integration/`.
- [X] T003 [P] Criar `contracts/localidades/verificacao/pyproject.toml`:
  - projeto `verificacao-localidades`, versão `0.1.0`, `requires-python = ">=3.11"`, `hatchling` com layout `src/`;
  - dependências: `pytest`, `httpx`, `jsonschema`, `pyyaml` e `openapi-spec-validator`;
  - script `ibge-falso = "ibge_falso.__main__:main"`;
  - os arquivos `src/ibge_falso/__init__.py` e `src/ibge_falso/__main__.py` (esboço) e a pasta `tests/`.
- [X] T004 [P] Criar `experiments/python/localidades/README.md` com:
  - a pergunta do E1;
  - os comandos de teste, de execução e de verificação;
  - a tabela de variáveis `LOCALIDADES_*`, apontando para `contracts/localidades/README.md` e `specs/002-servico-localidades/quickstart.md`.
- [X] T005 Rodar `uv sync --project experiments/python/localidades` e `uv sync --project contracts/localidades/verificacao`, e versionar os dois `uv.lock`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: fixtures, domínio, configuração, erros, cliente do IBGE, base da API e base da suíte de caixa-preta.

**⚠️ CRITICAL**: nenhuma história começa antes desta fase terminar.

### Fixtures do IBGE (verificação manual com chamada real)

- [X] T006 Gravar as respostas reais do IBGE em `contracts/localidades/fixtures-ibge/`, com o script `contracts/localidades/fixtures-ibge/gravar.py`.
  - **Como o script consulta:** usa `urllib` da biblioteca padrão, User-Agent `laboratorio-brasil-aberto-localidades/0.1.0`, chamadas em sequência com 2 s de intervalo, e grava o corpo exatamente como recebido. É uma execução manual, fora dos testes (Constituição IV).
  - **Arquivos gravados:**
    - `estados.json`, de `/estados`;
    - `municipios-uf-33.json` (RJ), `municipios-uf-35.json` (SP) e `municipios-uf-53.json` (DF), de `/estados/{codigo}/municipios`;
    - `municipio-5101837.json`, de `/municipios/5101837`, o município com `microrregiao: null` (R1).
  - **Fixtures sintéticas, à mão:**
    - `erro.html`: página HTML de erro;
    - `municipio-sem-regiao-imediata.json`: o objeto de `3304557` sem a chave `regiao-imediata`;
    - `estados-sem-regiao.json`: `estados` com um item sem `regiao`.
  - **`README.md` da pasta:** data e hora UTC da gravação, URL, tamanho e SHA-256 de cada arquivo, e a observação de que são dados públicos sem dados pessoais.

### Testes da fundação (escrever primeiro)

- [X] T007 [P] Criar `experiments/python/localidades/tests/conftest.py` com:
  - **bloqueio de rede:** um monkeypatch de `socket.socket.connect` e `socket.getaddrinfo` que recusa qualquer destino fora de `127.0.0.1`, `::1` e `localhost`;
  - **`RelogioFalso`:** `agora()` devolve um `datetime` UTC, `monotonic()` devolve um `float`, e `avancar(segundos)` adianta os dois;
  - **`ler_fixture(nome)`:** lê de `contracts/localidades/fixtures-ibge/`, localizado a partir de `Path(__file__)` subindo até a raiz do repositório;
  - **constante `IBGE`:** `https://servicodados.ibge.gov.br/api/v1/localidades`;
  - **fixture `mock_ibge`:** `respx.mock(base_url=IBGE, assert_all_called=False)`.
- [X] T008 [P] Escrever `experiments/python/localidades/tests/unit/test_dominio.py`, cobrindo:
  - **`dobrar`:** `"Niterói"` vira `"niteroi"`, `"SÃO"` vira `"sao"`, e o apóstrofo é mantido;
  - **ordenação:** pela chave `(dobrar(nome), codigo)`;
  - **`filtrar_por_nome`:** por substring do nome dobrado, depois de aparar;
  - **`paginar`:**
    - `paginas = ceil(total / itens)`, e `total` = 0 dá `paginas` = 0;
    - uma página além do fim devolve lista vazia com o total correto;
  - **`resolver_uf`:**
    - `" rj "` e `"33"` resolvem para `"33"`;
    - `"XX"` e `"99"` levantam `NaoEncontrado`;
    - `"R1"`, `"123"` e `""` levantam `EntradaInvalida`;
  - **`validar_codigo_municipio`:** `^\d{7}$`;
  - **`validar_paginacao`:** `pagina` ≥ 1 e `itens` de 1 a `itens_max`. Os erros levantam `EntradaInvalida`, e o detalhe cita o limite;
  - **`validar_nome`:** aparado, de 2 a 60 caracteres.
- [X] T009 [P] Escrever `experiments/python/localidades/tests/unit/test_config.py`, cobrindo:
  - os padrões de R14: `127.0.0.1`, `8000`, a URL do IBGE, `10`, `86400` e `500`;
  - a leitura de cada variável `LOCALIDADES_*`;
  - valores não numéricos, zero ou negativos, que levantam `ValueError` com o nome da variável.
- [X] T010 [P] Escrever `experiments/python/localidades/tests/unit/test_fonte_ibge.py` com `respx` e as fixtures de T006.
  - **Classificação de R6:**

    | Situação simulada | Erro esperado |
    |---|---|
    | `httpx.ConnectError` | `FonteIndisponivel` |
    | status 503 e 429 | `FonteIndisponivel` |
    | `httpx.ReadTimeout` | `FonteLenta` |
    | resposta que demora mais que o prazo total (`side_effect` assíncrono com `asyncio.sleep(0.2)` e prazo de `0.05`) | `FonteLenta` |
    | HTML com status 200 | `RespostaInesperadaDaFonte` |
    | status 404 | `RespostaInesperadaDaFonte` |
    | JSON sem campo obrigatório (`estados-sem-regiao.json`, `municipio-sem-regiao-imediata.json`) | `RespostaInesperadaDaFonte` |

  - **Normalização:**
    - `obter_estados()` devolve 27 UFs com códigos em texto (`"33"`) e região com código `"3"`;
    - `obter_municipios_da_uf("33")` devolve 92 `MunicipioResumido` com `codigo` de 7 dígitos em texto, e `[]` vira `RespostaInesperadaDaFonte`;
    - `obter_municipio(codigo)`:
      - aceita um objeto ou uma lista de exatamente 1 objeto (montados a partir de um item de `municipios-uf-33.json`);
      - `[]` vira `NaoEncontrado`;
      - `municipio-5101837.json` (com `microrregiao: null`) é aceito;
  - **Demais garantias:**
    - cada método devolve também a `url_fonte` consultada;
    - o User-Agent é o do laboratório;
    - cada chamada faz exatamente 1 pedido, sem nova tentativa (FR-017).

### Implementação da fundação

- [X] T011 Implementar `experiments/python/localidades/src/localidades/config.py`:
  - `Configuracao` como `@dataclass(frozen=True)`, com os campos `host`, `porta`, `ibge_url`, `prazo_fonte_s`, `validade_s` e `itens_max`;
  - `Configuracao.do_ambiente(env=os.environ)`, com os padrões e a validação de R14;
  - mensagens claras de erro com o nome da variável (faz T009 passar).
- [X] T012 [P] Implementar `experiments/python/localidades/src/localidades/erros.py`:
  - a base `ErroDominio(detalhe)`, com os atributos de classe `tipo`, `titulo` e `status`;
  - as subclasses:

    | Classe | Tipo | Status |
    |---|---|---|
    | `EntradaInvalida` | `entrada-invalida` | 400 |
    | `NaoEncontrado` | `nao-encontrado` | 404 |
    | `FonteIndisponivel` | `fonte-indisponivel` | 502 |
    | `FonteLenta` | `fonte-lenta` | 504 |
    | `RespostaInesperadaDaFonte` | `resposta-inesperada-da-fonte` | 502 |
    | `ErroInterno` | `erro-interno` | 500 |

  - a propriedade `urn`, que devolve `urn:brasil-aberto:problema:{tipo}` (R11);
  - o agrupamento `ERROS_DE_FONTE = (FonteIndisponivel, FonteLenta, RespostaInesperadaDaFonte)`.
- [X] T013 Implementar `experiments/python/localidades/src/localidades/dominio.py`, conforme `data-model.md`, para fazer T008 passar:
  - **dataclasses `frozen`:** `Regiao`, `Uf`, `UfResumida`, `RegiaoImediata`, `RegiaoIntermediaria`, `MunicipioResumido`, `Municipio` e `Pagina(itens, pagina, tamanho, total, paginas)`;
  - **`UFS_OFICIAIS`:** a tabela fixa de 27 códigos e siglas do data-model;
  - **funções:**
    - `dobrar(s)`: NFKD, remoção da categoria `Mn` e `casefold`;
    - `chave_ordenacao`;
    - `ordenar`;
    - `filtrar_por_nome`;
    - `paginar`;
    - `resolver_uf(param) -> str`: devolve o código;
    - `validar_codigo_municipio`;
    - `validar_paginacao(pagina, itens, itens_max)`;
    - `validar_nome`.
  - **Regras a respeitar à risca:**

    | Campo | Regra |
    |---|---|
    | `{codigo}` | `^\d{7}$` |
    | `itens` | inteiro de 1 a `ITENS_MAX` (padrão 500) |
    | `nome` | aparado, de 2 a 60 caracteres |
    | `{uf}` | aparado; `^[A-Za-z]{2}$` (sigla, comparada em maiúsculas) ou `^\d{2}$` (código) |

  - Este módulo não importa FastAPI nem httpx.
- [X] T014 Implementar `experiments/python/localidades/src/localidades/fonte_ibge.py`, para fazer T010 passar:
  - **`ClienteIBGE(config, cliente_http: httpx.AsyncClient | None = None, ao_medir=None)`**, com os métodos assíncronos `obter_estados()`, `obter_municipios_da_uf(codigo_uf)` e `obter_municipio(codigo)`. Cada um devolve `(dados_normalizados, url_fonte)`;
  - **`_buscar_json(recurso)`:**
    - faz uma única chamada GET dentro de `asyncio.timeout(config.prazo_fonte_s)`;
    - o httpx recebe o mesmo prazo por fase;
    - nenhuma nova tentativa;
    - classifica as falhas conforme a tabela de R6;
    - chama `ao_medir(recurso, segundos)` para as métricas, com `recurso` igual a `estados`, `municipios_da_uf` ou `municipio`;
  - **normalização:** conforme "Validação da resposta do IBGE" do data-model, convertendo os códigos para texto de tamanho fixo (R7);
  - **`microrregiao`:** é ignorada e pode vir `null`;
  - **mensagens de erro:** nunca incluem o corpo da resposta do IBGE.
- [X] T015 Implementar a base de `experiments/python/localidades/src/localidades/api.py`, com `criar_app(config, *, cliente_ibge=None, relogio=None) -> FastAPI`:
  - **OpenAPI automático desligado:** `openapi_url=None`, `docs_url=None` e `redoc_url=None` (R3);
  - **middleware de correlação (R12):**
    - aceita `X-Correlation-Id` que case com `^[A-Za-z0-9._-]{1,64}$` e, caso contrário, gera um UUID v4;
    - guarda o valor em `request.state.correlacao_id` e o devolve no cabeçalho de **toda** resposta;
  - **handlers de erro, todos em `application/problem+json` com `correlacao_id`:**
    - `ErroDominio` vira um problema com `type` (URN), `title`, `status` e `detail`;
    - `RequestValidationError` vira 400 `entrada-invalida`, com o campo no `detail`;
    - 404 e 405 do Starlette viram 404 `nao-encontrado`;
    - `Exception` vira 500 `erro-interno`, com o `detail` genérico "erro interno do serviço";
  - **`GET /health`:** devolve `{"status": "ok"}` sem tocar no IBGE;
  - **respostas JSON:** com `ensure_ascii=False`, ou seja, UTF-8.
- [X] T016 Escrever e fazer passar `experiments/python/localidades/tests/integration/test_api_base.py`, cobrindo:
  - `/health` devolve 200;
  - `/v2/ufs`, `/ufs` e `/nada` devolvem 404 `nao-encontrado` em `application/problem+json`;
  - o `X-Correlation-Id` é devolvido igual quando válido e trocado por um UUID v4 quando inválido (65 caracteres ou com espaço);
  - um erro forçado numa rota de teste vira 500 sem rastro de execução no corpo.
- [X] T017 Implementar a base de `experiments/python/localidades/src/localidades/servico.py`:
  - **`ServicoLocalidades(cliente_ibge, relogio, config)`:** não importa FastAPI;
  - **`Resultado(dados, meta, paginacao=None)`;**
  - **`Meta`:**
    - `fonte` = `"IBGE — API de localidades"`;
    - `url_fonte`;
    - `url_documentacao` = `"https://servicodados.ibge.gov.br/api/docs/localidades"`;
    - `coletado_em`, formatado como ISO 8601 UTC com milissegundos e `Z`;
    - `desatualizado`;
  - **`_obter(chave, buscar)`:** nesta fase, chama a fonte direto e usa `relogio.agora()` como `coletado_em`. A cópia guardada entra em T034;
  - **`RelogioSistema`:** `agora()` em UTC, `monotonic()` e `esperar()`.

### Base da suíte de caixa-preta

- [X] T018 Implementar o IBGE falso em `contracts/localidades/verificacao/src/ibge_falso/servidor.py` e `__main__.py`:
  - **servidor:** `ThreadingHTTPServer` da biblioteca padrão, em `127.0.0.1`, com a porta definida por `--porta` (padrão 8099) e as fixtures em `--fixtures` (padrão `contracts/localidades/fixtures-ibge/`, resolvido a partir do arquivo);
  - **rotas, sob `/api/v1/localidades`:**
    - `/estados` serve `estados.json`;
    - `/estados/{c}/municipios` serve `municipios-uf-{c}.json` e devolve `[]` para qualquer outra UF;
    - `/municipios/{c}` procura o item nas listas por UF ou usa `municipio-{c}.json` e, se não achar, devolve `[]`;
  - **demais caminhos:** 404;
  - **respostas:** `Content-Type: application/json; charset=utf-8`.
- [X] T019 Criar a base da suíte em `contracts/localidades/verificacao/tests/`:
  - **`contrato.py`:**
    - carrega `contracts/localidades/openapi.yaml` com `yaml.safe_load`;
    - `validar(resposta, metodo, rota_modelo)` confere:
      - que o status está declarado para a rota;
      - que o `Content-Type` é `application/json` ou `application/problem+json`, conforme o contrato;
      - que o `X-Correlation-Id` casa com o padrão;
      - que o corpo valida contra o schema da resposta, usando `jsonschema.Draft202012Validator` com um `referencing.Registry` sobre o documento OpenAPI;
  - **`conftest.py`:**
    - `servico = httpx.Client(base_url=os.environ["LOCALIDADES_URL"], timeout=10)`;
    - `ibge = httpx.Client(base_url=os.environ.get("IBGE_FALSO_URL", "http://127.0.0.1:8099"))`;
  - **`test_contrato_valido.py`:** o `openapi-spec-validator` aceita o `openapi.yaml`.
- [X] T020 Criar `contracts/localidades/verificacao/verificar.sh` (executável), que recebe o comando do serviço como `$1` e:
  1. sobe o IBGE falso na porta 8099;
  2. sobe o serviço com `LOCALIDADES_PORTA=8090`, `LOCALIDADES_IBGE_URL=http://127.0.0.1:8099/api/v1/localidades`, `LOCALIDADES_PRAZO_FONTE_S=1` e `LOCALIDADES_VALIDADE_S=2`;
  3. espera o `/health` por até 30 s;
  4. roda `uv run --project contracts/localidades/verificacao pytest contracts/localidades/verificacao/tests` com `LOCALIDADES_URL=http://127.0.0.1:8090`;
  5. encerra os dois processos com `trap` e sai com o código do pytest.

  O script respeita `UV_OFFLINE`, quando estiver definida.

**Checkpoint**: `uv run --project experiments/python/localidades pytest` passa (domínio, configuração, fonte e base da API), e o `verificar.sh` sobe tudo e passa no `test_contrato_valido.py`.

---

## Phase 3: User Story 1 - Listar estados e os municípios de um estado (Priority: P1) 🎯 MVP

**Goal**: `GET /v1/ufs`, `GET /v1/ufs/{uf}` e `GET /v1/ufs/{uf}/municipios` (sem o filtro por nome), paginados e com procedência.

**Independent Test**: com o IBGE simulado, listar as UFs e os municípios do RJ. As respostas seguem o contrato e trazem `meta`.

### Tests for User Story 1 ⚠️

- [X] T021 [P] [US1] Escrever `experiments/python/localidades/tests/integration/test_api_ufs.py` (`TestClient` + `respx`), cobrindo:
  - **`/v1/ufs`:** 27 UFs ordenadas por `dobrar(nome)` (Acre primeiro), códigos em texto, `meta` completo, e `coletado_em` casando com `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$`;
  - **`/v1/ufs/{uf}`:**
    - `/v1/ufs/rj`, `/v1/ufs/33` e `/v1/ufs/%20RJ%20` devolvem o RJ;
    - `/v1/ufs/XX` e `/v1/ufs/99` devolvem 404 sem chamar o IBGE;
    - `/v1/ufs/R1` devolve 400 sem chamar o IBGE;
  - **`/v1/ufs/RJ/municipios`:**
    - 92 itens em ordem alfabética, cada um só com `codigo` e `nome`;
    - `paginacao` igual a `{pagina: 1, itens: 100, total: 92, paginas: 1}`;
    - `itens=10&pagina=10` devolve 2 itens;
    - `pagina=20` devolve `dados: []` com `total: 92`;
    - `itens=0`, `itens=501` e `pagina=0` devolvem 400, e o `detail` cita o limite;
    - `[]` do IBGE para o RJ devolve 502 `resposta-inesperada-da-fonte`;
  - **consultas à fonte:** cada pedido válido faz exatamente 1 chamada ao IBGE.
- [X] T022 [P] [US1] Escrever `contracts/localidades/verificacao/tests/test_us1_ufs_municipios.py`, com cada resposta validada por `contrato.validar(...)`:
  - os cenários de aceitação 1 a 4 da US1;
  - os casos de borda:
    - DF, com 1 município (`5300108`);
    - SP com `itens=500&pagina=2`, que devolve o restante, com `paginas` = 2;
    - página além do fim;
    - sigla minúscula e com espaços;
    - `itens` acima do máximo.

### Implementation for User Story 1

- [X] T023 [US1] Em `experiments/python/localidades/src/localidades/servico.py`, implementar:
  - `listar_ufs()`: ordenadas;
  - `obter_uf(param)`: `resolver_uf` e depois a busca na lista do IBGE. Uma UF ausente da lista vira `RespostaInesperadaDaFonte`;
  - `listar_municipios(param_uf, pagina, itens)`:
    1. valida a paginação;
    2. resolve a UF;
    3. busca `estados/{codigo}/municipios`;
    4. ordena;
    5. pagina.
- [X] T024 [US1] Em `experiments/python/localidades/src/localidades/api.py`, criar as rotas `GET /v1/ufs`, `GET /v1/ufs/{uf}` e `GET /v1/ufs/{uf}/municipios`:
  - os parâmetros `pagina` e `itens` são inteiros opcionais, validados pelo domínio e não pelo FastAPI, para que o `detail` cite `itens_max`;
  - os envelopes seguem `{dados, meta}` e `{dados, paginacao, meta}`, como no data-model.

  Ao final, T021 e T022 passam.

**Checkpoint**: US1 funcional e verificada pela suíte de caixa-preta. Isso é o MVP.

---

## Phase 4: User Story 2 - Consultar um município pelo código oficial (Priority: P1)

**Goal**: `GET /v1/municipios/{codigo}`, com UF, região imediata e região intermediária.

**Independent Test**: consultar um código existente, um inexistente e um mal formado.

### Tests for User Story 2 ⚠️

- [X] T025 [P] [US2] Escrever `experiments/python/localidades/tests/integration/test_api_municipio.py`, cobrindo:
  - **código existente** (`3304557`, montado a partir do item de `municipios-uf-33.json`): `codigo`, `nome`, `uf{codigo: "33", sigla: "RJ", nome}`, `regiao_imediata{codigo de 6 dígitos, nome}` e `regiao_intermediaria{codigo de 4 dígitos, nome}`;
  - **casos de erro e de formato:**
    - `9999999`, com o IBGE respondendo `[]`, devolve 404;
    - `12ab`, `123456` e `12345678` devolvem 400 com 0 chamadas ao IBGE;
    - um município de SP com apóstrofo no nome sai idêntico ao da fixture;
    - `5101837` responde 200;
    - `municipio-sem-regiao-imediata.json` devolve 502.
- [X] T026 [P] [US2] Escrever `contracts/localidades/verificacao/tests/test_us2_municipio.py`, com os cenários 1 a 4 da US2 validados contra o contrato. Os códigos vêm das listas de RJ e SP das fixtures.

### Implementation for User Story 2

- [X] T027 [US2] Em `experiments/python/localidades/src/localidades/servico.py`, implementar `obter_municipio(codigo)`: `validar_codigo_municipio`, depois a chave `municipios/{codigo}` e `NaoEncontrado` quando a fonte devolver `[]`.
- [X] T028 [US2] Em `experiments/python/localidades/src/localidades/api.py`, criar a rota `GET /v1/municipios/{codigo}` com o envelope `{dados, meta}`. Ao final, T025 e T026 passam.

**Checkpoint**: US1 e US2 funcionam de forma independente.

---

## Phase 5: User Story 3 - Comportamento previsível quando o IBGE falha ou demora (Priority: P2)

**Goal**: cópia guardada com validade, consulta única por chave, cópia vencida em caso de falha e erros de fonte padronizados.

**Independent Test**: com o IBGE falso nos modos `fora`, `lento` e `invalido`, com e sem cópia guardada, conferir o tipo de erro, o tempo e a marcação `desatualizado`.

### Tests for User Story 3 ⚠️

- [X] T029 [P] [US3] Escrever `experiments/python/localidades/tests/unit/test_cache.py`, com `RelogioFalso` e uma função `buscar` falsa que conta as chamadas:
  - **entrada válida:** atende sem chamar `buscar`;
  - **entrada vencida:**
    - se `buscar` der certo, renova o `coletado_em`;
    - se `buscar` levantar um erro de `ERROS_DE_FONTE`, devolve a cópia com `desatualizado=True` e o `coletado_em` original;
  - **entrada ausente com falha:** propaga o erro;
  - **o que não é guardado:** `NaoEncontrado` (a chamada seguinte consulta de novo) e os erros;
  - **consulta única por chave:** 10 chamadas simultâneas, com `asyncio.gather` dentro de `asyncio.run` e uma `buscar` que dorme 0,05 s, fazem `buscar` ser chamada 1 vez.
- [X] T030 [P] [US3] Escrever `experiments/python/localidades/tests/integration/test_api_falhas.py` (`TestClient` + `respx`), cobrindo:
  - **sem cópia guardada:**
    - fonte fora (`ConnectError`) devolve 502 `fonte-indisponivel`;
    - fonte lenta devolve 504 `fonte-lenta`;
    - HTML com status 200 devolve 502 `resposta-inesperada-da-fonte`;
    - em nenhum desses casos o `detail` contém o corpo do IBGE, `Traceback` ou endereços internos;
  - **com cópia guardada:**
    - com a cópia vencida (`RelogioFalso.avancar(validade + 1)`), a fonte fora devolve 200, `meta.desatualizado: true` e o `coletado_em` original;
    - dois pedidos dentro da validade geram 1 chamada ao IBGE;
  - **isolamento:** depois de uma falha, o pedido seguinte para outro recurso funciona (FR-018).
- [X] T031 [P] [US3] Escrever `contracts/localidades/verificacao/tests/test_us3_falhas.py`, com cada resposta validada contra o contrato e cada cenário usando um código de município diferente, porque o serviço guarda cópias entre testes:
  - **SC-004:** dois pedidos iguais seguidos geram 1 consulta em `/_controle/contagem`;
  - **SC-003:** o pedido repetido responde em menos de 0,5 s;
  - **SC-005:** nos modos `fora`, `lento` (3 s) e `invalido`, sem cópia, a resposta é 502, 504 ou 502 em menos de 2 s, com o prazo de 1 s;
  - **cópia vencida:** pede um código, espera 2,2 s (validade de 2 s), põe a fonte em `fora` e pede de novo. Resposta esperada: 200 com `desatualizado: true` e o mesmo `coletado_em`;
  - **consulta única por chave:** no modo `lento` de 0,5 s, 10 pedidos simultâneos, disparados com threads, pelo mesmo código novo geram 1 consulta;
  - **limpeza:** uma fixture `autouse` volta o IBGE falso para `normal` depois de cada teste.

### Implementation for User Story 3

- [X] T032 [US3] Acrescentar o controle a `contracts/localidades/verificacao/src/ibge_falso/servidor.py`:
  - **`POST /_controle`**, com o corpo `{"modo": "normal" | "fora" | "lento" | "invalido", "segundos": float}`:
    - `fora` responde 503;
    - `lento` espera `segundos` antes de responder normalmente;
    - `invalido` responde `erro.html` com status 200 e `text/html`;
  - **`GET /_controle/contagem`:** devolve `{caminho: n}`;
  - **`POST /_controle/zerar`:** zera as contagens;
  - **concorrência:** o estado é protegido por `threading.Lock`.
- [X] T033 [US3] Implementar `experiments/python/localidades/src/localidades/cache.py`, conforme os estados do data-model (ausente, válida, vencida), para fazer T029 passar:
  - `CacheComValidade(relogio, validade_s)`;
  - `async obter(chave, buscar) -> Entrada(dados, url_fonte, coletado_em, desatualizado, resultado)`, em que `resultado` é `acerto`, `falta` ou `desatualizado`;
  - um `asyncio.Lock` por chave;
  - `NaoEncontrado` e erros nunca entram na cópia;
  - um erro de `ERROS_DE_FONTE` com uma entrada vencida devolve a cópia com `desatualizado=True`.
- [X] T034 [US3] Em `experiments/python/localidades/src/localidades/servico.py`, trocar o `_obter` para usar a `CacheComValidade`:
  - o `meta.coletado_em` passa a vir da entrada guardada;
  - o `meta.desatualizado` também;
  - o `resultado` do cache é exposto para as métricas da US5.

  Ao final, T030 e T031 passam.

**Checkpoint**: US1 a US3 verificadas, inclusive diante de falhas da fonte.

---

## Phase 6: User Story 4 - Encontrar um município pelo nome dentro de um estado (Priority: P3)

**Goal**: o parâmetro `nome` em `GET /v1/ufs/{uf}/municipios`.

**Independent Test**: buscar `niteroi`, `NITERÓI` e `são` e conferir os resultados e a paginação.

### Tests for User Story 4 ⚠️

- [X] T035 [P] [US4] Escrever `experiments/python/localidades/tests/integration/test_api_busca.py`, cobrindo:
  - **acerto:** `RJ?nome=niteroi` e `RJ?nome=NITERÓI` devolvem só `{codigo: "3303302", nome: "Niterói"}`;
  - **várias respostas:** `RJ?nome=são` devolve todos os municípios do RJ cujo nome dobrado contém "sao", em ordem, com `total` igual à contagem filtrada;
  - **busca sem resultado:** devolve `dados: []`, `total: 0` e `paginas: 0`;
  - **entrada inválida:** `nome=a`, `nome=%20a%20` e 61 caracteres devolvem 400, e o `detail` cita o mínimo de 2 ou o máximo de 60;
  - **consultas à fonte:** duas buscas na mesma UF geram 1 chamada ao IBGE.
- [X] T036 [P] [US4] Escrever `contracts/localidades/verificacao/tests/test_us4_busca.py`, com os cenários 1 a 3 da US4 (`SP?nome=são`, como na spec) validados contra o contrato.

### Implementation for User Story 4

- [X] T037 [US4] Acrescentar o parâmetro opcional `nome` a `listar_municipios` em `experiments/python/localidades/src/localidades/servico.py` (`validar_nome`, depois `filtrar_por_nome` e, por fim, `paginar`) e à rota em `experiments/python/localidades/src/localidades/api.py`. Ao final, T035 e T036 passam.

**Checkpoint**: busca por nome funcionando sobre a cópia guardada.

---

## Phase 7: User Story 5 - Saber se o serviço está saudável e como está sendo usado (Priority: P3)

**Goal**: métricas Prometheus, registro JSON por pedido e correlação verificada de fora.

**Independent Test**: fazer pedidos com acerto, falta e erro de fonte, ler o `/metrics` e encontrar o identificador de correlação na resposta e no registro.

### Tests for User Story 5 ⚠️

- [X] T038 [P] [US5] Escrever `experiments/python/localidades/tests/integration/test_api_operacao.py`, cobrindo:
  - **`/health`:** responde 200 com o IBGE fora, e o `respx` não registra nenhuma chamada;
  - **`/metrics`**, depois de um acerto, uma falta, um `desatualizado` e um `fonte-lenta`, contém:
    - `localidades_pedidos_total{rota="/v1/municipios/{codigo}",status="200"}`;
    - `localidades_erros_total{tipo="fonte-lenta"}`;
    - `localidades_cache_total{resultado="acerto"}`, `{resultado="falta"}` e `{resultado="desatualizado"}`;
    - `localidades_fonte_duracao_segundos_count{recurso="municipio"}`;
  - **registro:** cada pedido gera uma linha JSON com `momento`, `nivel`, `correlacao_id`, `metodo`, `rota`, `status`, `duracao_ms`, `cache` e `fonte_ms`, sem IP nem outros cabeçalhos.
- [X] T039 [P] [US5] Escrever `contracts/localidades/verificacao/tests/test_us5_operacao.py`, cobrindo:
  - **`/health`:** valida contra o contrato;
  - **`/metrics`:** responde `text/plain` e contém os 4 nomes de métrica;
  - **correlação:**
    - o `X-Correlation-Id` enviado volta igual;
    - um identificador inválido é trocado por um UUID v4;
    - num erro, `correlacao_id` do corpo é igual ao cabeçalho.

### Implementation for User Story 5

- [X] T040 [P] [US5] Implementar `experiments/python/localidades/src/localidades/metricas.py`:
  - um `CollectorRegistry` próprio por app, para não haver duplicação entre testes;
  - as 4 métricas de R12, com os rótulos do contrato;
  - a função `exportar()`, que devolve o texto e o `content-type` do Prometheus.
- [X] T041 [P] [US5] Implementar `experiments/python/localidades/src/localidades/registro.py`:
  - um `logging.Formatter` em JSON com os campos de R12, no stdout;
  - a função `registrar_pedido(...)`.
- [X] T042 [US5] Integrar a operação em `experiments/python/localidades/src/localidades/api.py`:
  - **`GET /metrics`;**
  - **middleware de medição**, que obtém o modelo da rota de `request.scope["route"].path` (ou `nao-encontrado` para rotas inexistentes) e atualiza `localidades_pedidos_total`, `localidades_erros_total` (pelo tipo do problema) e `localidades_cache_total` (pelo `resultado` exposto pelo serviço em `request.state`);
  - **duração da fonte:** o `ClienteIBGE` recebe `ao_medir=metricas.observar_fonte`;
  - **registro:** uma linha por pedido.

  Ao final, T038 e T039 passam.

**Checkpoint**: todas as histórias funcionando e verificadas.

---

## Phase 8: Polish & Fechamento do experimento

- [ ] T043 Rodar `uv run --project experiments/python/localidades pytest` e `contracts/localidades/verificacao/verificar.sh "uv run --project experiments/python/localidades localidades"` e registrar o número de testes de cada camada. Os dois precisam passar inteiros.
- [ ] T044 Executar a verificação com a rede externa bloqueada (SC-006), conforme o quickstart §3:
  - confirmar que um `curl` ao IBGE falha dentro do sandbox `(deny network*)(allow network* (remote ip "localhost:*"))`;
  - rodar as duas camadas de teste dentro dele;
  - registrar a data e o resultado.
- [ ] T045 Fazer a execução real manual contra o IBGE, conforme o quickstart §4:
  - registrar data e hora UTC;
  - medir a latência da primeira chamada e da repetida (SC-003);
  - conferir que MG tem `total` 853;
  - comparar com as fixtures;
  - medir o tempo do repositório clonado até a primeira resposta (SC-007).
- [ ] T046 [P] Atualizar `docs/adr/0001-convencoes-comuns-de-api.md`:
  - status: aceita no E1, a confirmar no E4;
  - os itens 3, 5 e 6 passam a refletir R10 (nomes do `meta` e `codigo` como identificador do registro), R9 (`itens` de 1 a 500, padrão 100), R11 (URNs dos problemas e mapeamento 502/504) e R12 (nomes das métricas e regras do `X-Correlation-Id`);
  - a nova decisão de códigos em texto (R7);
  - os pontos que ficam para o E4.
- [ ] T047 Escrever `specs/002-servico-localidades/RESULTS.md` a partir de `docs/templates/RESULTS.md`, com:
  - a resposta à pergunta do experimento;
  - o que funcionou e o que surpreendeu, incluindo o "não encontrado" com status 200 e a chave da documentação;
  - as limitações: cache só em memória e por processo, e a tabela fixa de UFs;
  - as métricas medidas;
  - a utilidade do serviço;
  - os próximos passos para o E4.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup e bloqueia todas as histórias.
  - T006 (fixtures) vem antes de T010, T018 e dos testes de integração.
  - T011 a T017 dependem dos testes T007 a T010 escritos.
  - T018 a T020 formam a base da suíte.
- **US1 (Phase 3)**: depende da Phase 2. É o MVP.
- **US2 (Phase 4)**: depende da Phase 2. T027 e T028 tocam `servico.py` e `api.py`, então vêm depois de T023 e T024.
- **US3 (Phase 5)**: depende da Phase 2.
  - T029 (cache) e T032 (IBGE falso) são independentes das outras histórias.
  - T034 altera o `_obter` do `servico.py`.
  - Os testes T030 e T031 exercitam rotas da US1 e da US2.
- **US4 (Phase 6)**: estende a rota da US1 (depende de T023 e T024) e usa a cópia guardada da US3 no teste "duas buscas, uma chamada".
- **US5 (Phase 7)**: T040 e T041 são independentes. T042 depende de T034, por causa do `resultado` do cache.
- **Polish (Phase 8)**: depende das histórias desejadas.

### User Story Dependencies

- **US1 (P1)**: independente após a fundação.
- **US2 (P1)**: lógica independente; compartilha os arquivos `servico.py` e `api.py` com a US1.
- **US3 (P2)**: o cache é independente, e a integração passa pelo `servico.py`.
- **US4 (P3)**: estende a US1.
- **US5 (P3)**: métricas e registro são independentes, e a integração passa pelo `api.py`.

### Within Each User Story

- Testes antes da implementação, falhando primeiro.
- Ordem: `dominio` e `erros` → `fonte_ibge` → `cache` → `servico` → `api`. A suíte de caixa-preta é escrita junto com os testes de cada história.

### Parallel Opportunities

- **Phase 1**: T003 e T004 em paralelo com T001 e T002.
- **Phase 2**: T007 a T010 em paralelo (depois de T006); T012 em paralelo com T011 e T013; T018 e T019 em paralelo com a implementação do serviço.
- **US1**: T021 e T022 em paralelo.
- **US2**: T025 e T026 em paralelo.
- **US3**: T029, T030 e T031 em paralelo; T032 e T033 em paralelo.
- **US5**: T038 e T039 em paralelo; T040 e T041 em paralelo.
- **Polish**: T046 em paralelo com T043 a T045.

---

## Parallel Example: User Story 3

```bash
# Testes da US3 juntos:
Task: "T029 test_cache.py em experiments/python/localidades/tests/unit/"
Task: "T030 test_api_falhas.py em experiments/python/localidades/tests/integration/"
Task: "T031 test_us3_falhas.py em contracts/localidades/verificacao/tests/"

# Implementações independentes da US3:
Task: "T032 modos e contagem do IBGE falso em contracts/localidades/verificacao/src/ibge_falso/servidor.py"
Task: "T033 cache.py em experiments/python/localidades/src/localidades/"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 e Phase 2.
2. Phase 3 (US1).
3. **Parar e validar**: o `pytest` passa, e o `verificar.sh` passa nos cenários da US1. Já existe um serviço que responde "quais municípios existem neste estado?" com procedência.

### Incremental Delivery

1. Setup e fundação: a base está pronta, e o `/health` responde.
2. US1: UFs e municípios por UF, o MVP. Um PR.
3. US2: município por código. Um PR.
4. US3: resiliência e cópia guardada. Um PR.
5. US4 e US5: busca por nome e operação. Um PR cada, ou juntos.
6. Fechamento: verificações, execução real, ADR e `RESULTS.md`.

---

## Notes

- **[P]** = arquivos diferentes, sem dependência pendente.
- O contrato (`contracts/localidades/openapi.yaml`) só muda por decisão explícita. Se um teste mostrar que o contrato está errado, corrija o contrato e o research.md no mesmo commit.
- A suíte de caixa-preta não importa nada de `experiments/python/localidades/`. Ela fala só pela rede, para servir igual ao E4.
- Os testes nunca chamam o IBGE real. Chamadas reais acontecem só em T006 e T045, com data registrada.
- Commits pequenos por tarefa ou grupo lógico, em branches a partir da `develop`, sem atribuição ao Claude.

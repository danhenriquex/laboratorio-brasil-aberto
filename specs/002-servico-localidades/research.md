# Research: E1 — Serviço de localidades (IBGE)

**Data**: 2026-11-26 | **Spec**: [spec.md](spec.md) | **Plano**: [plan.md](plan.md)

Decisões que a spec deixou para o plano. A spec é compartilhada com o E4: as decisões marcadas **(contrato)** valem para as duas implementações. As demais são da implementação em Python.

## R1. Comportamento real do IBGE (sondagem de 2026-11-26)

A spec deixou em aberto como o IBGE sinaliza "não encontrado". Fiz cinco chamadas reais, em sequência, com 2 s de intervalo, às 14:14 UTC, com o User-Agent do laboratório e sem guardar os corpos:

| Chamada | Resultado |
|---|---|
| `/municipios/3304557` | 200, **objeto** com `id`, `nome`, `microrregiao` e `regiao-imediata` (472 bytes, 160 ms) |
| `/municipios/9999999` | **200 com `[]`**, e não 404 (186 ms) |
| `/estados/RJ/municipios` | 200, lista com 92 municípios. A sigla é aceita no lugar do código (142 ms) |
| `/estados/99/municipios` | **200 com `[]`** (228 ms) |
| `/municipios` | 200, 5.571 municípios em 2,47 MB (428 ms) |

Constatações:

- **"Não encontrado" é uma lista vazia com status 200.** Um código existente devolve um objeto, e um inexistente devolve `[]`.
- **A chave real é `regiao-intermediaria`.** A grafia `regiao-intermediara` era erro da documentação.
- O caminho completo da UF dentro do município é `regiao-imediata.regiao-intermediaria.UF.regiao`.
- **Um município vem com `microrregiao: null`:** `5101837`, em MT, provavelmente criado depois da última revisão das microrregiões. Todos os 5.571 têm `regiao-imediata`.
- Os 5.571 códigos têm 7 dígitos. MG tem 853 municípios e o DF tem 1. Nomes com apóstrofo existem (por exemplo, `Alta Floresta D'Oeste`).

**Decision**:

- `[]` em resposta a um município ou UF solicitados vira "não encontrado".
- Uma UF que existe na lista oficial e volta com `[]` vira "resposta inesperada da fonte", como manda a spec.
- `microrregiao` é opcional na leitura. O serviço nem a expõe, porque a spec usa as regiões imediata e intermediária.
- Para distinguir uma UF inexistente de uma falha, o serviço usa uma **tabela fixa com o código e a sigla das 27 UFs** (`UFS_OFICIAIS`), que não muda desde 1988. Ela serve só para validar e resolver a entrada, sem consultar o IBGE. Nomes e regiões continuam vindo do IBGE.
  - Assim cada pedido faz no máximo uma consulta à fonte (FR-017), mesmo com o cache vazio.
  - Se a tabela e o IBGE divergirem (uma UF da tabela ausente em `/estados`), o serviço responde "resposta inesperada da fonte".

**Rationale**: o status HTTP do IBGE não basta para separar "não existe" de "existe", então a decisão tem de olhar o corpo. A ficha do IBGE é atualizada com esses fatos.

## R2. Linguagem e framework

- **Decision**: Python ≥ 3.11 com **FastAPI**, servido por **uvicorn**, e **httpx** assíncrono para falar com o IBGE. O `pydantic`, que vem com o FastAPI, valida a forma das respostas do IBGE.
- **Rationale**:
  - o FastAPI é o framework previsto na arquitetura do laboratório (board, seção 1);
  - ele é assíncrono, o que deixa simples a consulta única por chave (R5) e o prazo total (R6);
  - o httpx já foi usado no E0.
- **Alternatives considered**:
  - Flask: síncrono, o que complica a consulta única por chave;
  - Litestar: menos conhecido, sem ganho para o caso;
  - biblioteca padrão (`http.server`): sem validação nem roteamento, muito código de infraestrutura para um experimento sobre contrato.

## R3. Contrato primeiro **(contrato)**

- **Decision**: o contrato é escrito à mão em `contracts/localidades/openapi.yaml` (OpenAPI 3.1, com schemas em JSON Schema 2020-12). O OpenAPI que o FastAPI gera sozinho fica **desligado** (`openapi_url=None`, `docs_url=None`), para não existirem dois contratos.
- **Rationale**: a ADR 0001 pede que o E1 e o E4 cumpram o mesmo contrato. Se o código gerasse o contrato, ele acompanharia a implementação em Python, e a comparação com o E4 perderia o sentido.
- **Alternatives considered**:
  - code-first com o OpenAPI do FastAPI: rejeitado pela ADR 0001;
  - servir o contrato escrito à mão em `/openapi.yaml`: fica para depois, porque não é requisito.

## R4. Verificação de caixa-preta e IBGE falso **(contrato)**

- **Decision**: uma suíte em `contracts/localidades/verificacao/` que fala com o serviço **só pelo endereço** (FR-021, SC-008).
  - **IBGE falso:** um servidor com a biblioteca padrão (`http.server`), em `127.0.0.1`, serve as fixtures gravadas. Ele tem um endereço de controle (`POST /_controle`) com quatro modos:
    - `normal`;
    - `fora`: responde 503;
    - `lento`: espera mais que o prazo;
    - `invalido`: responde HTML com status 200.

    Ele também tem um endereço de contagem (`GET /_controle/contagem`), que diz quantas vezes cada recurso foi pedido e serve para provar o SC-004.
  - **Script `verificar.sh "<comando do serviço>"`:**
    1. sobe o IBGE falso;
    2. sobe o serviço com o perfil de verificação (prazo de 1 s, validade de 2 s, URL do IBGE falso);
    3. espera o `/health`;
    4. roda a suíte;
    5. encerra os dois.

    No E4, basta trocar o comando.
  - **Validação:** cada resposta é conferida contra o schema do `openapi.yaml` para a rota e o status, com `jsonschema` e `referencing`. O tipo de conteúdo também é conferido: `application/json` ou `application/problem+json`.
- **Rationale**:
  - os cenários de falha (US3) fazem parte do contrato, não só da implementação;
  - com o IBGE falso controlável, a mesma suíte prova fonte fora do ar, fonte lenta e cópia vencida nas duas linguagens.
- **Alternatives considered**:
  - Schemathesis: gera pedidos a partir do contrato, mas não controla a fonte;
  - Pact: voltado para contratos entre consumidor e provedor que já existem;
  - testes só dentro de cada implementação: divergiriam com o tempo.

## R5. Cópia guardada (cache) **(contrato: comportamento; implementação: forma)**

- **Decision**:
  - **Onde e qual chave:** em memória do processo, por recurso do IBGE. A chave é o caminho consultado: `estados`, `estados/{codigo}/municipios` e `municipios/{codigo}`.
  - **O que fica guardado:** a entrada guarda os dados **já normalizados**, a URL consultada, o `coletado_em` e o `expira_em`.
  - **Estados de uma entrada:** ausente, válida e vencida.
    - Válida: atende sem consultar a fonte.
    - Vencida: consulta a fonte. Se der certo, renova. Se falhar, entrega a cópia com `desatualizado: true` (FR-016).
    - Ausente: consulta a fonte. Se falhar, devolve o erro.
  - **Uma consulta por recurso:** um `asyncio.Lock` por chave faz pedidos simultâneos pelo mesmo recurso esperarem a primeira consulta.
  - **Respostas que não entram na cópia:** "não encontrado" (`[]`) não é guardado, para que um código recém-criado apareça. Erros também não.
  - **Limite de memória:** nenhum além do próprio domínio (27 + 27 listas + 5.571 municípios, cerca de 3 MB no pior caso).
  - **Busca e paginação:** são feitas sobre a lista guardada da UF, então não geram consulta nova.
- **Rationale**:
  - a Constituição X proíbe infraestrutura sem necessidade: um único processo não precisa de Redis;
  - a cópia vencida em caso de falha é a Assumption da spec.
- **Alternatives considered**:
  - Redis: previsto no board para quando houver mais de um processo;
  - `cachetools.TTLCache`: não tem cópia vencida nem consulta única;
  - carregar os 5.571 municípios de uma vez (`/municipios`, 2,5 MB): menos consultas, mas a primeira resposta fica mais lenta e foge do "repassar com cópia".

## R6. Prazo e classificação das falhas da fonte **(contrato: tipos de erro)**

- **Decision**: o prazo de cada consulta é **total**, aplicado com `asyncio.timeout(prazo)` em volta da chamada inteira (conexão e leitura). O httpx recebe o mesmo valor como limite por fase, como segunda proteção. É a lição do R8 do E0, onde o limite por fase deixava uma consulta durar cerca de 2× o prazo.

  Nenhuma nova tentativa (FR-017).

  Classificação:

  | Observado no IBGE | Erro de domínio | HTTP |
  |---|---|---|
  | Conexão recusada, DNS ou TLS | `fonte-indisponivel` | 502 |
  | 5xx ou 429 | `fonte-indisponivel` | 502 |
  | Prazo total esgotado | `fonte-lenta` | 504 |
  | 2xx que não é JSON, ou JSON fora da forma esperada | `resposta-inesperada-da-fonte` | 502 |
  | Outros 4xx | `resposta-inesperada-da-fonte` | 502 |
  | `[]` para município ou UF solicitados | `nao-encontrado` | 404 |
  | `[]` para a lista de municípios de uma UF existente | `resposta-inesperada-da-fonte` | 502 |

  Antes de devolver qualquer erro de fonte, o serviço tenta a cópia vencida (R5).
- **Rationale**: os status 502 e 504 seguem a ADR 0001. Um 429 do IBGE é tratado como indisponibilidade momentânea, sem nova tentativa.

## R7. Identificadores como texto de tamanho fixo **(contrato)**

- **Decision**: todos os códigos saem como **texto com tamanho fixo**:

  | Unidade | Formato |
  |---|---|
  | Região | `^\d$` |
  | UF | `^\d{2}$` |
  | Região intermediária | `^\d{4}$` |
  | Região imediata | `^\d{6}$` |
  | Município | `^\d{7}$` |

  O IBGE entrega números, e o serviço converte.
- **Rationale**:
  - identificador não é quantidade;
  - o laboratório vai cruzar fontes pelo código do IBGE (board, seção 2: "anti-corruption layer"), e o texto evita perder zeros à esquerda em outras bases e em outras linguagens;
  - a validação fica numa expressão regular, igual no Python e no Java.
- **Alternatives considered**: manter inteiros, como o IBGE. É mais simples hoje, mas cada consumidor teria de normalizar depois.

## R8. Ordenação e busca por nome **(contrato)**

- **Decision**: a regra de **dobra** é: Unicode NFKD, remoção das marcas diacríticas (categoria `Mn`) e `casefold`.
  - **Ordenação:** as listas de municípios são ordenadas pelo nome dobrado e, no empate, pelo código.
  - **Busca:** `nome` é aparado nas pontas e precisa ter de 2 a 60 caracteres. Um município combina quando o nome dobrado da busca está contido no nome dobrado dele.
  - **Paginação:** vem depois do filtro, e o `total` conta só os que combinaram.
- **Rationale**: a regra cabe numa linha, é determinística e tem equivalente direto em Java (`Normalizer.Form.NFKD`). A ordem do IBGE (`orderBy=nome`) não está documentada a ponto de garantir a mesma ordem nas duas implementações.

## R9. Paginação **(contrato)**

- **Decision**:
  - parâmetros `pagina` (≥ 1, padrão 1) e `itens` (1 a 500, padrão 100);
  - a resposta traz `paginacao: {pagina, itens, total, paginas}`;
  - uma página além do fim devolve `dados: []` com o total correto;
  - a lista de UFs não é paginada: são sempre 27.
- **Rationale**: com o máximo de 500, MG (853) ocupa duas páginas, e o padrão de 100 cobre a maioria das UFs numa página só. O limite fica no contrato (ADR 0001, item 5). `LOCALIDADES_ITENS_MAX` existe (FR-026), mas mudar o padrão de 500 sai do contrato v1, e isso está documentado.

## R10. Envelope das respostas e procedência **(contrato)**

- **Decision**: toda resposta com dados tem a forma `{ "dados": …, "meta": {…} }`, e as listas paginadas também levam `paginacao`. O `meta` tem:

  | Campo | Conteúdo |
  |---|---|
  | `fonte` | `"IBGE — API de localidades"` |
  | `url_fonte` | a URL do IBGE efetivamente consultada |
  | `url_documentacao` | `https://servicodados.ibge.gov.br/api/docs/localidades` |
  | `coletado_em` | ISO 8601 em UTC, com milissegundos e `Z`, sempre da consulta original |
  | `desatualizado` | booleano |

  O **identificador do registro** (Constituição II) é o `codigo` de cada item.
- **Rationale**: confirma a ADR 0001, item 3, e decide os pontos que ela deixava em aberto:
  - os nomes dos campos;
  - `id_registro` dá lugar ao `codigo` de cada item, porque uma lista tem vários registros;
  - `vigencia` não se aplica, e por isso fica fora do schema.

  A ADR é atualizada no fechamento do E1.

## R11. Erros **(contrato)**

- **Decision**: os erros seguem `application/problem+json` (RFC 9457) com `type`, `title`, `status`, `detail` e a extensão `correlacao_id`. Os tipos são URNs estáveis:

  | `type` | Status |
  |---|---|
  | `urn:brasil-aberto:problema:entrada-invalida` | 400 |
  | `urn:brasil-aberto:problema:nao-encontrado` | 404 |
  | `urn:brasil-aberto:problema:fonte-indisponivel` | 502 |
  | `urn:brasil-aberto:problema:fonte-lenta` | 504 |
  | `urn:brasil-aberto:problema:resposta-inesperada-da-fonte` | 502 |
  | `urn:brasil-aberto:problema:erro-interno` | 500 |

  Detalhes do tratamento:

  - o 422 padrão do FastAPI é convertido para 400 `entrada-invalida`, com um `detail` que diz o campo e o limite;
  - rotas inexistentes, inclusive sem `/v1` ou com outra versão, saem como 404 `nao-encontrado`;
  - o `detail` nunca inclui rastro de execução, endereço interno nem corpo do IBGE (FR-013).
- **Rationale**: as URNs não dependem de domínio nem de onde o repositório está hospedado, e a RFC 9457 aceita URIs não resolvíveis. O 400 segue a ADR 0001 e evita a semântica própria do 422 no FastAPI.

## R12. Observabilidade **(contrato: rotas, nomes e cabeçalho)**

- **Decision**:
  - **`GET /health`:** devolve `200 {"status": "ok"}` e nunca consulta o IBGE.
  - **`GET /metrics`:** formato texto do Prometheus (`prometheus-client`), com estes nomes, compartilhados com o E4:

    | Métrica | Tipo | Rótulos |
    |---|---|---|
    | `localidades_pedidos_total` | contador | `rota`, `status` |
    | `localidades_erros_total` | contador | `tipo` |
    | `localidades_cache_total` | contador | `resultado`: `acerto`, `falta` ou `desatualizado` |
    | `localidades_fonte_duracao_segundos` | histograma | `recurso` |

    O rótulo `rota` usa o modelo da rota (`/v1/municipios/{codigo}`), e não o caminho real, para não multiplicar séries.
  - **`X-Correlation-Id`:** é aceito se tiver de 1 a 64 caracteres em `[A-Za-z0-9._-]`. Se faltar ou for inválido, o serviço gera um UUID v4. O valor volta no cabeçalho de toda resposta e em `correlacao_id` nos erros.
  - **Registro:** uma linha JSON por pedido no stdout, com `momento`, `nivel`, `correlacao_id`, `metodo`, `rota`, `status`, `duracao_ms`, `cache` e `fonte_ms`. Não registra IP nem outros cabeçalhos.
- **Rationale**:
  - são os padrões de serviço da constituição;
  - com os nomes de métricas e de cabeçalho compartilhados, a mesma suíte confere as duas implementações;
  - o formato Prometheus é o que o Java (Micrometer) também entrega.

## R13. Testes e isolamento da rede

- **Decision**:
  - **Testes do E1** (`experiments/python/localidades/tests/`):
    - unitários de domínio e de cache, com um relógio falso injetável;
    - o cliente do IBGE testado com `respx`;
    - integração da API com o `TestClient` do FastAPI e `respx`;
    - o `conftest` bloqueia conexões a endereços que não sejam de loopback, como fazia o E0.
  - **Suíte de verificação:** fala só com `127.0.0.1`, onde ficam o serviço e o IBGE falso.
  - **Fixtures:** respostas reais do IBGE, gravadas uma vez numa verificação manual datada (estados, municípios de RJ, DF e SP, e alguns municípios por código), mais casos sintéticos (HTML de erro, campo ausente). São dados públicos, sem dados pessoais.
  - **SC-006:** a suíte roda num sandbox do macOS que nega a rede externa e permite o loopback: `(deny network*) (allow network* (remote ip "localhost:*"))`.
- **Alternatives considered**: o `(deny network*)` do E0 bloqueia também o loopback e impediria a suíte de caixa-preta.

## R14. Configuração comum **(contrato)**

- **Decision**: as variáveis de ambiente, com o mesmo nome no E1 e no E4:

  | Variável | Padrão | Uso |
  |---|---|---|
  | `LOCALIDADES_HOST` | `127.0.0.1` | endereço de escuta |
  | `LOCALIDADES_PORTA` | `8000` | porta |
  | `LOCALIDADES_IBGE_URL` | `https://servicodados.ibge.gov.br/api/v1/localidades` | base da fonte |
  | `LOCALIDADES_PRAZO_FONTE_S` | `10` | prazo total por consulta |
  | `LOCALIDADES_VALIDADE_S` | `86400` | validade da cópia guardada |
  | `LOCALIDADES_ITENS_MAX` | `500` | tamanho máximo de página |

  Valores inválidos (não numéricos, zero ou negativos) impedem o serviço de iniciar, com uma mensagem clara.
- **Rationale**:
  - FR-026;
  - com os nomes iguais, o `verificar.sh` sobe qualquer implementação com o mesmo perfil;
  - não há segredos (IX).

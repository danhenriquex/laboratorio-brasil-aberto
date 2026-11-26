# Research: E0 — Inventário e conectividade das fontes

**Data**: 2026-11-24 | **Spec**: [spec.md](spec.md) | **Plano**: [plan.md](plan.md)

Escolhas de base vindas de `docs/prompts/E0-inventario-fontes.md` (seção 2): Python 3.11+, `httpx`, `pytest` + `respx`, `uv`, código em `experiments/python/discovery/`, relatórios em `discovery/reports/`. Abaixo, as decisões que essas escolhas não resolviam.

## R1. Leitura limitada da resposta (FR-014, FR-016, edge case "resposta muito grande")

- **Decision**: usar `httpx.Client.stream()` e ler o corpo em blocos até um teto de **1 MiB**. Se o teto for atingido, a conexão é fechada e o resultado marca `truncada: true`. O corpo fica só em memória e nunca vai para o disco.
- **Rationale**: atende "sem coletar dados em volume" sem depender do `Content-Length`, que pode faltar. 1 MiB cobre com folga as três sondas da rodada 1 (respostas de poucos KB) e ainda é pouco para a fonte.
- **Alternatives considered**: `client.get()` com o corpo inteiro (sem controle de volume); requisição `HEAD` (muitas APIs não suportam e não dá amostra); parser JSON incremental (`ijson`), descartado por ser uma dependência a mais para um caso que a rodada 1 não tem.
- **Consequência**: JSON truncado não pode ser interpretado. Nesse caso a estrutura fica "indisponível (resposta truncada)", sem causar falha.

## R2. Redirecionamento e detecção de login (FR-009, edge case de redirecionamento)

- **Decision**: `follow_redirects=True` com no máximo **5** redirecionamentos. A cadeia (`response.history`) e a URL final são registradas. A ferramenta conclui "exige autenticação" quando ocorre uma destas condições:
  1. status 401, ou cabeçalho `WWW-Authenticate` presente;
  2. redirecionamento cuja URL final tem host `sso.acesso.gov.br` ou caminho com `login`, `signin`, `auth`, `oauth` ou `sso`.

  Um 403 sem esses indícios é registrado como `acesso_negado`.
- **Rationale**: o caso típico do gov.br é redirecionar para o SSO. A heurística é simples, testável e está registrada como hipótese no relatório (`indicio_autenticacao`).
- **Alternatives considered**: não seguir redirecionamentos (perde o formato real da maioria das fontes); analisar o HTML final em busca de formulário de senha (frágil).

## R3. Classificação de falhas (FR-010)

| Situação observada | `causa` |
|---|---|
| `httpx.TimeoutException` | `tempo_esgotado` |
| `httpx.ConnectError` (DNS, conexão recusada), exceto TLS | `indisponivel` |
| Erro de certificado ou TLS (`ssl.SSLError` na cadeia) | `erro_tls` |
| 401 ou indício de login (R2) | `exige_autenticacao` |
| 403 sem indício de login | `acesso_negado` |
| 429 | `limite_requisicoes` (registra `Retry-After` se vier) |
| 5xx | `erro_fonte` |
| Outros 4xx, ou excesso de redirecionamentos | `erro_requisicao` |
| 2xx cujo conteúdo não se interpreta no formato declarado ou detectado | `resposta_invalida` |

- **Rationale**: as causas da spec (FR-010) mais `erro_requisicao`. Os endereços de teste do catálogo são hipóteses, e um 404 ("endereço de teste errado") precisa ser distinguido de "fonte fora do ar". O Retry-After é só registrado: não há nova tentativa (FR-004, FR-007).
- **Alternatives considered**: agrupar todos os 4xx em `erro_fonte` (esconderia endereços de teste errados).

## R4. Detecção de formato (FR-011)

- **Decision**: o formato vem de duas fontes, e o resultado guarda as duas: o `Content-Type` (formato declarado) e a inspeção dos primeiros bytes (formato detectado). A inspeção ignora BOM e espaços iniciais:
  - começa com `{` ou `[` → `json`;
  - começa com `<?xml` ou `<` + nome de elemento, sem `<!doctype html`/`<html` → `xml`;
  - `<!doctype html` ou `<html` → `html`;
  - texto em que `csv.Sniffer` detecta delimitador e há mais de uma coluna → `csv`;
  - texto decodificável → `texto`; vazio → `vazio`; caso contrário → `outro`.

  O formato detectado prevalece. Quando os dois divergem, o resultado registra `formato_divergente: true`.
- **Rationale**: fontes públicas costumam declarar `text/html` para JSON, ou devolver página HTML de erro com status 200. O cenário "formato inesperado" da spec depende disso.

## R5. Inspeção de estrutura sem valores (FR-014, FR-015)

- **Decision**: a amostra são os **5 primeiros registros**.
  - **JSON**: se for lista, os 5 primeiros itens. Se for objeto, o próprio objeto; quando ele tem uma chave cujo valor é lista de objetos (ex.: `dados` na Câmara), a amostra é tirada dessa lista e o caminho dela é registrado.
  - **CSV**: cabeçalho mais 5 linhas.
  - **XML**: o elemento raiz e os filhos dos 5 primeiros elementos repetidos.

  Cada campo vira `{caminho, tipos}`, com caminho em notação de pontos (`regiao.sigla`, `itens[].id`). `tipos` é a união dos tipos vistos na amostra: `texto`, `inteiro`, `decimal`, `booleano`, `nulo`, `data` (texto no padrão ISO `AAAA-MM-DD`, com ou sem hora), `objeto`, `lista`. A profundidade vai até 5 níveis.

  Ajustes feitos na implementação (US2):
  - `data` também reconhece `dd/mm/aaaa`, formato usado pelo BCB/SGS.
  - Chaves de objeto que parecem dados (só dígitos, pontos, hífens, barras ou dois-pontos, como um CPF ou uma data usados como chave) aparecem como `<chave>`, para que valores não vazem pelo nome do campo.
  - Em CSV truncado, a última linha é descartada, porque pode estar partida.
- **Rationale**: o tipo é inferido do valor, e o valor é descartado na hora. Nada do conteúdo chega ao modelo de resultado, o que torna FR-015 verificável por construção: o tipo `CampoAmostra` não tem campo para valor.
- **Alternatives considered**: gerar JSON Schema completo com `genson` (dependência a mais, e o esquema pode carregar `enum`/`examples` com valores).

## R6. XML seguro

- **Decision**: `xml.etree.ElementTree` da biblioteca padrão.
- **Rationale**: o ElementTree não resolve entidades externas, e o expat empacotado nas versões suportadas do Python (≥ 2.4.1) já mitiga expansão exponencial de entidades. Isso, somado ao teto de 1 MiB (R1), basta para uma sondagem. Nenhuma fonte da rodada 1 devolve XML.
- **Alternatives considered**: `defusedxml` (mais garantias, mas uma dependência para um caso ainda hipotético). Reavaliar se uma fonte XML entrar no catálogo com sonda.

## R7. Relatório HTML sem framework (FR-017, FR-018)

- **Decision**: um módulo que monta o HTML com `string.Template` e `html.escape` em todo texto vindo do catálogo ou da resposta (URLs, nomes, tipos), com CSS inline e sem JavaScript nem recursos externos. O arquivo abre direto do disco.
- **Rationale**: princípio X. É uma página com uma tabela e um resumo, e o escape centralizado evita injeção a partir do catálogo.
- **Alternatives considered**: Jinja2 (autoescape é confortável, mas é uma dependência para um template só).

## R8. Ritmo, tempo limite e identificação (FR-004 a FR-008)

- **Decision**:
  - um único `httpx.Client` por execução, sem retries (`transport` padrão), tempo limite configurável (padrão 15 s) e `User-Agent: laboratorio-brasil-aberto-inventario/<versão>`;
  - **como o tempo limite é aplicado** (revisto na convergência, T038 e T039): o httpx aplica o valor a cada fase (conexão e cada espera de leitura); a sonda confere o prazo total da consulta depois de cada bloco lido e, se ele foi excedido, encerra com `tempo_esgotado`. O prazo total só é conferido quando chega um bloco. Por isso, no pior caso (conexão lenta seguida de servidor parado antes do primeiro bloco), uma consulta pode durar cerca de **2× o tempo limite** (~30 s com o padrão). Garantir um prazo rígido exigiria rodar a consulta em outra thread, complexidade que não se justifica numa ferramenta de sondagem (Constituição X);
  - o intervalo entre consultas (padrão 2 s) é medido com `time.monotonic()` desde o fim da consulta anterior;
  - a função de espera e o relógio são injetáveis, para os testes verificarem SC-005 sem esperar de verdade;
  - fontes sem endereço de teste não consomem intervalo.
- **Rationale**: execução sequencial é o modo mais respeitoso e o mais fácil de testar. Com 3 sondas, o caso comum de falha (cada fonte esgotando o tempo limite uma vez) é 3 × 15 s + 2 × 2 s = 49 s, dentro do SC-001 (< 1 min). O pior caso patológico, com as três fontes conectando devagar e travando antes do primeiro bloco, é 3 × ~30 s + 2 × 2 s ≈ 94 s e passaria do SC-001. Esse cenário é aceito e fica registrado como limitação. A execução real da rodada 1 levou 4,9 s.

## R9. Datas e fuso (FR-009, princípio II)

- **Decision**: todas as datas são gravadas em ISO 8601 com fuso UTC (`2026-11-24T13:05:12.345Z`) no JSON. O HTML mostra também o horário de Brasília (`America/Sao_Paulo`, via `zoneinfo`). O nome dos arquivos usa UTC: `inventario-20261124T130512Z.json` / `.html`.
- **Rationale**: UTC sem ambiguidade para comparar execuções e Brasília para leitura humana. O nome com timestamp atende "não sobrescrever".

## R10. Interrupção (edge case)

- **Decision**: o laço de sondagem captura `KeyboardInterrupt`, marca `interrompida: true`, grava os relatórios com as fontes já processadas e sai com código 130. As fontes não processadas aparecem como `nao_executada`.
- **Rationale**: atende "as fontes já consultadas não se perdem" e mantém SC-002, porque toda fonte do filtro aparece no relatório.

## R11. Grau de verificação sugerido (FR-003, FR-018, princípio III)

- **Decision**: o relatório mostra lado a lado o `verificacao_catalogo` (copiado) e o `verificacao_sugerida`:
  - sonda respondeu (2xx com formato interpretável), ou falhou com causa de autenticação, bloqueio ou limite: `confirmado`, com escopo explícito `conectividade_e_autenticacao`. Uma observação direta do endpoint oficial confirma esses dois fatos naquela data;
  - falha transitória (`tempo_esgotado`, `indisponivel`, `erro_fonte`, `erro_tls`) ou `erro_requisicao`/`resposta_invalida`: mantém o grau do catálogo e explica por quê;
  - sem teste automatizado: mantém o grau do catálogo.

  Licença, limites e termos nunca são sugeridos (FR-020).
- **Rationale**: separa o que a sonda prova do que só a documentação prova.

## R12. Divergência hipótese × observado (FR-018)

- **Decision**: a hipótese de autenticação é derivada do campo `auth` do catálogo: começa com "nenhuma" → `nao_exige`; qualquer outro texto não vazio → `exige`. A observação vale `exige`, `nao_exige` ou `indeterminado` (falhou antes de haver resposta). Há divergência quando hipótese e observação são conhecidas e diferentes. Disponibilidade: a hipótese implícita é "responde", e há divergência quando a situação é `falhou`. A hipótese textual de dificuldade (`access_hypothesis`) é exibida, mas não é comparada automaticamente.
- **Rationale**: compara só o que a sonda consegue observar. A dificuldade ("fácil", "moderado") é julgamento humano e fica para a ficha.

## R13. Dependências

| Pacote | Uso | Tipo |
|---|---|---|
| `httpx` | cliente HTTP com streaming e timeout | runtime |
| `pytest` | testes | dev |
| `respx` | simular respostas do `httpx` sem rede | dev |
| `jsonschema` | validar o relatório contra o contrato em `contracts/` | dev |

Todo o resto vem da biblioteca padrão: `argparse`, `dataclasses`, `json`, `csv`, `xml.etree`, `string`, `html`, `zoneinfo`.

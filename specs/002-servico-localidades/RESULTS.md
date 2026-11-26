# Resultados: E1 — Serviço de localidades (IBGE)

- **Pergunta que o experimento respondia:** o que é preciso para expor as localidades do IBGE como um serviço próprio, com contrato estável, procedência em cada resposta e comportamento previsível quando o IBGE falha ou demora?
- **Timebox previsto / usado:** 2 a 3 sessões curtas / 1 sessão (2026-11-26), da especificação ao fechamento.
- **Linguagem e ferramentas:** Python 3.11+ (executado em 3.12), FastAPI, uvicorn, httpx assíncrono, prometheus-client; testes com pytest, respx, jsonschema e openapi-spec-validator; `uv`.
- **Data de conclusão:** 2026-11-26

## Resposta curta
São necessárias quatro coisas, e a mais trabalhosa não é o código do serviço:
1. **Um contrato escrito à mão** (`contracts/localidades/openapi.yaml`) e uma **suíte de caixa-preta** que fala com o serviço só pela rede, diante de um **IBGE falso controlável**. Isso levou 20 das 47 tarefas, mas é o que torna o E4 uma comparação justa: a mesma suíte vai verificar o Java.
2. **Procedência em toda resposta**, com a data da consulta original. Mesmo quando a resposta sai da cópia guardada, o consumidor sabe de quando é o dado.
3. **Prazo total por consulta, sem nova tentativa**, mais uma **cópia guardada** que vira "desatualizada" quando a fonte cai. Com prazo de 1 s, nenhum pedido passou de 2 s mesmo com o IBGE travado.
4. **Ler a fonte de verdade, e não só a documentação.** O IBGE responde "não encontrado" com status 200 e `[]`, e a documentação erra o nome de uma chave.

## O que foi feito
Serviço HTTP somente leitura em `experiments/python/localidades/`:

| Rota | O que devolve |
|---|---|
| `GET /v1/ufs` e `/v1/ufs/{uf}` | as 27 UFs, ou uma UF por sigla ou código |
| `GET /v1/ufs/{uf}/municipios?nome=&pagina=&itens=` | municípios de uma UF, em ordem, paginados e com busca sem acento |
| `GET /v1/municipios/{codigo}` | um município, com UF e regiões imediata e intermediária |
| `GET /health` e `GET /metrics` | operação |

Tudo segue o contrato compartilhado com o E4. O trabalho foi dividido em 7 branches, uma por fase ou história (issues #19 a #25).

## Fontes e documentação oficial
- API de localidades do IBGE: https://servicodados.ibge.gov.br/api/docs/localidades. A documentação foi lida no navegador em 2026-11-25, porque recusa leitura automatizada.
- Ficha da fonte, atualizada em 2026-11-26 com o comportamento real: [discovery/fichas/ibge-localidades.md](../../discovery/fichas/ibge-localidades.md).
- Fixtures reais gravadas em 2026-11-26 16:06 UTC: [contracts/localidades/fixtures-ibge/](../../contracts/localidades/fixtures-ibge/README.md).

## Como executar localmente
A partir da raiz do repositório:

```bash
uv sync --project experiments/python/localidades
uv run --directory experiments/python/localidades pytest                                                  # 135 testes
contracts/localidades/verificacao/verificar.sh "uv run --project experiments/python/localidades localidades"  # 47 cenários
uv run --project experiments/python/localidades localidades                                               # execução real em :8000
```

O roteiro completo, inclusive o sandbox sem rede, está em [quickstart.md](quickstart.md).

## Exemplos de requisição e resposta
Execução real contra o IBGE em **2026-11-26 16:20 UTC**, a partir de um clone limpo:

```text
GET /v1/ufs                               200   142 ms (consulta ao IBGE)   → 27 UFs, a primeira é AC
GET /v1/ufs (repetido)                    200   1,3 ms (cópia guardada)
GET /v1/ufs/rj/municipios?nome=niteroi    200   → [{"codigo":"3303302","nome":"Niterói"}]
GET /v1/municipios/3304557                200   → Rio de Janeiro, imediata 330001, intermediária 3301
GET /v1/municipios/9999999                404   (o IBGE respondeu 200 com [])
GET /v1/municipios/12ab                   400   1,7 ms, sem consultar o IBGE
GET /v1/ufs/MG/municipios?itens=500&pagina=2   → {"pagina":2,"itens":500,"total":853,"paginas":2}, 353 itens
GET /v1/ufs/MG/municipios (repetido)      200   4,6 ms
```

O `meta` de `/v1/ufs` nessa execução:

```json
{"fonte": "IBGE — API de localidades",
 "url_fonte": "https://servicodados.ibge.gov.br/api/v1/localidades/estados",
 "url_documentacao": "https://servicodados.ibge.gov.br/api/docs/localidades",
 "coletado_em": "2026-11-26T16:20:02.551Z", "desatualizado": false}
```

Um pedido no registro, uma linha JSON:

```json
{"momento": "2026-11-26T16:17:18.815Z", "nivel": "info", "correlacao_id": "bd4827c9-…", "metodo": "GET", "rota": "/v1/ufs", "status": 200, "duracao_ms": 1.8, "cache": "falta", "fonte_ms": 1.3}
```

As consultas ao IBGE, pelo `/metrics`, levaram 138 ms em `estados`, uma média de 116 ms em `municipios_da_uf` e uma média de 93 ms em `municipio`.

## O que funcionou
- **Critérios de sucesso, todos verificados:**

  | Critério | Resultado |
  |---|---|
  | **SC-001** | `meta` em 100% das respostas com dados |
  | **SC-002** | 47 cenários validados contra o `openapi.yaml` |
  | **SC-003** | pedido com cópia em 1,3 a 4,6 ms, contra a meta de 500 ms |
  | **SC-004** | zero consultas extras dentro da validade, contadas pelo IBGE falso |
  | **SC-005** | fonte fora, lenta ou inválida responde em menos de 2 s com prazo de 1 s |
  | **SC-006** | as duas camadas passam num sandbox sem rede externa (abaixo) |
  | **SC-007** | do clone limpo à primeira resposta em **1,7 s**, com o cache do `uv` já populado |
  | **SC-008** | a suíte não importa nada do serviço; o E4 só troca o comando do `verificar.sh` |

- **Consulta única por chave:** 10 pedidos simultâneos pelo mesmo município geraram 1 consulta ao IBGE.
- **Prazo total com `asyncio.timeout`:** resolveu o problema do E0, onde o limite por fase deixava uma consulta durar o dobro do previsto.
- **Separação em camadas:** o `servico.py` e o `dominio.py` não importam FastAPI. A troca de framework, ou a reescrita em Java, mexe só no adaptador HTTP.
- **Escrever os testes primeiro** pegou um detalhe: `\d` em Python aceita dígitos de outros alfabetos (`７`). As expressões regulares passaram a usar `re.ASCII`.

## O que falhou ou surpreendeu
- **"Não encontrado" com status 200 e `[]`:** o IBGE responde assim a um código de município ou UF inexistente. O serviço olha o corpo para decidir, e um `[]` para uma UF que existe vira "resposta inesperada".
- **A documentação erra uma chave:** mostra `regiao-intermediara`, e a resposta real usa `regiao-intermediaria`. Só a sondagem real mostrou isso.
- **Um município sem microrregião:** o `5101837` (Boa Esperança do Norte, MT). O serviço nem usa esse recorte, mas um parser rígido teria quebrado.
- **Inconsistência no próprio plano:** o plano previa consultar a lista de UFs antes dos municípios, o que daria duas consultas ao IBGE por pedido com o cache vazio, contra o FR-017. Apareceu ao montar as tarefas, e foi resolvido com uma tabela fixa de códigos e siglas das 27 UFs, usada só para validar a entrada.
- **`uv run --project … pytest` da raiz coleta testes de todo o repositório.** Com a suíte de contrato no repositório, os comandos do E0 também quebraram. O certo é `uv run --directory …`. Corrigido nos dois experimentos.
- **Sandbox do macOS:** liberar só o `remote ip "localhost:*"` não deixa o IBGE falso abrir a porta. É preciso também `(allow network* (local ip "localhost:*"))`.
- **O Starlette atual avisa que o `TestClient` deve passar a usar o pacote `httpx2`.** O aviso foi silenciado no `pyproject.toml`; vale acompanhar.

## Limitações
- **Cópia guardada em memória:** é por processo e se perde ao reiniciar. Com mais de uma instância, cada uma consulta o IBGE por conta própria. Redis só quando houver mais de um processo (Constituição X).
- **Tabela fixa de UFs:** se o IBGE criar uma UF nova, a tabela precisa ser atualizada à mão.
- **Licença:** a documentação de localidades do IBGE não declara licença nem termos de uso. Não encontrei.
- **Sem autenticação:** o serviço escuta em `127.0.0.1` e não autentica consumidores. Exposição pública fica para a fase de implantação.
- **Página máxima:** `LOCALIDADES_ITENS_MAX` é configurável, mas um valor diferente de 500 sai do contrato v1.
- **Fixtures:** são uma foto de 2026-11-26. Se o IBGE mudar, os testes continuam passando até as fixtures serem regravadas.
- **SC-007:** foi medido com o cache do `uv` já populado. Numa máquina nova, o tempo inclui baixar as dependências.

## Convergência
O `/speckit-converge` rodou depois da implementação e achou uma lacuna, MEDIUM: o cliente do IBGE completava com zeros à esquerda um `id` mais curto que o esperado. Um município com `id` 33045 saía como `"0033045"`, um código que não existe, com status 200. Agora um `id` com quantidade de dígitos errada vira "resposta inesperada da fonte". Foi corrigido na tarefa T048 (issue #29), com 3 testes novos.

## Verificações finais
- **SC-006 (testes sem rede):** em 2026-11-26 16:17 UTC, dentro de `sandbox-exec -p '(version 1)(allow default)(deny network*)(allow network* (local ip "localhost:*"))(allow network* (remote ip "localhost:*"))'`:
  - o `curl` ao IBGE falhou (`Could not resolve host`);
  - os 132 testes da implementação passaram;
  - os 47 cenários de caixa-preta passaram;
  - os 161 testes do E0 também passaram, como regressão.

## Checklist de conclusão
- [x] A fonte foi identificada e documentada (ficha do IBGE atualizada)
- [x] As condições de acesso foram verificadas (sem autenticação; licença não declarada)
- [x] O dado foi consumido ou baixado (execução real e fixtures gravadas)
- [x] A estrutura dos dados foi inspecionada (forma do município, `microrregiao` nula, `[]` como não encontrado)
- [x] Os casos de erro foram testados (fonte fora, lenta e inválida; entradas inválidas; cópia vencida)
- [x] O resultado pode ser reproduzido (comandos acima e `verificar.sh`)
- [x] As limitações estão registradas
- [x] A utilidade do experimento foi avaliada (abaixo)

## Decisões e próximos passos
- **Utilidade:** alta. O serviço responde a pergunta-guia nº 2 do roteiro ("Quais municípios existem neste estado?") e dá ao laboratório a chave de cruzamento entre fontes: o código do município em texto de 7 dígitos.
- **ADR:** a [ADR 0001](../../docs/adr/0001-convencoes-comuns-de-api.md) passou de proposta a **aceita no E1**, com:
  - contrato escrito à mão;
  - URNs de problema;
  - `meta`;
  - códigos em texto;
  - paginação;
  - métricas;
  - correlação.

  A confirmação vem no E4.
- **E4 (o mesmo serviço em Java):** pode começar direto no `/speckit-plan`, porque a spec, o contrato, as fixtures e a suíte já existem. Critério de pronto: `verificar.sh "java -jar …"` passando nos 47 cenários. Vale fazê-lo logo, com o E1 fresco, para comparar a ergonomia.
- **Ideias que ficaram de fora:**
  - servir o contrato em `/openapi.yaml`;
  - busca de município por nome em todo o Brasil;
  - aproveitar a lista da UF para responder a consulta por código sem nova chamada.

# Resultados: E0 — Inventário e conectividade das fontes

- **Pergunta que o experimento respondia:** quais fontes do catálogo respondem hoje, com que autenticação e em que formato, e onde as hipóteses de acesso do catálogo estavam erradas?
- **Timebox previsto / usado:** 1 a 2 sessões curtas / 2 sessões (2026-11-24 e 2026-11-25). A maior parte do tempo foi gasta organizando o repositório e o board, mais do que na ferramenta em si.
- **Linguagem e ferramentas:** Python 3.11+ (executado em 3.12), `httpx`, `pytest` + `respx` + `jsonschema`, `uv`.
- **Data de conclusão:** 2026-11-25

## Resposta curta
As quatro fontes da rodada 1 respondem, **sem autenticação**, em **JSON**, em 160 a 340 ms. Nenhuma hipótese de acesso do catálogo estava errada. Os erros estavam em outro lugar:
- o `docs_url` do BCB SGS não levava à documentação;
- o IFData podia ser sondado pela raiz do serviço OData, sem os parâmetros que o catálogo supunha necessários;
- e o SGS tem limites que o catálogo não registrava (janela de 10 anos, `ultimos` até 20, filtros obrigatórios desde 2025).

## O que foi feito
O comando `inventario` (em `experiments/python/discovery/`) lê `discovery/sources.json` e consulta uma única vez cada fonte com `probe_url`, em sequência e com intervalo mínimo de 2 s. O resultado vai para dois relatórios em `discovery/reports/`, um JSON validado por [JSON Schema](contracts/relatorio.schema.json) e um HTML autocontido. Para cada fonte, o relatório registra:
- status, latência, formato declarado e detectado, tamanho, autenticação observada, redirecionamentos e data da coleta;
- a estrutura da amostra: nomes de campos e tipos, **nunca os valores**;
- as divergências entre a hipótese do catálogo e o observado;
- o grau de verificação sugerido.

O trabalho foi dividido em 5 PRs (#7 a #11), um por história, cada um fechando a sua issue no board.

## Fontes e documentação oficial
Lidas em 2026-11-25. Detalhes e grau de verificação de cada resposta estão nas fichas.

| Fonte | Documentação | Ficha |
|---|---|---|
| IBGE localidades | https://servicodados.ibge.gov.br/api/docs/localidades (403 para leitura automatizada) | [ibge-localidades.md](../../discovery/fichas/ibge-localidades.md) |
| BCB SGS | https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom | [bcb-sgs.md](../../discovery/fichas/bcb-sgs.md) |
| BCB IFData | https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/documentacao | [bcb-ifdata.md](../../discovery/fichas/bcb-ifdata.md) |
| Câmara | https://dadosabertos.camara.leg.br/swagger/api.html e o FAQ | [camara-dados-abertos.md](../../discovery/fichas/camara-dados-abertos.md) |

## Como executar localmente
A partir da raiz do repositório:

```bash
uv sync --project experiments/python/discovery
uv run --directory experiments/python/discovery pytest                # testes, sem rede
uv run --project experiments/python/discovery inventario --rodada 1   # execução real
```

Opções e códigos de saída: [contracts/cli.md](contracts/cli.md). Validação completa: [quickstart.md](quickstart.md).

## Exemplos de requisição e resposta
Execução real da rodada 1 em 2026-11-25 20:42 UTC, relatório [inventario-20261125T204235Z.json](../../discovery/reports/inventario-20261125T204235Z.json):

```text
[1/4] ibge-localidades ............. respondeu  200  json  161 ms
[2/4] bcb-sgs ...................... respondeu  200  json  206 ms
[3/4] bcb-ifdata ................... sem teste automatizado
[4/4] camara-dados-abertos ......... respondeu  200  json  285 ms

4 fontes: 3 responderam, 0 falharam, 1 sem teste, 0 com divergência
```

Sonda do IFData, adicionada depois da leitura da documentação, em 2026-11-25 20:52 UTC, relatório [inventario-20261125T205222Z.json](../../discovery/reports/inventario-20261125T205222Z.json): `respondeu  200  json  337 ms`.

Estruturas observadas (só nomes e tipos):

| Fonte | Registros em | Campos |
|---|---|---|
| IBGE `/estados` | raiz (lista) | `id` inteiro, `sigla` texto, `nome` texto, `regiao.{id,sigla,nome}` |
| BCB SGS 432 | raiz (lista) | `data` data (`dd/mm/aaaa`), `valor` **texto** |
| Câmara `/deputados` | `dados` | `id`, `idLegislatura` inteiros; `nome`, `siglaPartido`, `siglaUf`, `email`, `uri`, `uriPartido`, `urlFoto` textos |
| IFData `/odata` | `value` | `kind`, `name`, `url` textos (a lista de recursos do serviço) |

## O que funcionou
- **Tempo:** a rodada completa levou **4,9 s**, contra a meta de menos de 1 minuto (SC-001).
- **Ritmo:** uma consulta por fonte, com cerca de 2,2 s entre os inícios (SC-005).
- **Privacidade:** nenhum valor das respostas foi para os relatórios. Nomes e e-mails de parlamentares, presentes na resposta da Câmara, não aparecem (SC-004, FR-015). Isso é garantido por construção, porque o modelo da amostra não tem onde guardar valor, e testado com dados pessoais fictícios.
- **Testes:** 155 testes sem rede, com o `conftest.py` bloqueando sockets. Cobrem todas as causas de falha (tempo esgotado, indisponível, TLS, 401/SSO, 403, 429, 5xx, 4xx, excesso de redirecionamentos, resposta inválida), truncamento, interrupção e o relatório validado contra o schema.
- **Validação do catálogo:** encontrou um problema real logo no primeiro teste. O `datajud` tem `docs_url: null`, e a ferramenta passou a aceitar isso em vez de exigir uma URL que ninguém conferiu.

## O que falhou ou surpreendeu
- **BCB SGS:** o `docs_url` do catálogo (`https://api.bcb.gov.br/`) só redireciona para a página inicial do BCB. A documentação real fica nas páginas de recurso de cada série no portal de dados abertos. Já corrigido no catálogo.
- **BCB SGS:** há limites que o catálogo não registrava. Janela máxima de 10 anos por consulta, `/ultimos/N` até 20 e, desde 26/03/2025, filtros de data obrigatórios. Além disso, o `valor` vem como **texto**.
- **BCB IFData:** a raiz do serviço OData serve de sonda sem parâmetro nenhum. Porém, uma chamada composta a `ListaDeRelatorio` com `$top`/`$format` deu 400, e os códigos de `TipoInstituicao` e `Relatorio` não estão documentados.
- **IBGE:** a documentação recusa leitura automatizada (403). Licença, limites e filtros continuam não verificados.
- **Câmara:** o Swagger é montado por JavaScript, então os endpoints de proposições e votações não puderam ser lidos automaticamente. O máximo de 100 itens por página vem de um tutorial de 2017.
- **Erro de TLS:** o `respx` recria a exceção simulada e perde a causa original. Por isso a detecção de erro de TLS também olha a mensagem (`[SSL: CERTIFICATE_VERIFY_FAILED]`), que é como o `httpx` real entrega o erro.

## Limitações
- Uma sondagem mostra a conectividade de **um endereço numa data**. Não confirma licença, limites nem estabilidade ao longo do tempo.
- A detecção de login é heurística: status 401, `WWW-Authenticate` ou redirecionamento para o SSO do gov.br ou para caminhos com `login`, `auth` ou `sso`.
- O teto de leitura de 1 MiB impede inferir a estrutura de JSON grande (fica "indisponível, resposta truncada").
- O XML é lido com `xml.etree` da biblioteca padrão, sem `defusedxml`. Basta para sondagem, mas deve ser revisto se uma fonte XML entrar com volume.
- Só as fontes da rodada 1 foram sondadas. As rodadas 2 e 3 continuam sem `probe_url`.
- O tempo limite (15 s) é conferido no total da consulta só depois de cada bloco lido; antes do primeiro bloco valem os limites por fase do httpx. Numa conexão lenta seguida de servidor parado, uma consulta pode durar cerca de 2× o tempo limite, e uma rodada de 3 fontes nessas condições passaria de 1 minuto. É aceito para uma ferramenta de sondagem (detalhes no R8 de [research.md](research.md)).

## Convergência
O `/speckit-converge` rodou duas vezes depois da implementação:
- **1ª rodada:** encontrou um problema crítico. Uma fonte com defeito (corpo comprimido corrompido ou JSON aninhado demais) derrubava a execução inteira, contra o princípio V da constituição. Também mostrou que o tempo limite valia por fase, e não por consulta. Os dois foram corrigidos nas tarefas T037 e T038 (PR #15).
- **2ª rodada:** sobrou só o limite efetivo do tempo limite, documentado acima (T039).

## Verificações finais
- **SC-007 (testes sem rede):** em 2026-11-25, a suíte rodou dentro de um sandbox do macOS que nega todo acesso à rede (`sandbox-exec -p '(version 1)(allow default)(deny network*)' uv run --offline ...`). Primeiro, confirmei que uma chamada real ao IBGE falha dentro do sandbox. Depois, os **155 testes passaram**.
- **SC-006 (leitura do relatório):** o relatório HTML da rodada 1 foi lido pelo usuário em 2026-11-25, e dele se tira, para cada fonte, se responde, se exige autenticação, o formato e as divergências.

## Checklist de conclusão
- [x] A fonte foi identificada e documentada (4 fichas da rodada 1)
- [x] As condições de acesso foram verificadas (sondagem real e documentação oficial, com grau por resposta)
- [x] O dado foi consumido ou baixado (uma consulta por fonte; só a estrutura foi registrada)
- [x] A estrutura dos dados foi inspecionada
- [x] Os casos de erro foram testados (todas as causas, com respostas simuladas)
- [x] O resultado pode ser reproduzido (comandos acima; relatórios versionados)
- [x] As limitações estão registradas
- [x] A utilidade do experimento foi avaliada (abaixo)

## Decisões e próximos passos
- **Utilidade:** alta. Em menos de 5 s a ferramenta confirma o estado das fontes, e o catálogo saiu mais correto. Vale rodar de novo antes de cada experimento, com `--fonte` ou `--rodada`.
- **ADRs:** nenhum novo. As decisões do E0 são locais à ferramenta e estão em [research.md](research.md). A ADR 0001 (convenções de API) segue como proposta até o E1.
- **E1 (IBGE, Python):** pode começar. Antes do plano, ler a documentação do IBGE no navegador e preencher licença, limites, filtros (`orderBy`, `view`) e o formato dos códigos de município.
- **E2 (BCB SGS):** desenhar desde o início a paginação por janelas de 10 anos, a conversão de `valor` de texto para decimal e o código da série de IPCA em 12 meses.
- **E3 (Câmara):** confirmar no Swagger os endpoints de proposições e votações e o máximo atual de `itens`.
- **Inventário:** acrescentar `probe_url` às fontes da rodada 2 (Senado, Portal da Transparência) quando chegar a vez delas. O Portal exige chave, e a ferramenta deve apenas registrar isso, sem tentar contornar.

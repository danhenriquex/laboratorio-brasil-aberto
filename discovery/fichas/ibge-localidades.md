# Ficha da fonte: IBGE — API de localidades

- **Domínio:** geografia
- **Documentação oficial:** https://servicodados.ibge.gov.br/api/docs/localidades
- **Última verificação:** 2026-11-25
- **Acesso:** facil

Marque cada campo com o grau de verificação: **[confirmado]** (documentação oficial ou observação direta do endpoint oficial), **[parcial]** (indício de terceiros ou documentação incompleta) ou **[não verificado]**.

> **Como a documentação foi lida:** em 2026-11-25, as páginas `/api/docs/` e `/api/docs/localidades` responderam **HTTP 403** à leitura automatizada. No mesmo dia, o usuário abriu `/api/docs/localidades` no navegador e trouxe:
> - a introdução;
> - as seções "Aglomerações urbanas por identificador", "Municípios", "Municípios por UF", "por mesorregião", "por microrregião", "por região imediata" e "Município por identificador";
> - a informação de que o rodapé não mostra nada.
>
> As respostas marcadas "(doc. no navegador)" vêm desse material.
>
> **Escopo da API** (introdução): "países e às divisões político-administrativas do Brasil bem como meso e microrregiões", conforme a resolução PR nº 51/1989. As regiões geográficas **imediatas e intermediárias** "passam a substituir as mesorregiões e microrregiões geográficas de forma progressiva até 21/12/2023" e "serão periodicamente revisadas". Há um **Query Builder** para montar consultas.

## Checklist de discovery

| Pergunta | Resposta | Verificação |
|---|---|---|
| Existe API pública? | Sim: API REST em `https://servicodados.ibge.gov.br/api/v1/localidades/...`. `/estados` respondeu 200 com JSON. | [confirmado] sondagem E0 em 2026-11-25 |
| Há documentação oficial? | Sim, em `/api/docs/localidades`. Abre no navegador e recusa leitura automatizada (403). | [confirmado] (doc. no navegador) |
| Exige cadastro, token ou chave? | Não: respondeu 200 sem credenciais. A documentação não menciona autenticação. | [confirmado] sondagem E0 |
| Limites de requisição? | Não encontrado na documentação oficial (nem nas seções lidas nem no rodapé). | [confirmado] ausência na documentação; limite real [não verificado] |
| Paginação e filtros? | Sem paginação: as listas vêm inteiras. `orderBy`: por padrão os municípios vêm ordenados por `id`; `orderBy=nome` ordena alfabeticamente. `view=nivelado` coloca todas as localidades no mesmo nível, em vez da hierarquia aninhada padrão. Vários identificadores numa chamada, separados por `\|`. | [confirmado] (doc. no navegador) e sondagem |
| Frequência de atualização? | As regiões imediatas e intermediárias "serão periodicamente revisadas". Não há periodicidade nem data de atualização dos municípios. | [parcial] (doc. no navegador) |
| Existe histórico de dados? | Meso e microrregiões coexistem com as regiões imediatas e intermediárias, que as substituem desde 21/12/2023. Municípios extintos ou versões anteriores da divisão territorial: não encontrado nas seções lidas. | [parcial] (doc. no navegador) |
| Formatos disponíveis? | JSON: "a resposta JSON é configurada para refletir a hierarquia". Outros formatos: não encontrado na documentação. | [confirmado] JSON (doc. no navegador e sondagem) |
| Licença e termos de uso? | **Não encontrado na documentação oficial**: a página de localidades não traz licença nem termos, e o rodapé está vazio. | [confirmado] ausência; licença real [não verificado] |
| Como as entidades são identificadas? | "Exceptuando-se as rotas referentes aos países, os identificadores providos pela presente API são oficialmente designados pelo IBGE." Formatos, pelos exemplos oficiais:<br>• UF: 2 dígitos (`33` = RJ, `35` = SP)<br>• mesorregião: 4 (`3301`)<br>• microrregião: 5 (`33001`)<br>• região imediata: 6 (`310055`)<br>• **município: 7** (`3304557` = Rio de Janeiro)<br>• aglomeração urbana: texto com zeros à esquerda (`00301`)<br>No JSON, o `id` é `number`. Município também pode ser buscado por "URL amigável" (`rio-de-janeiro`, sem acentos e com hífens). Países seguem a M49 da ONU. | [confirmado] (doc. no navegador) |
| Dados completos ou apenas amostra? | Completos: `/municipios` "obtém o conjunto de municípios do Brasil" numa resposta, e `/estados` veio inteiro na sondagem. | [confirmado] (doc. no navegador) e sondagem |
| Comportamento em indisponibilidade? | Não documentado. | [não verificado] |
| O dado identifica uma pessoa? | Não: são unidades territoriais. | [confirmado] |

## Endpoints relevantes para o E1
Todos documentados em `/api/docs/localidades`. Os que terminam em `/municipios` aceitam `orderBy` e `view`.

| Endpoint | O que devolve |
|---|---|
| `/api/v1/localidades/estados` | UFs (sondado no E0) |
| `/api/v1/localidades/estados/{UF}/municipios` | municípios de uma ou mais UFs (`33\|35`) |
| `/api/v1/localidades/municipios` | todos os municípios do Brasil |
| `/api/v1/localidades/municipios/{id ou nome}` | um ou mais municípios por código de 7 dígitos ou "URL amigável". O esquema da resposta não está documentado nesta seção |
| `/api/v1/localidades/regioes-imediatas/{id}/municipios` | municípios de uma ou mais regiões imediatas |
| `/api/v1/localidades/mesorregioes/{id}/municipios` e `/microrregioes/{id}/municipios` | municípios por meso e microrregião (recortes em substituição) |

**Esquema de município** (documentado):
- `id` (number) e `nome` (string);
- `microrregiao` { `id`, `nome`, `mesorregiao` { … } };
- `regiao-imediata` { `id`, `nome`, `regiao-intermediara` { … } }.

A chave aparece escrita como `regiao-intermediara` na documentação, provavelmente um erro de digitação de `regiao-intermediaria`. Conferir na resposta real antes de modelar o E1.

## Resultado do teste de conectividade
- **Data e hora:** 2026-11-25 20:42:35 UTC (relatório `discovery/reports/inventario-20261125T204235Z.json`)
- **Status HTTP e latência:** 200, 161 ms
- **Endereço:** `https://servicodados.ibge.gov.br/api/v1/localidades/estados`, sem redirecionamento
- **Observações:**
  - formato declarado e detectado JSON, sem divergência;
  - sem `Content-Length` (resposta transmitida em blocos);
  - estrutura: lista na raiz com `id` (inteiro), `sigla` (texto), `nome` (texto) e `regiao` (objeto com `id`, `sigla`, `nome`).

## Decisão
- **Consumir por API, baixar arquivos ou ingerir de forma agendada?** Consumir por API, com cache de TTL longo, porque a divisão territorial muda raramente. É a fonte do E1.
- **Limitações e riscos:**
  - sem licença, termos nem limites declarados na documentação de localidades;
  - documentação inacessível a ferramentas automáticas (403);
  - recortes regionais em transição: preferir as regiões **imediatas e intermediárias** às meso e microrregiões;
  - possível erro de digitação no nome de uma chave do esquema documentado.
- **Próximo passo:**
  - no E1, usar o código de município de 7 dígitos como identificador e considerar `view=nivelado` para simplificar a resposta;
  - procurar a licença geral dos dados do IBGE fora desta página (ex.: termos do portal ibge.gov.br) e, se não houver, registrar "não encontrei".

# Ficha da fonte: IBGE — API de localidades

- **Domínio:** geografia
- **Documentação oficial:** https://servicodados.ibge.gov.br/api/docs/localidades
- **Última verificação:** 2026-11-25
- **Acesso:** facil

Marque cada campo com o grau de verificação: **[confirmado]** (documentação oficial ou observação direta do endpoint oficial), **[parcial]** (indício de terceiros) ou **[não verificado]**.

> Em 2026-11-25, as páginas de documentação (`/api/docs/` e `/api/docs/localidades`) responderam **HTTP 403** à leitura automatizada. No mesmo dia, o usuário leu `/api/docs/localidades` no navegador e trouxe a introdução e a seção "Aglomerações urbanas por identificador". As respostas marcadas "(doc. lida no navegador)" vêm desse texto. As demais seguem não verificadas.
>
> **Escopo da API** (introdução da documentação): "países e às divisões político-administrativas do Brasil bem como meso e microrregiões", conforme a resolução PR nº 51/1989. As regiões geográficas **imediatas e intermediárias** "passam a substituir as mesorregiões e microrregiões geográficas de forma progressiva até 21/12/2023" e "serão periodicamente revisadas". Há um **Query Builder** para montar consultas.

## Checklist de discovery

| Pergunta | Resposta | Verificação |
|---|---|---|
| Existe API pública? | Sim: `https://servicodados.ibge.gov.br/api/v1/localidades/...` respondeu 200 com JSON. | [confirmado] sondagem E0 em 2026-11-25 |
| Há documentação oficial? | Sim, em `servicodados.ibge.gov.br/api/docs/localidades`. Abre no navegador e recusa leitura automatizada (403). | [confirmado] (doc. lida no navegador) |
| Exige cadastro, token ou chave? | Não: respondeu 200 sem nenhuma credencial. | [confirmado] sondagem E0 em 2026-11-25 |
| Limites de requisição? | Não consegui ler a documentação. | [não verificado] |
| Paginação e filtros? | Sem paginação: `/estados` vem inteiro numa resposta. Ordenação alfabética com `orderBy=nome`. Vários identificadores numa só chamada, separados por `\|` (pipe), ex.: `/aglomeracoes-urbanas/{id1}\|{id2}`. Outros parâmetros (ex.: `view`) não lidos ainda. | [confirmado] sem paginação (sondagem); `orderBy` e pipe (doc. lida no navegador, seção "Aglomerações urbanas"); demais [não verificado] |
| Frequência de atualização? | As regiões imediatas e intermediárias "serão periodicamente revisadas". Periodicidade não informada no trecho lido. | [parcial] (doc. lida no navegador) |
| Existe histórico de dados? | Mesorregiões e microrregiões coexistem com as regiões imediatas e intermediárias, que as substituem progressivamente até 21/12/2023. Municípios extintos e versões antigas da divisão: não lidos. | [parcial] (doc. lida no navegador) |
| Formatos disponíveis? | JSON observado (`application/json`). Outros formatos não verificados. | [confirmado] JSON; demais [não verificado] |
| Licença e termos de uso? | Não consegui ler a documentação. | [não verificado] |
| Como as entidades são identificadas? | "Exceptuando-se as rotas referentes aos países, os identificadores providos pela presente API são oficialmente designados pelo IBGE." Nas UFs e regiões, o `id` é inteiro e há `sigla` (texto). Nas aglomerações urbanas, o identificador aparece como texto com zeros à esquerda (ex.: `00301`). Os países seguem a metodologia M49 da ONU. Número de dígitos dos códigos de UF e de município: não lido. | [confirmado] origem oficial (doc. lida no navegador) e campos e tipos (sondagem); dígitos [não verificado] |
| Dados completos ou apenas amostra? | `/estados` devolveu a lista completa numa resposta só (2.446 bytes). | [confirmado] sondagem E0 |
| Comportamento em indisponibilidade? | Não observado nem documentado. | [não verificado] |
| O dado identifica uma pessoa? | Não: são unidades territoriais. | [confirmado] estrutura observada |

## Resultado do teste de conectividade
- **Data e hora:** 2026-11-25 20:42:35 UTC (relatório `discovery/reports/inventario-20261125T204235Z.json`)
- **Status HTTP e latência:** 200, 161 ms
- **Endereço:** `https://servicodados.ibge.gov.br/api/v1/localidades/estados`, sem redirecionamento
- **Observações:**
  - formato declarado e detectado JSON, sem divergência;
  - sem `Content-Length` (resposta transmitida em blocos);
  - estrutura: lista na raiz com `id` (inteiro), `sigla` (texto), `nome` (texto) e `regiao` (objeto com `id`, `sigla`, `nome`).

## Decisão
- **Consumir por API, baixar arquivos ou ingerir de forma agendada?** Consumir por API, com cache de TTL longo (divisão territorial muda raramente). É a fonte do E1.
- **Limitações e riscos:**
  - documentação inacessível a ferramentas automáticas (403);
  - licença, limites e formatos sem confirmação;
  - recortes regionais em transição: no E1, preferir as regiões **imediatas e intermediárias** às meso e microrregiões, que estão sendo substituídas.
- **Próximo passo:** antes do plano do E1, ler no navegador a seção de municípios (formato do código e parâmetros como `view`) e procurar licença, termos e limites no rodapé ou na página inicial de `/api/docs/`.

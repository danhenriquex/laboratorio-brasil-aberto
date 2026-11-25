# Ficha da fonte: Banco Central — séries temporais (SGS)

- **Domínio:** economia
- **Documentação oficial:** https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom (página do conjunto, com os recursos JSON, CSV e SOAP)
- **Última verificação:** 2026-11-25
- **Acesso:** facil

Marque cada campo com o grau de verificação: **[confirmado]** (documentação oficial ou observação direta do endpoint oficial), **[parcial]** (indício de terceiros) ou **[não verificado]**.

> O `docs_url` atual do catálogo (`https://api.bcb.gov.br/`) só redireciona (302) para a página inicial do BCB; não é documentação. A documentação está nas páginas de recurso de cada série no portal de dados abertos.

## Checklist de discovery

| Pergunta | Resposta | Verificação |
|---|---|---|
| Existe API pública? | Sim: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial=dd/MM/aaaa&dataFinal=dd/MM/aaaa` e `.../dados/ultimos/{N}?formato=json`. | [confirmado] [recurso JSON](https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom/resource/2cb57a62-49de-405d-938b-482051a6e166) e sondagem E0 |
| Há documentação oficial? | Sim, nas páginas de recurso da série no portal de dados abertos ("Interface json do serviço BCData/SGS"). | [confirmado] |
| Exige cadastro, token ou chave? | Não: respondeu 200 sem credenciais. A documentação não menciona autenticação. | [confirmado] sondagem E0 em 2026-11-25 |
| Limites de requisição? | Período máximo de **10 anos** entre `dataInicial` e `dataFinal`, com erro se exceder. `/ultimos/N` **limitado a 20**. Desde 26/03/2025, "tornando-se obrigatório o uso de filtros" de data. Limite de taxa (requisições por minuto): não encontrado. | [confirmado] limites de período e volume; taxa [não verificado] |
| Paginação e filtros? | Sem paginação; o filtro é por período (`dataInicial`, `dataFinal` em `dd/MM/aaaa`) ou por `ultimos/N`. | [confirmado] |
| Frequência de atualização? | Não informada ("Tempestividade: Não se aplica"). | [não verificado] |
| Existe histórico de dados? | Série 432 desde **1999-03-05**, sem data de fim. | [confirmado] [página do conjunto](https://dadosabertos.bcb.gov.br/dataset/432-taxa-de-juros---meta-selic-definida-pelo-copom) |
| Formatos disponíveis? | JSON e CSV (`formato=json` ou `formato=csv`); há também uma interface SOAP (WSDL). | [confirmado] |
| Licença e termos de uso? | Open Data Commons Open Database License (**ODbL**). | [confirmado] página do conjunto |
| Como as entidades são identificadas? | A série, pelo código numérico (432 = "meta, definida pelo Copom, para a taxa Selic", % a.a., periodicidade diária). Cada registro tem `data` (texto `dd/mm/aaaa`) e `valor` (**texto**, não número). | [confirmado] código na documentação; campos e tipos na sondagem E0 |
| Dados completos ou apenas amostra? | Completos, mas cada consulta fica limitada a uma janela de 10 anos. | [confirmado] |
| Comportamento em indisponibilidade? | Só está documentado o erro para período acima de 10 anos; códigos HTTP e mensagens não estão documentados. | [parcial] |
| O dado identifica uma pessoa? | Não: são indicadores agregados. | [confirmado] |

## Resultado do teste de conectividade
- **Data e hora:** 2026-11-25 20:42:37 UTC (relatório `discovery/reports/inventario-20261125T204235Z.json`)
- **Status HTTP e latência:** 200, 206 ms
- **Endereço:** `https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json`, sem redirecionamento
- **Observações:**
  - formato JSON, declarado e detectado; 39 bytes, com `Content-Length` informado;
  - estrutura: lista com `data` (data no formato `dd/mm/aaaa`) e `valor` (**texto**). Converter para decimal no serviço, com cuidado com o separador.

## Decisão
- **Consumir por API, baixar arquivos ou ingerir de forma agendada?** Por API, com cache (séries mudam no máximo uma vez por dia). Para histórico longo, paginar por janelas de até 10 anos. É a fonte do E2.
- **Limitações e riscos:**
  - janela máxima de 10 anos e `ultimos` limitado a 20;
  - filtros obrigatórios desde 2025, um sinal de que a API muda de regras;
  - `valor` chega como texto;
  - frequência de atualização não documentada.
- **Próximo passo:** trocar o `docs_url` do catálogo pela página do conjunto. No E2, ler a [página de metadados da série](https://www3.bcb.gov.br/sgspub/consultarmetadados/consultarMetadadosSeries.do?method=consultarMetadadosSeriesInternet&hdOidSerieSelecionada=432) e confirmar o código da série de inflação (IPCA em 12 meses), para responder "Qual é a Selic atual e a inflação em 12 meses?".

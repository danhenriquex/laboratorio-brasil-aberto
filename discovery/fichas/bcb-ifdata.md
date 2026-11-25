# Ficha da fonte: Banco Central — IFData (instituições financeiras)

- **Domínio:** economia
- **Documentação oficial:** https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/documentacao e `$metadata` em https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata/$metadata
- **Última verificação:** 2026-11-25
- **Acesso:** facil (hipótese do catálogo; sem sondagem automatizada até agora)

Marque cada campo com o grau de verificação: **[confirmado]** (documentação oficial ou observação direta do endpoint oficial), **[parcial]** (indício de terceiros) ou **[não verificado]**.

> A página `/aplicacao` (o `docs_url` atual) é uma aplicação web que não mostra conteúdo sem JavaScript. A página do conjunto no portal de dados abertos respondeu **HTTP 400** à leitura automatizada em 2026-11-25.

## Checklist de discovery

| Pergunta | Resposta | Verificação |
|---|---|---|
| Existe API pública? | Sim: serviço OData v4 em `https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata`. A raiz respondeu 200 em JSON. | [confirmado] leitura da documentação em 2026-11-25 |
| Há documentação oficial? | Sim: a página `/documentacao` lista os parâmetros OData, e o `$metadata` descreve recursos e campos. Não explica os códigos. | [confirmado] |
| Exige cadastro, token ou chave? | Não encontrado na documentação. A raiz respondeu sem credenciais. | [parcial] |
| Limites de requisição? | Não encontrado. | [não verificado] |
| Paginação e filtros? | `$top`, `$skip`, `$filter`, `$orderby`, `$select`, `$format`. Tamanho máximo de página não declarado. | [confirmado] `/documentacao` |
| Recursos e parâmetros obrigatórios | `IfDataCadastro(AnoMes)`; `IfDataValores(AnoMes, TipoInstituicao, Relatorio)`; `ListaDeRelatorio()`, sem parâmetros. Os valores válidos de `TipoInstituicao` e `Relatorio` não estão documentados. | [confirmado] `$metadata`; códigos [não verificado] |
| Frequência de atualização? | Não encontrado (a página do conjunto falhou). | [não verificado] |
| Existe histórico de dados? | Não encontrado. O parâmetro `AnoMes` indica séries por data-base. | [não verificado] |
| Formatos disponíveis? | Observados: JSON (raiz) e XML (`$metadata`). A lista de valores de `$format` não está documentada. | [confirmado] JSON e XML observados; lista [não verificado] |
| Licença e termos de uso? | O catálogo registra ODbL a partir do portal de dados abertos, mas não foi possível reconfirmar nesta rodada (página 400). | [parcial] |
| Como as entidades são identificadas? | Campos `CodInst`, `CnpjInstituicaoLider`, `CodConglomeradoFinanceiro` e `CodConglomeradoPrudencial`. A regra de formação não está documentada. | [confirmado] campos; regra [não verificado] |
| Dados completos ou apenas amostra? | Não verificado. | [não verificado] |
| Comportamento em indisponibilidade? | Não documentado. Uma chamada composta a `ListaDeRelatorio?$top=1&$format=json` devolveu 400 (causa não verificada). | [não verificado] |
| O dado identifica uma pessoa? | Identifica pessoas jurídicas (instituições e CNPJ); pessoas físicas não aparecem no esquema. | [confirmado] `$metadata` |

## Resultado do teste de conectividade
- **Data e hora:** 2026-11-25. Sem teste automatizado no E0 (`probe_url: null`), e o relatório marca a fonte como "sem teste automatizado". Durante a leitura da documentação, a raiz do serviço respondeu uma vez.
- **Status HTTP e latência:** raiz `/odata` com 200 e `application/json` (latência não medida).
- **Observações:** a raiz devolve `@odata.context` e a lista de recursos, sem exigir parâmetros. A chamada composta a `ListaDeRelatorio` com `$top`/`$format` deu 400 e precisa ser investigada antes de qualquer uso.

## Decisão
- **Consumir por API, baixar arquivos ou ingerir de forma agendada?** Ingestão agendada por data-base (`AnoMes`), quando houver experimento para ela; hoje está fora do roteiro E1–E6.
- **Limitações e riscos:**
  - códigos de `TipoInstituicao` e `Relatorio` não documentados;
  - página do conjunto inacessível a ferramentas automáticas;
  - a sintaxe exata das chamadas de função ainda não foi validada.
- **Próximo passo:** adicionar `probe_url` = raiz do serviço OData (`https://olinda.bcb.gov.br/olinda/servico/IFDATA/versao/v1/odata`), para que a próxima rodada do inventário teste a conectividade. Antes de consumir os dados, descobrir os valores válidos dos parâmetros.

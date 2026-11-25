# Ficha da fonte: Câmara dos Deputados — dados abertos

- **Domínio:** estado
- **Documentação oficial:** https://dadosabertos.camara.leg.br/swagger/api.html (API) e https://dadosabertos.camara.leg.br/faq/faq-home.html (FAQ)
- **Última verificação:** 2026-11-25
- **Acesso:** facil

Marque cada campo com o grau de verificação: **[confirmado]** (documentação oficial ou observação direta do endpoint oficial), **[parcial]** (indício de terceiros ou documento oficial antigo) ou **[não verificado]**.

> A página do Swagger é montada por JavaScript, e a leitura automatizada não obteve a lista de endpoints e parâmetros. Endpoints e filtros abaixo, além de `/deputados`, ficam para a leitura manual no navegador.

## Checklist de discovery

| Pergunta | Resposta | Verificação |
|---|---|---|
| Existe API pública? | Sim: API REST v2 em `https://dadosabertos.camara.leg.br/api/v2/`. `/deputados?itens=1` respondeu 200 em JSON. | [confirmado] sondagem E0 e portal |
| Há documentação oficial? | Sim: Swagger, FAQ e tutoriais no portal. | [confirmado] |
| Exige cadastro, token ou chave? | Não: "não é preciso se cadastrar, nem se identificar". A sondagem respondeu sem credenciais. | [confirmado] FAQ e sondagem E0 |
| Limites de requisição? | Limite de taxa: não encontrado. Máximo de itens por página: 100 segundo um tutorial oficial de 2017 ("Quando da publicação deste tutorial"); padrão 15. | [parcial] tutorial antigo |
| Paginação e filtros? | Parâmetros `pagina` e `itens`. A resposta traz `dados` e `links` (`self`, `next`, `previous`, `first`, `last`). Filtros e ordenação não foram lidos. | [confirmado] envelope `dados` na sondagem; parâmetros [parcial] tutorial 2017; filtros [não verificado] |
| Frequência de atualização? | Arquivos para download: "Atualização diária". API: não informado. | [confirmado] arquivos; API [não verificado] |
| Existe histórico de dados? | Sim, variando por conjunto: legislaturas desde 1826; proposições completas desde 2001; órgãos e membros desde a legislatura 51; cota parlamentar desde 2008. | [confirmado] Swagger e FAQ |
| Formatos disponíveis? | API: JSON e XML, escolhidos pelo cabeçalho `Accept` (tutorial). Sem `Accept` específico, a sondagem recebeu JSON. Arquivos em lote: CSV, XLSX, ODS, JSON, XML. | [confirmado] JSON e arquivos; XML via `Accept` [parcial] |
| Licença e termos de uso? | Licença formal não encontrada. O FAQ diz que os dados são públicos e gratuitos, sem restrição a uso em aplicativos pagos, e cita restrições a informações pessoais e familiares (Ato da Mesa 45/2012). | [parcial] sem licença formal |
| Como as entidades são identificadas? | Deputado e partido têm `id` numérico exclusivo (o do partido não é o eleitoral), e as entidades trazem `uri`. A sondagem viu `id`, `idLegislatura` (inteiros), `uri` e `uriPartido`. | [confirmado] |
| Dados completos ou apenas amostra? | A API é paginada. Os arquivos anuais em lote (`proposicoes-{ano}`, `votacoes-{ano}`, `votacoesVotos-{ano}`) trazem conjuntos completos. | [confirmado] |
| Comportamento em indisponibilidade? | Não documentado. | [não verificado] |
| O dado identifica uma pessoa? | **Sim**: `nome`, `email` e `urlFoto` de parlamentares (figuras públicas). A ferramenta do E0 não guardou os valores. Nos serviços, expor só o necessário e respeitar o Ato da Mesa 45/2012. | [confirmado] estrutura observada |

## Resultado do teste de conectividade
- **Data e hora:** 2026-11-25 20:42:39 UTC (relatório `discovery/reports/inventario-20261125T204235Z.json`)
- **Status HTTP e latência:** 200, 285 ms
- **Endereço:** `https://dadosabertos.camara.leg.br/api/v2/deputados?itens=1`, sem redirecionamento
- **Observações:**
  - formato JSON, sem `Content-Length`;
  - registros em `dados`, com `id`, `idLegislatura` (inteiros), `nome`, `siglaPartido`, `siglaUf`, `email`, `uri`, `uriPartido` e `urlFoto` (textos).

## Decisão
- **Consumir por API, baixar arquivos ou ingerir de forma agendada?** API para consultas pontuais (E3: paginação e filtros). Arquivos anuais em lote para votações e votos, se o volume pedir.
- **Limitações e riscos:**
  - máximo de itens por página baseado em tutorial de 2017;
  - sem licença formal;
  - endpoints de proposições e votações ainda não confirmados na documentação;
  - dados pessoais de parlamentares.
- **Próximo passo:** no plano do E3, ler o Swagger no navegador e confirmar os endpoints e filtros de `/proposicoes`, as tramitações, `/votacoes` e os votos, e o máximo atual de `itens`.

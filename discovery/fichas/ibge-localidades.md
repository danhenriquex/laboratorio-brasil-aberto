# Ficha da fonte: IBGE — API de localidades

- **Domínio:** geografia
- **Documentação oficial:** https://servicodados.ibge.gov.br/api/docs/localidades
- **Última verificação:** 2026-11-25
- **Acesso:** facil

Marque cada campo com o grau de verificação: **[confirmado]** (documentação oficial ou observação direta do endpoint oficial), **[parcial]** (indício de terceiros) ou **[não verificado]**.

> Em 2026-11-25, as páginas de documentação (`/api/docs/` e `/api/docs/localidades`) responderam **HTTP 403** à leitura automatizada. As respostas abaixo que dependem da documentação ficam como não verificadas até a leitura manual no navegador.

## Checklist de discovery

| Pergunta | Resposta | Verificação |
|---|---|---|
| Existe API pública? | Sim: `https://servicodados.ibge.gov.br/api/v1/localidades/...` respondeu 200 com JSON. | [confirmado] sondagem E0 em 2026-11-25 |
| Há documentação oficial? | Sim, em `servicodados.ibge.gov.br/api/docs/localidades`, mas ela recusou a leitura automatizada (403). | [parcial] existência; conteúdo [não verificado] |
| Exige cadastro, token ou chave? | Não: respondeu 200 sem nenhuma credencial. | [confirmado] sondagem E0 em 2026-11-25 |
| Limites de requisição? | Não consegui ler a documentação. | [não verificado] |
| Paginação e filtros? | Não consegui ler a documentação. A resposta de `/estados` vem inteira, sem envelope de paginação. | [confirmado] sem paginação em `/estados`; filtros [não verificado] |
| Frequência de atualização? | Não consegui ler a documentação. | [não verificado] |
| Existe histórico de dados? | Não consegui ler a documentação. | [não verificado] |
| Formatos disponíveis? | JSON observado (`application/json`). Outros formatos não verificados. | [confirmado] JSON; demais [não verificado] |
| Licença e termos de uso? | Não consegui ler a documentação. | [não verificado] |
| Como as entidades são identificadas? | Campo `id` inteiro nas UFs e nas regiões, mais `sigla` (texto). O número de dígitos de cada código não foi registrado, porque a sonda não guarda valores. | [confirmado] campos e tipos; formato dos códigos [não verificado] |
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
- **Limitações e riscos:** documentação inacessível a ferramentas automáticas (403); licença e limites sem confirmação.
- **Próximo passo:** ler a documentação no navegador e registrar licença, limites, filtros (ex.: `orderBy`, `view`) e o formato dos códigos de município, antes do plano do E1.

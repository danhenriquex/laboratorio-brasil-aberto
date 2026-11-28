# Roteiro de experimentos

Cada experimento é um ciclo do Spec Kit (specify, plan, tasks, implement) com um timebox curto e um `RESULTS.md`. Os prompts prontos ficam em `docs/prompts/`; os demais são escritos quando chegar a vez de cada um.

| # | Experimento | Linguagem | O que ensina |
|---|---|---|---|
| E0 | Inventário e conectividade das fontes | Python | Quais fontes respondem, com que autenticação e formato |
| E1 | Serviço de localidades (IBGE) | Python | Contrato HTTP, cache, tratamento de erro, testes |
| E4 | Serviço de localidades (IBGE), de novo | Java | Ergonomia: setup, testes e contratos, lado a lado com o E1 |
| E7 | Serviço de localidades (IBGE), em Go | Go | Binário único e biblioteca padrão, com a mesma régua do E1 e do E4 |
| E8 | Serviço de localidades (IBGE), em Rust | Rust | Eficiência e garantias em tempo de compilação contra o custo de construir |
| E2 | Séries do BCB | Python | Séries temporais, OData, estabilidade da API |
| E3 | Proposições da Câmara | Python | Paginação, filtros, normalização |
| E5 | Simulador de crédito (SAC e Price) | Java | Modelagem de domínio, precisão decimal, Strategy |
| E6 | Portal da Transparência | Python | Chave, limite de requisições, fila e backoff |

O E4 foi antecipado para logo depois do E1 (2026-11-27), para comparar a ergonomia com o E1 ainda fresco. O E7 e o E8 entraram com a constituição 1.1.0 ([ADR 0002](adr/0002-go-e-rust-como-linguagens.md)) e vêm logo depois do E4, pelo mesmo motivo. O E7 foi concluído em 2026-11-28 ([RESULTS](../specs/004-localidades-go/RESULTS.md)): passou nos 82 cenários, com respostas idênticas às do E1 e do E4. O E8 foi concluído no mesmo dia ([RESULTS](../specs/005-localidades-rust/RESULTS.md)): passou nos 82 cenários, com respostas idênticas às das outras três. A ordem de execução é a da tabela.

Depois, com os serviços estabelecidos: ingestão agendada, MCP, RAG e chatbot.

## Regras
- E1, E4, E7 e E8 usam a mesma especificação e o mesmo contrato OpenAPI (`contracts/`), com planos diferentes, e passam pela mesma suíte de caixa-preta.
- Num serviço que só repassa chamadas externas, a rede domina o tempo. Compare ergonomia no E1, no E4, no E7 e no E8, e design de domínio no E5.
- O desempenho só é comparado em tarefas onde ele pode diferir (cálculo, processamento de arquivos).
- Decisões de arquitetura viram ADR em `docs/adr/`.

## Perguntas que orientam os serviços
Anote aqui as perguntas reais que você quer responder. Mais tarde elas viram o conjunto de avaliação do RAG.

1. Qual é a Selic atual e a inflação em 12 meses?
2. Quais municípios existem neste estado?
3. Em que fase está este projeto de lei e como cada partido votou?
4. Sofri um acidente de trânsito: o que fazer e quais normas se aplicam?
5. Quanto este município recebeu em transferências e como evoluiu?

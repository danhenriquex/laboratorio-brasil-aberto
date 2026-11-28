# Laboratório Brasil Aberto

Laboratório pessoal para explorar dados públicos brasileiros e experimentar tecnologias (Python, Java, Go e Rust). Leia `.specify/memory/constitution.md` antes de qualquer trabalho: ela é a fonte das regras do projeto.

## Como trabalhar aqui
- Responda em português do Brasil.
- Fluxo do Spec Kit: `/speckit-specify` (o quê, sem tecnologia), `/speckit-plan` (o como), `/speckit-tasks`, `/speckit-implement`, `/speckit-converge` (repita implement e converge até `Converged`).
- Cada experimento tem uma pergunta, um timebox e um `RESULTS.md` (modelo em `docs/templates/RESULTS.md`). Decisões de arquitetura viram ADR em `docs/adr/`.
- O roteiro está em `docs/roteiro.md` e o catálogo de fontes em `discovery/sources.json`.

## Regras que mais importam
- Testes automatizados nunca chamam APIs reais. Use fixtures ou respostas simuladas (`respx` em Python).
- Classificações de acesso e limites de fontes são hipóteses até conferidas na documentação oficial. Registre confirmado, parcial ou não verificado.
- Todo dado devolvido por um serviço carrega fonte e data de coleta.
- Nunca versionar segredos. Chaves ficam em `.env`.
- Não recomende investimentos nem execute transações. Em temas jurídicos, cite a norma e a vigência, e diga "não encontrei" quando a fonte não cobrir.
- Mantenha simples: sem infraestrutura nova antes de haver necessidade comprovada.

## Estrutura
- `specs/`: uma pasta por experimento (criada pelo Spec Kit)
- `discovery/`: catálogo, fichas e relatórios das fontes
- `experiments/<linguagem>/` (`python`, `java`, `go`, `rust`): código dos experimentos
- `services/`: serviços que "se graduam" dos experimentos
- `contracts/`: especificações OpenAPI
- `docs/`: roteiro, prompts, templates e ADRs

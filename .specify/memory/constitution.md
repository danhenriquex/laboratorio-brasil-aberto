# Laboratório Brasil Aberto Constitution

Este projeto é um laboratório pessoal para explorar o Brasil por meio de dados públicos e fontes oficiais. A prioridade não é uma arquitetura definitiva: é descobrir quais dados existem, como acessá-los, quais perguntas podem ser respondidas e quais tecnologias servem a cada problema.

Fluxo de trabalho: explorar → coletar → entender → experimentar → comparar → decidir.

## Core Principles

### I. Fontes oficiais primeiro
Use órgãos públicos e instituições responsáveis pelos dados sempre que possível. Blogs, repositórios de terceiros e notícias servem de indício, nunca de confirmação. Toda afirmação sobre acesso, limites ou licença de uma fonte deve apontar para a documentação oficial.

### II. Rastreabilidade (NON-NEGOTIABLE)
Todo dado devolvido por um serviço carrega a fonte, a data de coleta e o identificador ou a versão do registro. Para normas, inclui também a data de vigência. Sem procedência, o dado não sai do serviço.

### III. Verificar antes de afirmar
Condições de acesso (cadastro, chave, limites, licença, formato) são registradas com um grau de verificação: confirmado (fonte oficial), parcial (indício de terceiros) ou não verificado. Classificações de dificuldade são hipóteses até serem testadas. Dados publicados podem ser incompletos, incorretos ou fora de padrão.

### IV. Testes sem rede
Testes automatizados nunca chamam APIs reais. Usam respostas gravadas (fixtures) ou simuladas. Chamadas reais acontecem apenas em verificações manuais e no inventário de fontes, e seus resultados são registrados com data.

### V. Resiliência por padrão
Toda chamada externa tem timeout, tratamento de erro de domínio e cache com TTL quando o dado muda pouco. Limites de requisição das fontes são respeitados, sem tentativas agressivas. A queda de uma fonte não derruba os demais serviços.

### VI. Contrato como fronteira
Todo serviço que expõe API mantém uma especificação OpenAPI versionada em `contracts/`. Erros seguem o formato `application/problem+json` (RFC 9457). Entre serviços de linguagens diferentes, compartilha-se o contrato, nunca o código. Cada serviço é dono dos seus dados.

### VII. Privacidade e dados pessoais
Comece com dados públicos. Dado público pode ainda identificar uma pessoa: pergunte "este dado identifica alguém?" antes de coletar, guardar ou exibir. Não colete dados pessoais ou bancários de terceiros sem base legal e necessidade legítimas (LGPD).

### VIII. Cautela jurídica e financeira
Apresente fontes, premissas e limites. Distinga o texto da lei, a orientação de um órgão público e uma interpretação aplicada ao caso. Respostas citam a norma e a data de vigência, e dizem "não encontrei" quando a fonte não cobre a pergunta. Uma resposta automatizada não é aconselhamento profissional individual. O sistema não recomenda investimentos nem executa transações. Sobre temas politicamente contestados, descreve as decisões e os argumentos de cada lado sem emitir veredito.

### IX. Segredos fora do código
Chaves, tokens e credenciais ficam em variáveis de ambiente ou em arquivos `.env` que nunca são versionados. Segredos não passam por argumentos de ferramentas nem por prompts de modelos.

### X. Simplicidade
Não adicione infraestrutura complexa antes de existir necessidade comprovada. Prefira um repositório único com serviços independentes em pastas separadas. Separar em serviço exige uma razão: linguagem diferente, ciclo de dados diferente, restrição da fonte ou isolamento de falha.

## Additional Constraints

- **Linguagens:** Python 3.11+ e Java (JDK de suporte longo, versão a confirmar no E4). TypeScript fica fora do escopo inicial.
- **Padrões de serviço:** endpoints `/health` e `/metrics`, versionamento no caminho (`/v1/...`), paginação e filtros com convenção única, cabeçalho de correlação entre serviços.
- **Dados:** registre licença e termos de uso de cada fonte. Dados acessíveis publicamente não são necessariamente livres de restrições.
- **Ordem de construção:** entender as fontes, estabelecer os serviços, só então construir chatbot e RAG.

## Development Workflow

- Cada experimento é uma feature do Spec Kit, com timebox, uma pergunta que responde e critério de pronto.
- A especificação descreve o quê e não fala de tecnologia. O plano decide o como (linguagem, framework, padrões).
- Todo experimento termina com um `RESULTS.md` (dificuldades, resultados, limitações e próximos passos) e, quando houver decisão de arquitetura, um ADR em `docs/adr/`.
- Checklist de conclusão: fonte documentada; condições de acesso verificadas; dado consumido ou baixado; estrutura inspecionada; casos de erro testados; resultado reproduzível; limitações registradas; utilidade avaliada.
- Comparações entre linguagens usam a mesma especificação e planos diferentes, e não declaram vencedor antes de medir.

## Governance

Esta constituição prevalece sobre outras práticas do projeto. Alterações exigem registro da razão (em ADR quando afetarem a arquitetura) e atualização da versão abaixo. Complexidade adicional deve ser justificada contra o princípio X.

**Version**: 1.0.0 | **Ratified**: 2026-11-14 | **Last Amended**: 2026-11-14

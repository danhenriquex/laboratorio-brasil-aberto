# Feature Specification: E0 — Inventário e conectividade das fontes

**Feature Branch**: `001-inventario-fontes`

**Created**: 2026-11-24

**Status**: Draft

**Input**: User description: "Quero uma ferramenta de linha de comando que catalogue e avalie fontes públicas brasileiras de dados, para que eu entenda quais podem ser integradas de forma sustentável antes de construir serviços." (descrição completa em `docs/prompts/E0-inventario-fontes.md`, seção 1)

**Pergunta do experimento**: Quais fontes do catálogo respondem hoje, com que autenticação e em que formato, e onde as hipóteses de acesso do catálogo estavam erradas?

**Timebox**: 1 a 2 sessões curtas.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sondar as fontes do catálogo e ver o resultado (Priority: P1)

Como desenvolvedor do laboratório, rodo a ferramenta localmente. Ela lê o catálogo de fontes, faz uma única consulta a cada fonte que tem endereço de teste e me entrega um relatório estruturado com o que observou: se respondeu, em quanto tempo, em que formato, com que tamanho, se pediu autenticação e quando a consulta foi feita.

**Why this priority**: É a resposta direta à pergunta do experimento. Sem isso, não há como confrontar as hipóteses do catálogo com a realidade nem decidir o E1.

**Independent Test**: Com um catálogo de três fontes e respostas simuladas (uma normal, uma fora do ar, uma que exige chave), a execução termina e o relatório estruturado traz um resultado para cada uma das três, com causa da falha onde houver.

**Acceptance Scenarios**:

1. **Given** uma fonte com endereço de teste que responde normalmente, **When** a ferramenta é executada, **Then** o relatório mostra o código de resposta, a latência, o formato observado, o tamanho da resposta e a data e hora da coleta.
2. **Given** uma fonte fora do ar ou que não responde dentro do tempo limite, **When** a ferramenta é executada, **Then** o relatório registra a falha com a causa (tempo esgotado, conexão recusada, nome não resolvido etc.) e a execução continua com as demais fontes.
3. **Given** uma fonte que exige chave ou credencial, **When** a ferramenta é executada, **Then** o relatório marca "exige autenticação" e a ferramenta não tenta nenhuma forma de contorno.
4. **Given** uma fonte que devolve um formato diferente do esperado (por exemplo, uma página HTML de erro no lugar de dados), **When** a ferramenta é executada, **Then** o relatório registra o formato realmente observado.
5. **Given** uma fonte sem endereço de teste no catálogo, **When** a ferramenta é executada, **Then** ela aparece no relatório como "sem teste automatizado", com o link da documentação para verificação manual, e nenhuma consulta é feita a ela.

---

### User Story 2 - Entender a estrutura dos dados sem guardar os dados (Priority: P2)

Quando uma fonte responde com dados estruturados, quero ver no relatório quais campos ela devolve e de que tipo é cada um (texto, número, data, lista, objeto), a partir de uma amostra pequena. Os valores em si não são guardados, para não reter dados pessoais.

**Why this priority**: Saber a forma dos dados orienta o desenho dos serviços (E1 a E3), mas só faz sentido depois de saber se a fonte responde.

**Independent Test**: Com uma resposta simulada contendo nomes e e-mails de pessoas, o relatório lista os campos `nome` e `email` com seus tipos e não contém nenhum dos valores originais.

**Acceptance Scenarios**:

1. **Given** uma resposta estruturada (lista de registros ou objeto), **When** a amostra é inspecionada, **Then** o relatório lista os nomes dos campos e seus tipos, incluindo campos aninhados.
2. **Given** uma resposta com dados que identificam pessoas, **When** o relatório é gerado, **Then** nenhum valor da resposta aparece no relatório, só nomes de campos e tipos.
3. **Given** uma resposta tabular (colunas com cabeçalho), **When** a amostra é inspecionada, **Then** o relatório lista os nomes das colunas.
4. **Given** uma resposta que não pode ser interpretada no formato que declara, **When** a amostra é inspecionada, **Then** o relatório registra "resposta inválida" com a causa, sem interromper a execução.

---

### User Story 3 - Relatório legível com hipótese versus observado (Priority: P3)

Quero abrir um relatório legível no navegador que mostre, fonte por fonte, o grau de verificação (confirmado, parcial, não verificado), a hipótese de acesso que estava no catálogo e o que foi observado, destacando onde as duas divergem.

**Why this priority**: Acelera a revisão das hipóteses e a decisão do próximo experimento, mas o relatório estruturado da US1 já contém a informação.

**Independent Test**: A partir de um relatório estruturado de exemplo em que uma fonte tinha hipótese "nenhuma autenticação" e foi observada exigindo chave, o relatório legível destaca essa divergência.

**Acceptance Scenarios**:

1. **Given** uma execução concluída, **When** o relatório legível é aberto, **Then** cada fonte aparece com nome, domínio, grau de verificação, hipótese de acesso, resultado observado e link da documentação.
2. **Given** uma fonte cuja hipótese de autenticação ou disponibilidade não bate com o observado, **When** o relatório legível é aberto, **Then** a divergência aparece destacada.
3. **Given** uma execução concluída, **When** os dois relatórios são comparados, **Then** contêm as mesmas fontes e os mesmos resultados.

---

### User Story 4 - Rodar só uma parte do catálogo (Priority: P3)

Quero poder limitar a execução a uma rodada do catálogo (por exemplo, só a rodada 1: IBGE, BCB e Câmara) ou a fontes específicas, para não consultar fontes que não estou estudando no momento.

**Why this priority**: Conveniência que reduz consultas desnecessárias às fontes; a execução completa já atende ao experimento.

**Independent Test**: Com um catálogo de fontes em rodadas 1 e 2, pedir só a rodada 1 gera um relatório apenas com as fontes da rodada 1 e nenhuma consulta às da rodada 2.

**Acceptance Scenarios**:

1. **Given** um catálogo com fontes de várias rodadas, **When** peço só a rodada 1, **Then** só as fontes da rodada 1 são consultadas e aparecem no relatório.
2. **Given** um identificador de fonte inexistente, **When** peço essa fonte, **Then** a ferramenta avisa que não a encontrou no catálogo e não faz consultas.

---

### Edge Cases

- Catálogo ausente, ilegível ou com uma fonte sem campos obrigatórios: a ferramenta informa qual é o problema (e qual fonte, se for o caso) antes de fazer qualquer consulta, sem gerar relatório parcial enganoso.
- Redirecionamento: o relatório registra que houve redirecionamento e o endereço final; redirecionamento para uma página de login conta como "exige autenticação".
- Bloqueio (acesso negado) ou limite de requisições atingido: registrados como causas distintas, com o tempo de espera sugerido pela fonte quando ela o informar. A ferramenta não tenta de novo na mesma execução.
- Resposta muito grande: a ferramenta lê só o necessário para a amostra e registra que a resposta foi truncada, sem baixar o conteúdo inteiro.
- Resposta vazia ou lista sem registros: o relatório registra "sem registros na amostra" no lugar da estrutura.
- Erro de certificado ou de conexão segura: registrado como causa própria, sem desativar a verificação de segurança.
- Interrupção da execução pelo usuário: as fontes já consultadas não se perdem; o relatório indica que a execução foi interrompida.
- Todas as fontes falham: a execução termina normalmente com um relatório que mostra todas as falhas.

## Requirements *(mandatory)*

### Functional Requirements

**Catálogo**

- **FR-001**: A ferramenta MUST ler o catálogo de fontes em `discovery/sources.json`, usando de cada fonte: identificador, nome, domínio, link da documentação, endereço de teste (opcional), tipo de dado, hipótese de acesso, autenticação esperada, grau de verificação e rodada.
- **FR-002**: A ferramenta MUST validar o catálogo antes de qualquer consulta e informar com clareza qualquer fonte malformada.
- **FR-003**: A ferramenta MUST NOT alterar o catálogo; o grau de verificação atualizado é sugestão no relatório, e a decisão de atualizar o catálogo é manual.

**Sondagem**

- **FR-004**: Para cada fonte com endereço de teste, a ferramenta MUST fazer exatamente uma consulta de leitura por execução, sem nova tentativa.
- **FR-005**: A ferramenta MUST consultar as fontes uma de cada vez, com um intervalo mínimo entre consultas (padrão de 2 segundos, ajustável).
- **FR-006**: Cada consulta MUST ter um tempo limite (padrão de 15 segundos, ajustável).
- **FR-007**: A ferramenta MUST NOT fazer consultas que escrevam ou alterem dados nas fontes, nem enviar credenciais, nem tentar contornar autenticação, bloqueio ou limite de requisições.
- **FR-008**: A ferramenta MUST se identificar nas consultas de forma genérica (nome da ferramenta do laboratório), sem dados pessoais do usuário.
- **FR-009**: Para cada consulta, a ferramenta MUST registrar: código de resposta, latência, formato observado (JSON, CSV, XML, HTML ou outro), tamanho da resposta, se exigiu autenticação, se houve redirecionamento e para onde, e data e hora da coleta com fuso horário.
- **FR-010**: Falhas MUST ser classificadas por causa: tempo esgotado, fonte indisponível (conexão ou nome), erro de conexão segura, acesso negado, exige autenticação, limite de requisições, erro da fonte, resposta inválida. Uma falha em uma fonte MUST NOT interromper a execução das demais.
- **FR-011**: O formato observado MUST ser determinado pelo conteúdo e pelo tipo declarado na resposta, e o relatório MUST indicar quando os dois divergem.
- **FR-012**: Fontes sem endereço de teste MUST aparecer no relatório como "sem teste automatizado", com o link da documentação, sem consulta.
- **FR-013**: O usuário MUST poder limitar a execução a uma ou mais rodadas ou a fontes específicas pelo identificador.

**Amostra e privacidade**

- **FR-014**: A ferramenta MUST inspecionar uma amostra limitada da resposta (alguns registros, com teto de tamanho lido) e registrar os nomes dos campos e seus tipos, incluindo campos aninhados e colunas de dados tabulares.
- **FR-015**: Os relatórios MUST NOT conter valores vindos das respostas, só nomes de campos, tipos e metadados da consulta.
- **FR-016**: A ferramenta MUST NOT guardar o corpo das respostas em disco.

**Relatórios**

- **FR-017**: Cada execução MUST gerar dois relatórios em `discovery/reports/`, um estruturado e um legível no navegador, com a data e hora da execução no nome, sem sobrescrever execuções anteriores.
- **FR-018**: Os relatórios MUST trazer, por fonte: identificação, domínio, link da documentação, grau de verificação do catálogo, grau sugerido pela observação, hipótese de acesso, resultado observado e a divergência entre hipótese e observado (autenticação e disponibilidade).
- **FR-019**: Os relatórios MUST trazer um resumo da execução: total de fontes, quantas responderam, quantas falharam (por causa), quantas sem teste automatizado, início e fim da execução, e se ela foi interrompida.
- **FR-020**: Os relatórios MUST deixar claro que o resultado de uma sondagem mostra a conectividade de um endereço numa data, e que licença, limites e termos de uso só se confirmam na documentação oficial.
- **FR-021**: Ao terminar, a ferramenta MUST mostrar no terminal um resumo curto e os caminhos dos dois relatórios.

### Key Entities

- **Fonte**: uma entrada do catálogo. Identificador, nome, domínio, link da documentação, endereço de teste opcional, tipo de dado, hipótese de acesso, autenticação esperada, grau de verificação, rodada e notas.
- **Resultado de sondagem**: o que foi observado numa fonte numa execução. Situação (respondeu, falhou, sem teste automatizado), causa da falha, código de resposta, latência, formato observado e declarado, tamanho, autenticação exigida, redirecionamento, data e hora da coleta, estrutura da amostra e divergências em relação à hipótese.
- **Estrutura da amostra**: lista de campos com nome, tipo e caminho (para aninhados), mais a indicação de amostra vazia ou truncada. Nunca contém valores.
- **Execução**: um conjunto de resultados de sondagem, com início, fim, filtros aplicados, configuração (intervalo e tempo limite) e resumo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma execução com as 4 fontes da rodada 1 termina em menos de 1 minuto e gera os dois relatórios.
- **SC-002**: 100% das fontes do catálogo (ou do filtro escolhido) aparecem no relatório, inclusive as que falharam e as sem teste automatizado.
- **SC-003**: Em testes com respostas simuladas, cada um dos cenários de falha das Edge Cases produz a causa correta no relatório, e a execução sempre chega ao fim.
- **SC-004**: Nenhum valor de resposta aparece nos relatórios, verificado com uma resposta simulada contendo dados pessoais fictícios.
- **SC-005**: Nenhuma fonte recebe mais de uma consulta por execução, e o intervalo entre consultas consecutivas nunca é menor que o configurado.
- **SC-006**: Lendo só o relatório legível, consigo dizer em menos de 5 minutos, para cada fonte da rodada 1, se ela responde, se exige autenticação, em que formato e onde a hipótese do catálogo estava errada.
- **SC-007**: Os testes automatizados rodam sem acesso à rede.

## Assumptions

- O usuário é o próprio desenvolvedor do laboratório, rodando a ferramenta localmente com acesso à internet; não há múltiplos usuários nem permissões.
- O catálogo atual (`discovery/sources.json`, versão de esquema 1) é a referência de formato; os endereços de teste nele são hipóteses até a primeira execução.
- O grau sugerido pela observação vale só para a conectividade e a autenticação daquele endereço: uma sondagem bem-sucedida não confirma licença, limites ou termos de uso (princípio III).
- Valores padrão de intervalo (2 s) e tempo limite (15 s) são razoáveis para APIs públicas e podem ser ajustados por execução.
- "Exige autenticação" é inferido da resposta (acesso não autorizado, ou redirecionamento para login); acesso proibido sem indício de login é registrado como "acesso negado".
- Os relatórios de execuções reais podem ser versionados no repositório, pois não contêm valores das respostas nem segredos.
- Ao fim do experimento, as fichas das fontes da rodada 1 (IBGE, BCB, Câmara) em `discovery/fichas/` e o `RESULTS.md` são preenchidos manualmente a partir do relatório; não são gerados pela ferramenta.
- Fora do escopo: contornar autenticação, coletar dados em volume, consultas que escrevam nas fontes, agendamento de execuções e histórico comparativo entre execuções.

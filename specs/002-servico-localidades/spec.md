# Feature Specification: E1 — Serviço de localidades (IBGE)

**Feature Branch**: `002-servico-localidades`

**Created**: 2026-11-26

**Status**: Draft

**Input**: User description: "Começar o E1 do roteiro: um serviço de localidades sobre a API do IBGE, com contrato HTTP, cache, tratamento de erro e testes." (escrito a partir de `docs/roteiro.md`, da ficha `discovery/fichas/ibge-localidades.md` e da ADR 0001)

**Pergunta do experimento**: O que é preciso para expor as localidades do IBGE como um serviço próprio, com contrato estável, procedência em cada resposta e comportamento previsível quando o IBGE falha ou demora?

**Timebox**: 2 a 3 sessões curtas.

**Especificação compartilhada**: esta especificação vale também para o E4, que implementa o mesmo serviço em outra linguagem. Ela descreve só o comportamento visível de fora. O contrato publicado é o mesmo nos dois experimentos, e só o plano muda.

## User Scenarios & Testing *(mandatory)*

Os consumidores do serviço são o desenvolvedor do laboratório e, mais tarde, outros serviços e um agente de IA. Todos falam com o serviço pela rede, seguindo o contrato publicado.

### User Story 1 - Listar estados e os municípios de um estado (Priority: P1)

Como consumidor, peço a lista das unidades federativas e, escolhida uma delas, a lista dos seus municípios. Cada resposta traz os dados oficiais e diz de onde vieram e quando foram coletados.

**Why this priority**: Responde à pergunta-guia nº 2 do roteiro ("Quais municípios existem neste estado?") e é o caminho mínimo que exercita contrato, procedência e consulta à fonte. Sozinha, já é um serviço útil.

**Independent Test**: Com respostas simuladas do IBGE, pedir a lista de estados e depois os municípios de uma UF. As duas respostas seguem o contrato e trazem fonte e data de coleta.

**Acceptance Scenarios**:

1. **Given** o serviço no ar, **When** o consumidor pede as unidades federativas, **Then** recebe as 27, cada uma com código de 2 dígitos, sigla, nome e grande região, mais a fonte e a data e hora da coleta.
2. **Given** uma UF existente, informada pela sigla (em maiúsculas ou minúsculas) ou pelo código de 2 dígitos, **When** o consumidor pede os seus municípios, **Then** recebe a lista em ordem alfabética, com código de 7 dígitos e nome oficial de cada município, e com a procedência.
3. **Given** uma UF com mais municípios do que cabem numa página, **When** o consumidor pede uma página e um tamanho de página, **Then** recebe só aqueles itens e é informado do total e de como pedir as demais páginas.
4. **Given** uma sigla bem formada que não corresponde a nenhuma UF (por exemplo, `XX`), **When** o consumidor pede os seus municípios, **Then** recebe um erro padronizado de "não encontrado".

---

### User Story 2 - Consultar um município pelo código oficial (Priority: P1)

Como consumidor, informo o código de 7 dígitos de um município e recebo o nome oficial, a UF a que pertence e as regiões geográficas imediata e intermediária, com a procedência.

**Why this priority**: O código de 7 dígitos é a chave que os outros experimentos vão usar para cruzar dados (transferências, deputados por UF etc.). Consultar por ele é o uso mais frequente que se espera do serviço.

**Independent Test**: Com respostas simuladas, consultar um código existente, um inexistente e um mal formado, e verificar as três respostas contra o contrato.

**Acceptance Scenarios**:

1. **Given** um código de município existente (por exemplo, `3304557`), **When** o consumidor o consulta, **Then** recebe código, nome oficial, UF (código e sigla), região imediata e região intermediária (código e nome de cada), mais a procedência.
2. **Given** um código com 7 dígitos que não corresponde a nenhum município, **When** o consumidor o consulta, **Then** recebe um erro padronizado de "não encontrado".
3. **Given** um código mal formado (letras, menos ou mais de 7 dígitos), **When** o consumidor o consulta, **Then** recebe um erro padronizado de "entrada inválida", e o IBGE não é consultado.
4. **Given** um município de nome com acento ou apóstrofo (por exemplo, `Santa Bárbara d'Oeste`), **When** o consumidor o consulta, **Then** o nome vem exatamente como o IBGE publica.

---

### User Story 3 - Comportamento previsível quando o IBGE falha ou demora (Priority: P2)

Como consumidor, quero saber exatamente o que aconteceu quando o serviço não consegue me dar o dado: se o erro foi meu, se a fonte está fora do ar, se demorou demais ou se respondeu algo inesperado. E, quando o serviço já tem uma cópia do dado, prefiro recebê-la, sabendo de quando ela é, a receber um erro.

**Why this priority**: É o centro do aprendizado do E1 (tratamento de erro e cache) e o que permite que outros serviços dependam deste sem herdar as falhas do IBGE (Constituição V).

**Independent Test**: Simular o IBGE fora do ar, lento e respondendo conteúdo inesperado, com e sem cópia guardada, e verificar o tipo de erro, o tempo até a resposta e a indicação de cópia desatualizada.

**Acceptance Scenarios**:

1. **Given** um dado consultado há pouco e ainda dentro da validade, **When** o consumidor o pede de novo, **Then** recebe a mesma resposta sem que o IBGE seja consultado outra vez, e a data de coleta é a da consulta original.
2. **Given** o IBGE fora do ar e nenhuma cópia guardada, **When** o consumidor pede um dado, **Then** recebe um erro padronizado de "fonte indisponível".
3. **Given** o IBGE sem responder dentro do prazo e nenhuma cópia guardada, **When** o consumidor pede um dado, **Then** recebe um erro padronizado de "fonte lenta" assim que o prazo se esgota.
4. **Given** o IBGE fora do ar e uma cópia guardada já fora da validade, **When** o consumidor pede o dado, **Then** recebe a cópia, marcada como desatualizada e com a data de coleta original.
5. **Given** o IBGE respondendo conteúdo que não segue o formato esperado (por exemplo, uma página de erro ou um campo obrigatório ausente) e nenhuma cópia guardada, **When** o consumidor pede o dado, **Then** recebe um erro padronizado de "resposta inesperada da fonte", e o serviço continua atendendo os demais pedidos.

---

### User Story 4 - Encontrar um município pelo nome dentro de um estado (Priority: P3)

Como consumidor, informo uma UF e parte do nome de um município, sem me preocupar com acentos ou maiúsculas, e recebo os municípios que combinam.

**Why this priority**: Pessoas e agentes de IA conhecem os municípios pelo nome, não pelo código. É o caminho de "Niterói" até `3303302`. Pode esperar as histórias 1 a 3.

**Independent Test**: Com a lista simulada de municípios de uma UF, buscar `niteroi`, `NITERÓI` e `são` e verificar os resultados.

**Acceptance Scenarios**:

1. **Given** a UF `RJ`, **When** o consumidor busca `niteroi`, **Then** recebe Niterói, com código e nome oficial.
2. **Given** a UF `SP`, **When** o consumidor busca `são`, **Then** recebe todos os municípios cujo nome contém "são", em ordem alfabética e paginados.
3. **Given** uma busca sem resultado, **When** o consumidor a faz, **Then** recebe uma lista vazia com total zero, e não um erro.

---

### User Story 5 - Saber se o serviço está saudável e como está sendo usado (Priority: P3)

Como desenvolvedor do laboratório, verifico se o serviço está no ar, acompanho quantos pedidos atendeu, quantos erros houve por tipo e quantas vezes a cópia guardada evitou uma consulta ao IBGE. Também consigo seguir um pedido específico pelo identificador de correlação.

**Why this priority**: Atende os padrões de serviço da constituição (saúde, métricas, correlação) e dá os números que o `RESULTS.md` e a comparação com o E4 vão usar. Não muda o que o consumidor recebe.

**Independent Test**: Fazer alguns pedidos simulados (com acerto e erro de cache e um erro de fonte), consultar as métricas e conferir as contagens. Enviar um identificador de correlação e encontrá-lo na resposta e no registro do pedido.

**Acceptance Scenarios**:

1. **Given** o serviço no ar, **When** se verifica a saúde, **Then** a resposta é imediata e não depende de o IBGE estar respondendo.
2. **Given** pedidos já atendidos, **When** se consultam as métricas, **Then** elas mostram o total de pedidos, os erros por tipo, os acertos e as faltas da cópia guardada e o tempo das consultas ao IBGE.
3. **Given** um pedido com identificador de correlação, **When** o serviço responde, **Then** devolve o mesmo identificador e o registra junto com o pedido. Sem identificador, o serviço gera um.

---

### Edge Cases

- **Distrito Federal**: tem um único município (Brasília, `5300108`). A lista vem com um item, e a busca por nome funciona igual.
- **UF com muitos municípios**: Minas Gerais tem mais de 800. A paginação devolve páginas completas e uma última página parcial.
- **Página além do fim**: devolve lista vazia com o total correto, sem erro.
- **Tamanho de página acima do máximo, zero ou negativo**: erro de "entrada inválida" que informa o limite.
- **Sigla em minúsculas ou com espaços nas pontas**: `rj` e ` RJ ` valem como `RJ`.
- **Código de UF com 2 dígitos inexistente** (por exemplo, `99`): "não encontrado".
- **Endereço sem versão ou com versão desconhecida**: "não encontrado", no formato padronizado.
- **Vários pedidos ao mesmo tempo pelo mesmo dado ainda não guardado**: o serviço não deve consultar o IBGE uma vez para cada pedido além do necessário. No mínimo, depois da primeira resposta guardada, os demais usam a cópia.
- **Mudança no formato do IBGE** (campo renomeado, como a chave `regiao-intermediara` que a documentação mostra): o serviço trata como "resposta inesperada da fonte" e não devolve dado parcial sem avisar.
- **IBGE devolve lista vazia para uma UF existente**: tratado como resposta inesperada, porque toda UF tem ao menos um município.
- **Busca por nome com 1 caractere ou vazia**: erro de "entrada inválida", com o tamanho mínimo informado.

## Requirements *(mandatory)*

### Functional Requirements

#### Dados e consultas

- **FR-001**: O serviço MUST listar as 27 unidades federativas, cada uma com código oficial de 2 dígitos, sigla, nome e grande região (código, sigla e nome).
- **FR-002**: O serviço MUST permitir consultar uma UF pela sigla, sem diferenciar maiúsculas e minúsculas e ignorando espaços nas pontas, ou pelo código de 2 dígitos.
- **FR-003**: O serviço MUST listar os municípios de uma UF em ordem alfabética, com código oficial de 7 dígitos e nome de cada um.
- **FR-004**: O serviço MUST permitir consultar um município pelo código de 7 dígitos e devolver código, nome, UF (código e sigla), região geográfica imediata e região geográfica intermediária (código e nome de cada).
- **FR-005**: O serviço MUST permitir filtrar os municípios de uma UF por parte do nome, sem diferenciar maiúsculas, minúsculas e acentos, com no mínimo 2 caracteres.
- **FR-006**: O serviço MUST devolver nomes exatamente como o IBGE os publica, com acentos, apóstrofos e hífens.
- **FR-007**: Listas de municípios MUST ser paginadas. O consumidor escolhe a página e o tamanho, até um máximo documentado no contrato, e a resposta informa a página, o tamanho e o total de itens.

#### Procedência (Constituição II)

- **FR-008**: Toda resposta com dados MUST trazer a procedência: o nome da fonte, o endereço da documentação oficial, a data e hora da coleta em UTC e o identificador oficial de cada registro (o código do IBGE).
- **FR-009**: Quando o dado vier de uma cópia guardada, a data de coleta MUST ser a da consulta original ao IBGE, e não a do pedido atual. Uma cópia servida fora da validade MUST vir marcada como desatualizada.

#### Erros

- **FR-010**: Todos os erros MUST seguir um único formato padronizado e legível por máquina, com tipo, título, código de status e detalhe, conforme o contrato.
- **FR-011**: O serviço MUST distinguir pelo menos estes erros: entrada inválida, não encontrado, fonte indisponível, fonte lenta e resposta inesperada da fonte.
- **FR-012**: Entradas inválidas MUST ser rejeitadas antes de qualquer consulta ao IBGE.
- **FR-013**: Mensagens de erro MUST explicar o problema ao consumidor sem expor detalhes internos (rastros de execução, endereços internos ou o corpo bruto da resposta do IBGE).

#### Resiliência (Constituição V)

- **FR-014**: Cada consulta ao IBGE MUST ter um prazo máximo configurável (padrão de 10 s). Esgotado o prazo, o pedido termina com "fonte lenta", ou com a cópia desatualizada, se houver (FR-016).
- **FR-015**: O serviço MUST guardar uma cópia de cada dado obtido do IBGE, com validade configurável (padrão de 24 horas). Dentro da validade, pedidos pelo mesmo dado MUST ser atendidos sem nova consulta à fonte.
- **FR-016**: Quando o IBGE falhar (indisponível, lento ou com resposta inesperada) e houver uma cópia guardada fora da validade, o serviço MUST devolver essa cópia, marcada como desatualizada, em vez do erro.
- **FR-017**: O serviço MUST fazer no máximo uma consulta ao IBGE por pedido do consumidor, sem novas tentativas automáticas.
- **FR-018**: Uma resposta inesperada ou uma falha da fonte num pedido MUST NOT afetar os demais pedidos nem derrubar o serviço.

#### Contrato e versionamento (Constituição VI)

- **FR-019**: O serviço MUST ter um contrato publicado e versionado no repositório, legível por máquina, que descreva todas as rotas, parâmetros, respostas e erros.
- **FR-020**: Todos os endereços de dados MUST carregar a versão (`v1`). Uma mudança incompatível no contrato exige uma nova versão.
- **FR-021**: A conformidade com o contrato MUST poder ser verificada de fora, falando com o serviço pela rede, de modo que as mesmas verificações sirvam para qualquer implementação (E1 e E4).

#### Operação

- **FR-022**: O serviço MUST oferecer uma verificação de saúde que responde sem consultar o IBGE.
- **FR-023**: O serviço MUST expor métricas com, no mínimo: total de pedidos por rota, erros por tipo, acertos e faltas da cópia guardada e tempo das consultas ao IBGE.
- **FR-024**: O serviço MUST aceitar um identificador de correlação enviado pelo consumidor, devolvê-lo na resposta e registrá-lo. Se ele não vier, o serviço gera um.
- **FR-025**: O serviço MUST registrar cada pedido com rota, resultado, duração, uso ou não da cópia guardada e identificador de correlação.
- **FR-026**: Prazo, validade da cópia, tamanho máximo de página e endereço de escuta MUST ser configuráveis sem alterar o código. O serviço não precisa de credenciais.

#### Testes (Constituição IV)

- **FR-027**: Os testes automatizados MUST rodar sem acesso à rede, usando respostas do IBGE gravadas ou simuladas.

### Key Entities

- **Unidade federativa (UF)**: código oficial de 2 dígitos, sigla de 2 letras, nome e a grande região a que pertence.
- **Grande região**: Norte, Nordeste, Sudeste, Sul ou Centro-Oeste, com código, sigla e nome.
- **Município**: código oficial de 7 dígitos, nome oficial, UF, região imediata e região intermediária.
- **Região geográfica imediata e intermediária**: recortes do IBGE que substituem as meso e microrregiões desde 2023. Cada uma tem código e nome, e a imediata pertence a uma intermediária.
- **Procedência**: fonte, endereço da documentação oficial, data e hora da coleta (UTC) e indicação de cópia desatualizada. Acompanha toda resposta com dados.
- **Página**: número da página, tamanho, total de itens e os itens da página.
- **Erro padronizado**: tipo, título, código de status e detalhe.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das respostas com dados, nos testes e numa execução manual, trazem fonte e data de coleta.
- **SC-002**: 100% das respostas exercitadas pela suíte de verificação do contrato, de sucesso e de erro, estão conformes ao contrato publicado.
- **SC-003**: Com o dado já guardado, 95% dos pedidos são respondidos em menos de meio segundo, medidos na máquina local.
- **SC-004**: Pedidos repetidos pelo mesmo dado dentro da validade geram zero consultas adicionais ao IBGE (verificado contando as consultas simuladas).
- **SC-005**: Com o IBGE fora do ar ou sem responder, 100% dos pedidos recebem um erro padronizado ou a cópia desatualizada em até 12 segundos (o prazo padrão mais uma margem). Nenhum pedido fica pendurado.
- **SC-006**: A suíte de testes passa inteira com a rede bloqueada.
- **SC-007**: Seguindo só a documentação do experimento, alguém sai do repositório clonado e obtém a primeira resposta do serviço em menos de 5 minutos.
- **SC-008**: As verificações de contrato rodam contra o serviço apenas pelo seu endereço, sem depender de nada da implementação, prontas para serem reaproveitadas no E4.

## Assumptions

- **Escopo territorial**: unidades federativas e municípios, com as regiões imediata e intermediária como atributos do município. Ficam de fora: países, distritos, subdistritos, aglomerações urbanas, meso e microrregiões (em substituição, conforme a ficha) e o histórico de municípios extintos.
- **Fonte única**: a API de localidades do IBGE é a única fonte. Não há outra fonte de contingência.
- **Validade da cópia**: 24 horas por padrão, porque a divisão territorial muda raramente (ficha do IBGE). A validade é configurável.
- **Cópia desatualizada em vez de erro**: é preferível entregar um dado territorial de alguns dias atrás, com a data visível, a não entregar nada. A procedência permite ao consumidor decidir.
- **Prazo da fonte**: 10 segundos por padrão. Nas sondagens do E0, o IBGE respondeu em cerca de 160 ms.
- **Sem autenticação**: o serviço roda localmente e não autentica consumidores. Exposição pública fica para depois, conforme o roteiro de implantação.
- **Licença**: a documentação de localidades não declara licença nem termos (ficha do IBGE). A procedência aponta para a documentação oficial, e o `RESULTS.md` registra a licença como "não encontrei" se nada aparecer até o fim do experimento.
- **Sinal de "não encontrado" do IBGE**: a documentação não diz como o IBGE responde a um código inexistente. O plano deve conferir isso numa chamada real e registrar a data.
- **Dados pessoais**: nenhum. São unidades territoriais (ficha do IBGE).
- **Convenções**: nomes de campos de procedência, formato de erro, paginação e versionamento seguem a ADR 0001, que este experimento deve confirmar ou revisar.
- **Dependências**: nenhuma infraestrutura além do próprio serviço (Constituição X). Onde e como a cópia é guardada fica para o plano.

# Feature Specification: E8 — Serviço de localidades (IBGE), em Rust

**Feature Branch**: `005-localidades-rust`

**Created**: 2026-11-28

**Status**: Draft

**Input**: User description: "E8 do roteiro: o mesmo serviço de localidades do E1, do E4 e do E7, implementado em Rust, com a mesma especificação e o mesmo contrato e um plano diferente." (`docs/roteiro.md`: "E1, E4, E7 e E8 usam a mesma especificação e o mesmo contrato OpenAPI, com planos diferentes"; constituição 1.1.0 e ADR 0002)

**Pergunta do experimento**: Como é construir e operar o mesmo serviço de localidades em Rust, do setup aos testes e ao cumprimento do mesmo contrato, comparado ao E1 (Python), ao E4 (Java) e ao E7 (Go)?

**Timebox**: 2 a 3 sessões curtas.

## Especificação compartilhada

O comportamento do serviço **não é especificado de novo aqui**. A fonte da verdade é [specs/002-servico-localidades/spec.md](../002-servico-localidades/spec.md), com:

- as histórias US1 a US5;
- os requisitos FR-001 a FR-027;
- os critérios SC-001 a SC-008;
- os casos de borda e as premissas.

O contrato é o mesmo: [contracts/localidades/openapi.yaml](../../contracts/localidades/openapi.yaml). A suíte de caixa-preta também: [contracts/localidades/verificacao/](../../contracts/localidades/verificacao/), com os 82 cenários que passam no E1, no E4 e no E7.

Qualquer mudança de comportamento passa pela spec do E1 e vale para todas as implementações. Esta spec acrescenta só o que é próprio do E8: **implementar a mesma coisa numa quarta linguagem e comparar com medidas**.

## User Scenarios & Testing *(mandatory)*

### User Stories 1 a 5 — As mesmas do E1 (Priorities: P1, P1, P2, P3, P3)

As histórias, as prioridades, os testes independentes e os cenários de aceitação são os de [specs/002-servico-localidades/spec.md](../002-servico-localidades/spec.md):

| História | Prioridade | O que entrega |
|---|---|---|
| US1 | P1 | listar estados e os municípios de um estado |
| US2 | P1 | consultar um município pelo código oficial |
| US3 | P2 | comportamento previsível quando o IBGE falha ou demora |
| US4 | P3 | encontrar um município pelo nome dentro de um estado |
| US5 | P3 | saber se o serviço está saudável e como está sendo usado |

**Independent Test** de cada uma: os cenários da história correspondente na suíte de caixa-preta passam contra o serviço em Rust.

---

### User Story 6 - Comparar o E1, o E4, o E7 e o E8 com medidas (Priority: P2)

Como desenvolvedor do laboratório, quero comparar as quatro implementações do mesmo serviço com números medidos do mesmo jeito, na mesma máquina e no mesmo dia, e com um registro do que foi fácil ou difícil em cada uma. Assim decido com base em evidência quando usar cada linguagem.

**Why this priority**: É a pergunta do experimento. Sem a comparação, o E8 seria só uma quarta implementação. Ela depende de existir um serviço funcionando (US1 a US5), por isso vem depois do MVP.

**Independent Test**: com as quatro implementações prontas, rodar o roteiro de medição do quickstart e conferir que a tabela comparativa fica preenchida para as quatro, com data e método.

**Acceptance Scenarios**:

1. **Given** as quatro implementações passando na suíte de caixa-preta, **When** as medidas são tiradas, **Then** a tabela traz, para cada uma, os mesmos itens, medidos pelo mesmo método e na mesma data.
2. **Given** a tabela preenchida, **When** alguém lê o `RESULTS.md` do E8, **Then** encontra também o registro qualitativo: o que foi mais fácil ou mais difícil em Rust (setup, testes, cumprir o contrato, erros, métricas), comparado às outras três, e por quê.
3. **Given** os comportamentos fora do contrato achados nas convergências do E4 e no E7, **When** o E8 é avaliado, **Then** o `RESULTS.md` registra quais deles apareceram também em Rust e quais não, porque essa é uma diferença de pilha HTTP que a suíte mede.
4. **Given** uma diferença medida, **When** ela é citada, **Then** vem acompanhada do contexto que a explica. O resultado não declara vencedor sem medida (constituição, fluxo de trabalho).

---

### Edge Cases

- **Os casos de borda do E1 valem todos.** A suíte de caixa-preta é a mesma, com os cenários acrescentados no E4.
- **Regra de dobra (sem acento e sem diferença de maiúsculas):** a biblioteca padrão pode não ter remoção de acentos nem *casefold*. A ordenação e a busca precisam dar **exatamente** o mesmo resultado que no E1, no E4 e no E7 para os nomes reais das fixtures.
- **Entrada mal formada antes da aplicação:** um servidor HTTP pode recusar sozinho, antes de qualquer código do serviço, um caminho com escape inválido, um método incomum ou um pedido como `OPTIONS *`, ou pode redirecionar caminhos com barras repetidas, `.` e `..`. Em todos esses casos, a resposta precisa sair no formato único de erro, com correlação. Foi o que mais custou no E4 e no E7.
- **Leitura da consulta:** a leitura dos parâmetros pode descartar em silêncio um valor mal codificado, ou pegar o primeiro de um parâmetro repetido. A regra do E1 vale: codificação inválida é erro do pedido, e vale o último valor.
- **Formato de data:** o `coletado_em` precisa sair no mesmo formato, com milissegundos e `Z`, mesmo que a biblioteca de datas formate diferente por padrão.
- **Serialização do JSON:** o conteúdo precisa ser o mesmo valor JSON das outras implementações, com os nomes de campos do contrato e na mesma ordem do E1.
- **Nomes de métricas e formato do `/metrics`:** a biblioteca de métricas pode impor convenções de nome ou negociar o formato pelo cabeçalho `Accept`. Os nomes expostos precisam ser os do contrato, e o formato, sempre o texto do Prometheus.
- **Tempo de partida:** o `verificar.sh` espera até 30 s pelo `/health`. Se a implementação demorar mais, isso é um achado a registrar, e não um motivo para mudar a suíte em silêncio.
- **Tempo de build:** linguagens compiladas com otimização podem ter build longo. O tempo é uma das medidas e precisa ser registrado tal como é, com e sem otimização se as duas formas forem usadas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O serviço MUST atender a todos os requisitos FR-001 a FR-027 de `specs/002-servico-localidades/spec.md`.
- **FR-002**: O serviço MUST passar na suíte de caixa-preta de `contracts/localidades/verificacao/` sem mudanças no contrato. A suíte só pode mudar com cenários novos que também passem contra o E1, o E4 e o E7.
- **FR-003**: O serviço MUST ler as mesmas variáveis de configuração `LOCALIDADES_*`, com os mesmos padrões e as mesmas regras de validação do E4 e do E7. Valor inválido, inclusive não finito ou que arredonda para zero, impede a partida com uma mensagem clara.
- **FR-004**: A ordenação e a busca por nome MUST produzir exatamente a mesma ordem e o mesmo resultado que o E1, o E4 e o E7 para todos os municípios das fixtures.
- **FR-005**: Os testes automatizados da implementação MUST rodar sem acesso à rede externa (Constituição IV).
- **FR-006**: A comparação MUST medir, para o E1, o E4, o E7 e o E8, pelo mesmo método, na mesma máquina e na mesma data, as 9 medidas do FR-006 do E4:
  - o tempo do repositório clonado até a primeira resposta;
  - o tempo de build;
  - o tempo da suíte de testes da implementação;
  - o tempo de partida até o `/health` responder;
  - a memória em repouso;
  - o tamanho do artefato executável;
  - as linhas de código de produção e de teste;
  - o número de dependências diretas;
  - a latência de um pedido atendido pela cópia guardada.
- **FR-007**: A comparação MUST registrar a avaliação qualitativa do E8 nos mesmos cinco pontos do E4 e do E7 (setup, escrita de testes, cumprimento do contrato escrito à mão, tratamento de erros e métricas), comparando com as outras três.
- **FR-008**: Uma diferença entre as implementações MUST NOT ser apresentada como superioridade de uma linguagem sem a medida e o contexto que a sustentam.
- **FR-009**: O `RESULTS.md` MUST registrar, para cada comportamento fora do contrato achado antes, se ele apareceu no E8 e como foi tratado: as 7 lacunas das convergências do E4 (T044 a T050) e o caso do E7 (`OPTIONS *` respondido pelo próprio servidor, T044 do E7).

### Key Entities

- **Entidades do serviço:** as mesmas de `specs/002-servico-localidades/data-model.md`.
- **Medida comparativa:** nome, valor no E1, no E4, no E7 e no E8, unidade, método de medição, data e observação.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos cenários da suíte de caixa-preta passam contra o E8, com o mesmo contrato usado pelas outras três implementações.
- **SC-002**: Os critérios SC-001 a SC-008 do E1 valem para o E8, medidos da mesma forma.
- **SC-003**: A tabela comparativa tem as 9 medidas do FR-006 preenchidas para as quatro implementações, com data e método.
- **SC-004**: A suíte de testes da implementação em Rust passa inteira com a rede externa bloqueada.
- **SC-005**: A ordem dos 645 municípios de SP e o resultado das buscas da suíte são idênticos nas quatro implementações.
- **SC-006**: Os 8 comportamentos do FR-009 têm, cada um, um registro de como se comportaram no E8.

## Assumptions

- **Fonte da verdade:** a spec do E1 é a fonte da verdade do comportamento. Se a implementação em Rust revelar ambiguidade, a correção vai para a spec e o contrato do E1, e as outras implementações são ajustadas junto.
- **Escopo:** o E8 não acrescenta funcionalidade. Ideias novas de comportamento ficam para depois do experimento.
- **Comparação em máquina local:** a mesma máquina das outras (macOS, arm64), com o cache de dependências de cada ecossistema já populado. O E1, o E4 e o E7 são medidos de novo no mesmo dia do E8.
- **Linguagem:** Rust, na versão estável vigente, confirmada na documentação oficial no plano, como pede a constituição 1.1.0. Bibliotecas e estrutura ficam para o plano.
- **Ordem de construção:** o E8 vem depois do E1, do E4 e do E7, já com as decisões e as lições conhecidas. Isso favorece o E8 em acertar o desenho e precisa constar nas limitações do `RESULTS.md`.
- **Ordem do roteiro:** o E8 fecha a sequência de comparação de linguagens começada no E4. Os E2 e E3 vêm em seguida.

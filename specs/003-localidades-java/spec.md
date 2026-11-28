# Feature Specification: E4 — Serviço de localidades (IBGE), em Java

**Feature Branch**: `003-localidades-java`

**Created**: 2026-11-27

**Status**: Draft

**Input**: User description: "E4 do roteiro: o mesmo serviço de localidades do E1, implementado em Java, com a mesma especificação e o mesmo contrato e um plano diferente." (`docs/roteiro.md`: "E1 e E4 usam a mesma especificação e o mesmo contrato OpenAPI, com planos diferentes")

**Pergunta do experimento**: Como é construir e operar o mesmo serviço de localidades em Java, do setup aos testes e ao cumprimento do mesmo contrato, comparado ao E1 em Python?

**Timebox**: 2 a 3 sessões curtas.

## Especificação compartilhada

O comportamento do serviço **não é especificado de novo aqui**. A fonte da verdade é [specs/002-servico-localidades/spec.md](../002-servico-localidades/spec.md), com:

- as histórias US1 a US5;
- os requisitos FR-001 a FR-027;
- os critérios SC-001 a SC-008;
- os casos de borda e as premissas.

O contrato é o mesmo: [contracts/localidades/openapi.yaml](../../contracts/localidades/openapi.yaml).

Qualquer mudança de comportamento passa pela spec do E1 e vale para as duas implementações. Esta spec acrescenta só o que é próprio do E4: **implementar a mesma coisa em outra linguagem e comparar com medidas**.

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

**Independent Test** de cada uma: os cenários da história correspondente na suíte de caixa-preta (`contracts/localidades/verificacao/`) passam contra o serviço em Java.

---

### User Story 6 - Comparar o E1 e o E4 com medidas (Priority: P2)

Como desenvolvedor do laboratório, quero comparar as duas implementações do mesmo serviço com números medidos do mesmo jeito, na mesma máquina e no mesmo dia, e com um registro do que foi fácil ou difícil em cada uma. Assim decido com base em evidência quando usar cada linguagem.

**Why this priority**: É a pergunta do experimento. Sem a comparação, o E4 seria só uma segunda implementação. Ela depende de existir um serviço funcionando (US1 a US5), por isso vem depois do MVP.

**Independent Test**: com as duas implementações prontas, rodar o roteiro de medição do quickstart e conferir que a tabela comparativa fica preenchida para as duas, com data e método.

**Acceptance Scenarios**:

1. **Given** as duas implementações passando na suíte de caixa-preta, **When** as medidas são tiradas, **Then** a tabela traz, para cada uma, os mesmos itens, medidos pelo mesmo método e na mesma data.
2. **Given** a tabela preenchida, **When** alguém lê o `RESULTS.md` do E4, **Then** encontra também o registro qualitativo: o que foi mais fácil ou mais difícil em cada linguagem (setup, testes, cumprir o contrato, erros, métricas) e por quê.
3. **Given** uma diferença medida, **When** ela é citada, **Then** vem acompanhada do contexto que a explica. O resultado não declara vencedor sem medida (constituição, fluxo de trabalho).

---

### Edge Cases

- **Os casos de borda do E1 valem todos.** A suíte de caixa-preta é a mesma.
- **Regra de dobra (sem acento e sem diferença de maiúsculas):** a outra linguagem pode não ter a mesma função de "casefold". A ordenação e a busca precisam dar **exatamente** o mesmo resultado que no E1 para os nomes reais das fixtures.
- **Formato de data:** o `coletado_em` precisa sair no mesmo formato, com milissegundos e `Z`, mesmo que a biblioteca de datas da outra linguagem formate diferente por padrão.
- **Nomes de métricas:** a biblioteca de métricas da outra linguagem pode impor convenções próprias, como sufixos de unidade. Os nomes expostos precisam ser os do contrato.
- **Tempo de partida:** o `verificar.sh` espera até 30 s pelo `/health`. Se a outra linguagem demorar mais para iniciar, isso é um achado a registrar, e não um motivo para mudar a suíte em silêncio.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O serviço MUST atender a todos os requisitos FR-001 a FR-027 de `specs/002-servico-localidades/spec.md`.
- **FR-002**: O serviço MUST passar na suíte de caixa-preta de `contracts/localidades/verificacao/` sem mudanças no contrato. A suíte só pode mudar com cenários novos que também passem contra o E1.
- **FR-003**: O serviço MUST ler as mesmas variáveis de configuração `LOCALIDADES_*`, com os mesmos padrões, para que o `verificar.sh` o suba com o mesmo perfil.
- **FR-004**: A ordenação e a busca por nome MUST produzir exatamente a mesma ordem e o mesmo resultado que o E1 para todos os municípios das fixtures.
- **FR-005**: Os testes automatizados da implementação MUST rodar sem acesso à rede externa (Constituição IV).
- **FR-006**: A comparação MUST medir, para o E1 e o E4, pelo mesmo método, na mesma máquina e na mesma data:
  - o tempo do repositório clonado até a primeira resposta;
  - o tempo de build;
  - o tempo da suíte de testes da implementação;
  - o tempo de partida até o `/health` responder;
  - a memória em repouso;
  - o tamanho do artefato executável;
  - as linhas de código de produção e de teste;
  - o número de dependências diretas;
  - a latência de um pedido atendido pela cópia guardada.
- **FR-007**: A comparação MUST registrar a avaliação qualitativa de cada implementação em cinco pontos: setup, escrita de testes, cumprimento do contrato escrito à mão, tratamento de erros e métricas.
- **FR-008**: Uma diferença entre o E1 e o E4 MUST NOT ser apresentada como superioridade de uma linguagem sem a medida e o contexto que a sustentam.

### Key Entities

- **Entidades do serviço:** as mesmas de `specs/002-servico-localidades/data-model.md`.
- **Medida comparativa:** nome, valor no E1, valor no E4, unidade, método de medição, data e observação.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos cenários da suíte de caixa-preta passam contra o E4, com o mesmo contrato usado pelo E1.
- **SC-002**: Os critérios SC-001 a SC-008 do E1 valem para o E4, medidos da mesma forma.
- **SC-003**: A tabela comparativa tem as 9 medidas do FR-006 preenchidas para as duas implementações, com data e método.
- **SC-004**: A suíte de testes da implementação em Java passa inteira com a rede externa bloqueada.
- **SC-005**: A ordem dos 645 municípios de SP e o resultado das buscas da suíte são idênticos nas duas implementações.

## Assumptions

- **Fonte da verdade:** a spec do E1 é a fonte da verdade do comportamento. Se a implementação em Java revelar ambiguidade, a correção vai para a spec e o contrato do E1, e o E1 é ajustado junto.
- **Escopo:** o E4 não acrescenta funcionalidade. Ideias novas de comportamento ficam para depois do experimento.
- **Comparação em máquina local:** a mesma máquina do E1 (macOS), com o cache de dependências de cada ecossistema já populado. A medição "do clone à primeira resposta" é feita com e sem cache, quando for viável.
- **Linguagem:** Java, com JDK de suporte longo. A versão é confirmada no plano, como pede a constituição.
- **Ordem do roteiro:** o E4 foi antecipado para logo depois do E1, com o E1 ainda fresco, para que a comparação de ergonomia seja mais justa. Os E2 e E3 vêm em seguida.

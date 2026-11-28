# Feature Specification: E7 — Serviço de localidades (IBGE), em Go

**Feature Branch**: `004-localidades-go`

**Created**: 2026-11-27

**Status**: Draft

**Input**: User description: "E7 do roteiro: o mesmo serviço de localidades do E1 e do E4, implementado em Go, com a mesma especificação e o mesmo contrato e um plano diferente." (`docs/roteiro.md`: "E1, E4, E7 e E8 usam a mesma especificação e o mesmo contrato OpenAPI, com planos diferentes"; constituição 1.1.0 e ADR 0002)

**Pergunta do experimento**: Como é construir e operar o mesmo serviço de localidades em Go, do setup aos testes e ao cumprimento do mesmo contrato, comparado ao E1 (Python) e ao E4 (Java)?

**Timebox**: 2 a 3 sessões curtas.

## Especificação compartilhada

O comportamento do serviço **não é especificado de novo aqui**. A fonte da verdade é [specs/002-servico-localidades/spec.md](../002-servico-localidades/spec.md), com:

- as histórias US1 a US5;
- os requisitos FR-001 a FR-027;
- os critérios SC-001 a SC-008;
- os casos de borda e as premissas.

O contrato é o mesmo: [contracts/localidades/openapi.yaml](../../contracts/localidades/openapi.yaml). A suíte de caixa-preta também: [contracts/localidades/verificacao/](../../contracts/localidades/verificacao/), com os 82 cenários do fim do E4, que já incluem os casos de borda achados nas convergências do E4 (entradas mal codificadas, métodos não suportados, cabeçalho `Accept`, parâmetros de caminho).

Qualquer mudança de comportamento passa pela spec do E1 e vale para todas as implementações. Esta spec acrescenta só o que é próprio do E7: **implementar a mesma coisa numa terceira linguagem e comparar com medidas**.

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

**Independent Test** de cada uma: os cenários da história correspondente na suíte de caixa-preta passam contra o serviço em Go.

---

### User Story 6 - Comparar o E1, o E4 e o E7 com medidas (Priority: P2)

Como desenvolvedor do laboratório, quero comparar as três implementações do mesmo serviço com números medidos do mesmo jeito, na mesma máquina e no mesmo dia, e com um registro do que foi fácil ou difícil em cada uma. Assim decido com base em evidência quando usar cada linguagem.

**Why this priority**: É a pergunta do experimento. Sem a comparação, o E7 seria só uma terceira implementação. Ela depende de existir um serviço funcionando (US1 a US5), por isso vem depois do MVP.

**Independent Test**: com as três implementações prontas, rodar o roteiro de medição do quickstart e conferir que a tabela comparativa fica preenchida para as três, com data e método.

**Acceptance Scenarios**:

1. **Given** as três implementações passando na suíte de caixa-preta, **When** as medidas são tiradas, **Then** a tabela traz, para cada uma, os mesmos itens, medidos pelo mesmo método e na mesma data.
2. **Given** a tabela preenchida, **When** alguém lê o `RESULTS.md` do E7, **Then** encontra também o registro qualitativo: o que foi mais fácil ou mais difícil em Go (setup, testes, cumprir o contrato, erros, métricas), comparado ao Python e ao Java, e por quê.
3. **Given** os achados das convergências do E4 (comportamentos padrão do servidor e do framework que o contrato não previa), **When** o E7 é avaliado, **Then** o `RESULTS.md` registra quais desses comportamentos apareceram também em Go e quais não, porque essa é uma diferença de ecossistema que a suíte mede.
4. **Given** uma diferença medida, **When** ela é citada, **Then** vem acompanhada do contexto que a explica. O resultado não declara vencedor sem medida (constituição, fluxo de trabalho).

---

### Edge Cases

- **Os casos de borda do E1 valem todos.** A suíte de caixa-preta é a mesma, com os cenários acrescentados no E4.
- **Regra de dobra (sem acento e sem diferença de maiúsculas):** a biblioteca padrão da outra linguagem pode não ter remoção de acentos nem "casefold" equivalentes. A ordenação e a busca precisam dar **exatamente** o mesmo resultado que no E1 e no E4 para os nomes reais das fixtures.
- **Normalização de caminhos pelo servidor HTTP:** servidores HTTP costumam limpar caminhos (barras duplas, `.` e `..`) e às vezes respondem com redirecionamento. A suíte espera 404 em `problem+json` para esses casos, e um redirecionamento seria uma divergência a corrigir, não a aceitar.
- **Formato de data:** o `coletado_em` precisa sair no mesmo formato, com milissegundos e `Z`, mesmo que a biblioteca de datas formate diferente por padrão.
- **Serialização do JSON:** a biblioteca da outra linguagem pode escapar caracteres por padrão (por exemplo, `<`, `>` e `&`) ou ordenar campos de outro jeito. O conteúdo precisa ser o mesmo valor JSON das outras implementações, e os nomes dos campos, os do contrato.
- **Nomes de métricas:** a biblioteca de métricas pode impor convenções próprias. Os nomes expostos precisam ser os do contrato.
- **Tempo de partida:** o `verificar.sh` espera até 30 s pelo `/health`. Se a implementação demorar mais, isso é um achado a registrar, e não um motivo para mudar a suíte em silêncio.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O serviço MUST atender a todos os requisitos FR-001 a FR-027 de `specs/002-servico-localidades/spec.md`.
- **FR-002**: O serviço MUST passar na suíte de caixa-preta de `contracts/localidades/verificacao/` sem mudanças no contrato. A suíte só pode mudar com cenários novos que também passem contra o E1 e o E4.
- **FR-003**: O serviço MUST ler as mesmas variáveis de configuração `LOCALIDADES_*`, com os mesmos padrões e as mesmas regras de validação, para que o `verificar.sh` o suba com o mesmo perfil. Valor inválido, inclusive não finito ou que arredonda para zero, impede a partida com uma mensagem clara.
- **FR-004**: A ordenação e a busca por nome MUST produzir exatamente a mesma ordem e o mesmo resultado que o E1 e o E4 para todos os municípios das fixtures.
- **FR-005**: Os testes automatizados da implementação MUST rodar sem acesso à rede externa (Constituição IV).
- **FR-006**: A comparação MUST medir, para o E1, o E4 e o E7, pelo mesmo método, na mesma máquina e na mesma data, as 9 medidas do FR-006 do E4:
  - o tempo do repositório clonado até a primeira resposta;
  - o tempo de build;
  - o tempo da suíte de testes da implementação;
  - o tempo de partida até o `/health` responder;
  - a memória em repouso;
  - o tamanho do artefato executável;
  - as linhas de código de produção e de teste;
  - o número de dependências diretas;
  - a latência de um pedido atendido pela cópia guardada.
- **FR-007**: A comparação MUST registrar a avaliação qualitativa do E7 nos mesmos cinco pontos do E4 (setup, escrita de testes, cumprimento do contrato escrito à mão, tratamento de erros e métricas), comparando com o E1 e o E4.
- **FR-008**: Uma diferença entre as implementações MUST NOT ser apresentada como superioridade de uma linguagem sem a medida e o contexto que a sustentam.
- **FR-009**: O `RESULTS.md` MUST registrar, para cada lacuna achada nas convergências do E4 (T044 a T050), se o mesmo comportamento apareceu no E7 e como foi resolvido.

### Key Entities

- **Entidades do serviço:** as mesmas de `specs/002-servico-localidades/data-model.md`.
- **Medida comparativa:** nome, valor no E1, valor no E4, valor no E7, unidade, método de medição, data e observação.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos cenários da suíte de caixa-preta passam contra o E7, com o mesmo contrato usado pelo E1 e pelo E4.
- **SC-002**: Os critérios SC-001 a SC-008 do E1 valem para o E7, medidos da mesma forma.
- **SC-003**: A tabela comparativa tem as 9 medidas do FR-006 preenchidas para as três implementações, com data e método.
- **SC-004**: A suíte de testes da implementação em Go passa inteira com a rede externa bloqueada.
- **SC-005**: A ordem dos 645 municípios de SP e o resultado das buscas da suíte são idênticos nas três implementações.
- **SC-006**: As 7 lacunas das convergências do E4 (T044 a T050) têm, cada uma, um registro de como se comportaram no E7.

## Assumptions

- **Fonte da verdade:** a spec do E1 é a fonte da verdade do comportamento. Se a implementação em Go revelar ambiguidade, a correção vai para a spec e o contrato do E1, e o E1 e o E4 são ajustados junto.
- **Escopo:** o E7 não acrescenta funcionalidade. Ideias novas de comportamento ficam para depois do experimento.
- **Comparação em máquina local:** a mesma máquina do E1 e do E4 (macOS, arm64), com o cache de dependências de cada ecossistema já populado. A medição do E1 e do E4 é refeita no mesmo dia do E7, para os números serem comparáveis.
- **Linguagem:** Go, na versão estável vigente, confirmada na documentação oficial no plano, como pede a constituição 1.1.0. Bibliotecas e estrutura ficam para o plano.
- **Ordem de construção:** o E7 vem depois do E4, já com as decisões e as correções conhecidas, como o E4 veio depois do E1. Isso favorece o E7 em acertar o desenho e precisa constar nas limitações do `RESULTS.md`.
- **Ordem do roteiro:** o E7 vem logo depois do E4, e o E8 (Rust) logo depois do E7, com a mesma régua. Os E2 e E3 vêm em seguida.

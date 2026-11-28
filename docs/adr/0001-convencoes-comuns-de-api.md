# ADR 0001: Convenções comuns de API entre serviços

- **Status:** aceita no E1 (2026-11-26) e confirmada no E4 (2026-11-27)
- **Data:** 2026-11-14 (proposta), 2026-11-26 (aceita) e 2026-11-27 (confirmada)
- **Experimentos de origem:** E1, serviço de localidades em Python (`specs/002-servico-localidades/`), e E4, o mesmo serviço em Java (`specs/003-localidades-java/`).

## Contexto
Os serviços do laboratório serão escritos em Python e Java e consumidos por clientes diferentes (outros serviços e, mais tarde, um agente de IA). Sem convenções comuns, cada serviço responderia de um jeito, e o consumidor teria de tratar cada caso.

O E1 pôs a proposta à prova num serviço real e fechou os pontos que ela deixava em aberto. As decisões detalhadas estão no `research.md` do E1, de R7 a R12.

## Decisão
1. **Contrato primeiro:** cada serviço mantém um OpenAPI 3.1 **escrito à mão** em `contracts/<servico>/openapi.yaml`. Implementações em linguagens diferentes cumprem o mesmo contrato e passam pela mesma suíte de verificação de caixa-preta, que fala com o serviço só pela rede. Geradores automáticos de OpenAPI do framework ficam desligados, para não existirem dois contratos.
2. **Erros:** `application/problem+json` (RFC 9457), com `type`, `title`, `status`, `detail` e a extensão `correlacao_id`. Os tipos são URNs estáveis, `urn:brasil-aberto:problema:<tipo>`:

   | Tipo | Status |
   |---|---|
   | `entrada-invalida` | 400 |
   | `nao-encontrado` | 404 |
   | `fonte-indisponivel` | 502 |
   | `fonte-lenta` | 504 |
   | `resposta-inesperada-da-fonte` | 502 |
   | `erro-interno` | 500 |

   O `detail` explica o problema sem rastro de execução, endereço interno nem corpo da fonte. Rotas inexistentes também respondem com um problema.
3. **Procedência:** toda resposta com dados tem a forma `{dados, meta}`, e as listas paginadas também levam `paginacao`. O `meta` traz:
   - `fonte`;
   - `url_fonte`, a URL efetivamente consultada;
   - `url_documentacao`;
   - `coletado_em`: ISO 8601 em UTC, com milissegundos e `Z`, sempre da consulta original à fonte, mesmo quando a resposta sai da cópia guardada;
   - `desatualizado`: `true` quando uma cópia vencida foi servida porque a fonte falhou.

   O identificador do registro é o campo `codigo` de cada item, e não um campo do `meta`. A `vigencia` entra no `meta` só nos serviços de normas.
4. **Identificadores:** códigos oficiais (IBGE e, depois, CNPJ) saem como **texto de tamanho fixo**, e nunca como número. Evitam perda de zeros à esquerda e facilitam o cruzamento entre fontes.
5. **Versionamento:** prefixo `/v1/` no caminho. Mudanças que quebram o contrato exigem nova versão.
6. **Paginação:**
   - parâmetros `pagina` (≥ 1, padrão 1) e `itens` (padrão 100), com o máximo definido por serviço e documentado no contrato (500 no E1);
   - a resposta traz `paginacao: {pagina, itens, total, paginas}`;
   - uma página além do fim devolve lista vazia, sem erro.
7. **Observabilidade:**
   - `/health` responde sem depender da fonte;
   - `/metrics` usa o formato do Prometheus. As métricas são prefixadas pelo nome do serviço e levam o rótulo `rota` com o **modelo** da rota (`/v1/municipios/{codigo}`), e não o caminho real;
   - o `X-Correlation-Id` é aceito se tiver de 1 a 64 caracteres em `[A-Za-z0-9._-]`; caso contrário, o serviço gera um UUID v4. Ele volta em toda resposta e no corpo dos erros;
   - o registro é uma linha JSON por pedido, sem IP.
8. **Configuração:** variáveis de ambiente com prefixo do serviço (por exemplo, `LOCALIDADES_*`), com os mesmos nomes em todas as implementações. Isso permite que a suíte de verificação suba qualquer uma delas com o mesmo perfil.

## Alternativas consideradas
- **Code-first em todos os serviços:** mais rápido, mas o contrato acompanha a implementação e a comparação entre linguagens perde rigor.
- **Formato de erro próprio:** mais simples agora, mas exige código específico em cada cliente.
- **Códigos como número, como o IBGE entrega:** mais simples hoje, mas cada consumidor teria de normalizar depois.
- **Schemathesis ou Pact no lugar da suíte própria:** não exercitam a fonte fora do ar nem a cópia vencida, que fazem parte do contrato.

## Consequências
- Mais trabalho no início de cada serviço. A fundação do E1 levou 20 das 47 tarefas, metade delas para a verificação. Em troca, consumidores simples e uma comparação justa entre linguagens.
- Cada serviço precisa de um "falso" controlável da sua fonte para a suíte de caixa-preta.
## Confirmação no E4 (Java, 2026-11-27)

As convenções funcionaram numa segunda linguagem **sem mudar o contrato**. A mesma suíte de caixa-preta passou contra as duas implementações (53 cenários), e, contra o IBGE real, os corpos das respostas foram idênticos nos 7 pedidos comparados. Os pontos que esta ADR mandava revisitar:

- **Ordenação sem acento:** o Java não tem `casefold`. `Normalizer` NFKD, remoção de `\p{Mn}` e `toLowerCase(Locale.ROOT)` deram a mesma ordem para os 645 municípios de SP e o mesmo resultado em 4 buscas. Um cenário de paridade na suíte passou a garantir isso.
- **Formato do `coletado_em`:** `Instant.toString()` omite os milissegundos quando são zero e quebraria o padrão `\.\d{3}Z`. É preciso um formatador explícito. O schema do contrato pegaria a diferença.
- **Nomes de métricas:** o Micrometer acrescenta o sufixo da unidade a um `Timer` (`_seconds`). Para manter `localidades_fonte_duracao_segundos`, use um `DistributionSummary` sem unidade. **Regra para os próximos serviços:** o contrato nomeia a métrica, e cada implementação escolhe o tipo que não altera o nome.
- **Erros:** o `ProblemDetail` do Spring implementa a RFC 9457 nativamente e cumpriu o formato sem código próprio. A propriedade extra `instance`, que o Spring pode incluir, é aceita porque o schema `Problema` não fecha propriedades adicionais.
- **Configuração:** o *relaxed binding* do Spring trata cada `_` da variável de ambiente como separador de nível. Variáveis como `LOCALIDADES_PRAZO_FONTE_S` precisam de mapeamento explícito (`${LOCALIDADES_PRAZO_FONTE_S:10}`) para manter os nomes comuns.
- **Ergonomia de cumprir um contrato escrito à mão:** nas duas linguagens o contrato passou praticamente sem retrabalho. O custo maior foi a infraestrutura de verificação, feita uma vez e reaproveitada. A comparação completa está em `specs/003-localidades-java/RESULTS.md`.

# ADR 0001: Convenções comuns de API entre serviços

- **Status:** aceita no E1 (2026-11-26); a confirmar no E4
- **Data:** 2026-11-14 (proposta) e 2026-11-26 (aceita)
- **Experimento de origem:** E1 — serviço de localidades (`specs/002-servico-localidades/`). A ser confirmada pelo E4 (Java).

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
- **Pontos a revisitar no E4:**
  - se o Java reproduz a regra de ordenação sem acento (NFKD + casefold) com o mesmo resultado;
  - se o formato do `coletado_em` sai idêntico;
  - se as bibliotecas Java de métricas permitem os mesmos nomes;
  - como fica a ergonomia de cumprir um contrato escrito à mão.

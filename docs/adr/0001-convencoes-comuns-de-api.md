# ADR 0001: Convenções comuns de API entre serviços

- **Status:** proposta (rascunho para discutir depois do E1)
- **Data:** 2026-11-14
- **Experimento de origem:** nenhum ainda; confirmar com o E1 e o E4

## Contexto
Os serviços do laboratório serão escritos em Python e Java e consumidos por clientes diferentes (outros serviços e, mais tarde, um agente de IA). Sem convenções comuns, cada serviço responderia de um jeito, e o consumidor teria de tratar cada caso.

## Decisão (proposta)
1. **Contrato:** cada serviço mantém um OpenAPI versionado em `contracts/`. O E1 (Python) e o E4 (Java) devem cumprir o mesmo contrato.
2. **Erros:** `application/problem+json` (RFC 9457), com `type`, `title`, `status`, `detail`. Falha de fonte externa devolve 502 com mensagem clara; fonte lenta devolve 504.
3. **Procedência:** toda resposta de dados inclui um bloco `meta` com `fonte`, `coletado_em` e, quando existir, `id_registro` e `vigencia`.
4. **Versionamento:** prefixo `/v1/` no caminho. Mudanças que quebram o contrato exigem nova versão.
5. **Paginação:** parâmetros `pagina` e `itens`, com limite máximo definido por serviço e documentado no contrato.
6. **Observabilidade:** `/health` e `/metrics` em todos os serviços; cabeçalho `X-Correlation-Id` propagado entre chamadas.
7. **Testes de contrato:** a suíte de cada serviço valida que as respostas reais correspondem ao OpenAPI.

## Alternativas consideradas
- Code-first em todos os serviços: mais rápido, mas o contrato acompanha a implementação e a comparação entre linguagens perde rigor.
- Formato de erro próprio: mais simples agora, mas exige código específico em cada cliente.

## Consequências
- Mais trabalho no início de cada serviço, em troca de consumidores simples.
- Pontos a revisitar depois do E1 e do E4: nomes dos campos de `meta`, política de paginação e o que fazer quando a fonte não fornece data de vigência.

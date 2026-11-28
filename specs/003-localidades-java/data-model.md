# Data Model: E4 — Serviço de localidades (IBGE), em Java

**Data**: 2026-11-27 | **Fonte da verdade**: [specs/002-servico-localidades/data-model.md](../002-servico-localidades/data-model.md)

As entidades, as regras de validação, a tabela `UFS_OFICIAIS`, a dobra, os estados da cópia guardada e a validação da resposta do IBGE são **os mesmos do E1** e não se repetem aqui. Este documento só registra como cada um vira tipo em Java.

## Entidades expostas

Todas são `record`s imutáveis no pacote `dominio`, sem anotações do Spring. Os nomes dos componentes são os nomes dos campos do contrato, em `snake_case` via `@JsonProperty` onde o nome difere.

| Entidade (E1) | Tipo Java | Componentes |
|---|---|---|
| Regiao | `record Regiao` | `String codigo, String sigla, String nome` |
| UF | `record Uf` | `String codigo, String sigla, String nome, Regiao regiao` |
| UFResumida | `record UfResumida` | `String codigo, String sigla, String nome` |
| RegiaoImediata / RegiaoIntermediaria | `record RegiaoImediata`, `record RegiaoIntermediaria` | `String codigo, String nome` |
| MunicipioResumido | `record MunicipioResumido` | `String codigo, String nome` |
| Municipio | `record Municipio` | `String codigo, String nome, UfResumida uf, RegiaoImediata regiaoImediata` (`regiao_imediata`), `RegiaoIntermediaria regiaoIntermediaria` (`regiao_intermediaria`) |
| Paginacao | `record Paginacao` | `int pagina, int itens, int total, int paginas` |
| Pagina | `record Pagina<T>` | `List<T> itens, Paginacao paginacao` |
| Meta | `record Meta` | `String fonte, String urlFonte` (`url_fonte`), `String urlDocumentacao` (`url_documentacao`), `String coletadoEm` (`coletado_em`), `boolean desatualizado` |

**Códigos são `String`**, como decidido no R7 do E1, nunca `int` nem `long`.

## Envelopes

`record Resposta<T>(T dados, Paginacao paginacao, Meta meta)` com `@JsonInclude(NON_NULL)`. Assim, `paginacao` só aparece nas listas paginadas, como no contrato.

## `coletado_em`

O instante é guardado como `Instant`, a partir do `Clock` injetado, e formatado com `DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").withZone(ZoneOffset.UTC)`. Não se usa `Instant.toString()`, que omite os milissegundos quando eles são zero e quebraria o padrão `\.\d{3}Z` do contrato.

## Erros de domínio

O pacote `erros` tem a classe base `ErroDominio extends RuntimeException`, com `tipo()`, `titulo()`, `status()` e `urn()`. As subclasses, com os mesmos tipos, títulos e status do E1:

| Classe | Tipo | Status |
|---|---|---|
| `EntradaInvalida` | `entrada-invalida` | 400 |
| `NaoEncontrado` | `nao-encontrado` | 404 |
| `FonteIndisponivel` | `fonte-indisponivel` | 502 |
| `FonteLenta` | `fonte-lenta` | 504 |
| `RespostaInesperadaDaFonte` | `resposta-inesperada-da-fonte` | 502 |
| `ErroInterno` | `erro-interno` | 500 |

`FonteIndisponivel`, `FonteLenta` e `RespostaInesperadaDaFonte` implementam a interface marcadora `ErroDeFonte`. É o equivalente ao `ERROS_DE_FONTE` do E1.

## Cópia guardada

- `record Guardada(Object dados, String urlFonte, Instant coletadoEm, long expiraEmNanos)`, em que a validade usa uma fonte monotônica injetável.
- `record Entrada(Object dados, String urlFonte, Instant coletadoEm, boolean desatualizado, String resultado)`, em que `resultado` é `acerto`, `falta` ou `desatualizado`.
- Os estados e as transições são os do data-model do E1. A consulta em andamento por chave é um `CompletableFuture<Entrada>`, compartilhado inclusive na falha (R5).

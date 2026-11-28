# Data Model: E7 — Serviço de localidades (IBGE), em Go

**Data**: 2026-11-27 | **Fonte da verdade**: [specs/002-servico-localidades/data-model.md](../002-servico-localidades/data-model.md)

As entidades, as regras de validação, a tabela `UFS_OFICIAIS`, a dobra, os estados da cópia guardada e a validação da resposta do IBGE são **os mesmos do E1** e não se repetem aqui. Este documento só registra como cada um vira tipo em Go.

## Entidades expostas

Todas são *structs* no pacote `internal/dominio`, sem importar `net/http`. Os nomes dos campos JSON vêm das *tags* `json:"..."`, em `snake_case` como no contrato.

| Entidade (E1) | Tipo Go | Campos (tag JSON) |
|---|---|---|
| Regiao | `type Regiao struct` | `Codigo` (`codigo`), `Sigla` (`sigla`), `Nome` (`nome`) |
| UF | `type UF struct` | `Codigo`, `Sigla`, `Nome`, `Regiao Regiao` (`regiao`) |
| UFResumida | `type UFResumida struct` | `Codigo`, `Sigla`, `Nome` |
| RegiaoImediata / RegiaoIntermediaria | `type RegiaoImediata struct`, `type RegiaoIntermediaria struct` | `Codigo`, `Nome` |
| MunicipioResumido | `type MunicipioResumido struct` | `Codigo`, `Nome` |
| Municipio | `type Municipio struct` | `Codigo`, `Nome`, `UF UFResumida` (`uf`), `RegiaoImediata` (`regiao_imediata`), `RegiaoIntermediaria` (`regiao_intermediaria`) |
| Paginacao | `type Paginacao struct` | `Pagina int64` (`pagina`), `Itens int` (`itens`), `Total int` (`total`), `Paginas int` (`paginas`) |
| Meta | `type Meta struct` | `Fonte` (`fonte`), `URLFonte` (`url_fonte`), `URLDocumentacao` (`url_documentacao`), `ColetadoEm` (`coletado_em`), `Desatualizado bool` (`desatualizado`) |

**Códigos são `string`**, como decidido no R7 do E1, nunca `int`.

**`Pagina` é `int64`**, porque a lição da T045 do E4 mostrou que `pagina=99999999999` estoura um inteiro de 32 bits. Uma página com só dígitos que não cabe em `int64` é tratada como além do fim (research R4).

## Envelope

```go
type Resposta[T any] struct {
    Dados     T          `json:"dados"`
    Paginacao *Paginacao `json:"paginacao,omitempty"`
    Meta      Meta       `json:"meta"`
}
```

O ponteiro com `omitempty` faz o `paginacao` aparecer só nas listas paginadas, como no contrato.

## `coletado_em`

O instante é um `time.Time` em UTC, vindo da função `agora()` injetada, formatado com o *layout* `2006-01-02T15:04:05.000Z07:00`. Em UTC, o Go escreve `Z` no lugar do fuso. Não se usa `time.RFC3339Nano`, que omite os zeros à direita e quebraria o padrão `\.\d{3}Z` do contrato. É a mesma armadilha do `Instant.toString()` no E4.

## Erros de domínio

O pacote `internal/erros` tem `type ErroDominio struct { Tipo, Titulo, Detalhe string; Status int }`, que implementa `error`, e um construtor por tipo, com os mesmos tipos, títulos e status do E1:

| Construtor | Tipo | Status |
|---|---|---|
| `EntradaInvalida(detalhe)` | `entrada-invalida` | 400 |
| `NaoEncontrado(detalhe)` | `nao-encontrado` | 404 |
| `FonteIndisponivel(detalhe)` | `fonte-indisponivel` | 502 |
| `FonteLenta(detalhe)` | `fonte-lenta` | 504 |
| `RespostaInesperadaDaFonte(detalhe)` | `resposta-inesperada-da-fonte` | 502 |
| `ErroInterno()` | `erro-interno` | 500 |

`ErroDominio.DeFonte()` diz se o erro é um dos três de fonte. É o equivalente ao `ERROS_DE_FONTE` do E1 e à interface `ErroDeFonte` do E4. O reconhecimento usa `errors.As`.

## Cópia guardada

- `type guardada struct { dados any; urlFonte string; coletadoEm time.Time; expiraEm time.Duration }`, em que `expiraEm` é medido no relógio monotônico injetado.
- `type Entrada struct { Dados any; URLFonte string; ColetadoEm time.Time; Desatualizado bool; Resultado string }`, em que `Resultado` é `acerto`, `falta` ou `desatualizado`.
- Os estados e as transições são os do data-model do E1. A consulta em andamento por chave fica no `singleflight.Group`, compartilhada inclusive na falha (research R7).

## Configuração

`type Configuracao struct { IBGEURL string; PrazoFonte, Validade time.Duration; ItensMax int; Host string; Porta int }`, lida de `LOCALIDADES_*` e validada na partida (research R11). Prazo e validade são guardados já como `time.Duration`, depois de conferidos entre 1 ms e 10⁹ s.

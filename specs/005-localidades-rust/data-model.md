# Data Model: E8 — Serviço de localidades (IBGE), em Rust

**Data**: 2026-11-28 | **Fonte da verdade**: [specs/002-servico-localidades/data-model.md](../002-servico-localidades/data-model.md)

As entidades, as regras de validação, a tabela `UFS_OFICIAIS`, a dobra, os estados da cópia guardada e a validação da resposta do IBGE são **os mesmos do E1** e não se repetem aqui. Este documento só registra como cada um vira tipo em Rust.

## Entidades expostas

Todas são `struct`s no módulo `dominio`, com `#[derive(Serialize, Clone)]`, sem depender do axum. Os nomes dos campos JSON vêm dos nomes dos campos, em `snake_case` como no contrato.

| Entidade (E1) | Tipo Rust | Campos |
|---|---|---|
| Regiao | `struct Regiao` | `codigo: String, sigla: String, nome: String` |
| UF | `struct Uf` | `codigo, sigla, nome: String, regiao: Regiao` |
| UFResumida | `struct UfResumida` | `codigo, sigla, nome: String` |
| RegiaoImediata / RegiaoIntermediaria | `struct RegiaoImediata`, `struct RegiaoIntermediaria` | `codigo, nome: String` |
| MunicipioResumido | `struct MunicipioResumido` | `codigo, nome: String` |
| Municipio | `struct Municipio` | `codigo, nome: String, uf: UfResumida, regiao_imediata: RegiaoImediata, regiao_intermediaria: RegiaoIntermediaria` |
| Paginacao | `struct Paginacao` | `pagina: i64, itens: u32, total: usize, paginas: usize` |
| Meta | `struct Meta` | `fonte, url_fonte, url_documentacao, coletado_em: String, desatualizado: bool` |

**Códigos são `String`**, como decidido no R7 do E1.

**`pagina` é `i64`**, pela lição da T045 do E4. Uma página com só dígitos que não cabe em `i64` é tratada como além do fim (research R4).

## Envelope

```rust
#[derive(Serialize)]
struct Resposta<T: Serialize> {
    dados: T,
    #[serde(skip_serializing_if = "Option::is_none")]
    paginacao: Option<Paginacao>,
    meta: Meta,
}
```

O `paginacao` aparece só nas listas paginadas, como no contrato, e os campos saem na ordem da *struct*: `dados`, `paginacao`, `meta`.

## `coletado_em`

O instante é um `time::OffsetDateTime` em UTC, vindo da função de relógio injetada, formatado com a descrição `[year]-[month]-[day]T[hour]:[minute]:[second].[subsecond digits:3]Z`. Os milissegundos saem sempre, inclusive `.000`, que é a armadilha que o E4 e o E7 tiveram de contornar.

## Erros de domínio

O módulo `erros` tem `struct ErroDominio { tipo: &'static str, titulo: &'static str, status: StatusCode, detalhe: String }`, que implementa `IntoResponse` e `std::error::Error`, e um construtor por tipo, com os tipos, títulos e status do E1:

| Construtor | Tipo | Status |
|---|---|---|
| `ErroDominio::entrada_invalida(detalhe)` | `entrada-invalida` | 400 |
| `ErroDominio::nao_encontrado(detalhe)` | `nao-encontrado` | 404 |
| `ErroDominio::fonte_indisponivel(detalhe)` | `fonte-indisponivel` | 502 |
| `ErroDominio::fonte_lenta(detalhe)` | `fonte-lenta` | 504 |
| `ErroDominio::resposta_inesperada(detalhe)` | `resposta-inesperada-da-fonte` | 502 |
| `ErroDominio::interno()` | `erro-interno` | 500 |

`ErroDominio::de_fonte()` diz se o erro é um dos três de fonte, o equivalente ao `ERROS_DE_FONTE` do E1. O tipo é `Clone`, para o `Shared` da consulta compartilhada entregar o mesmo erro a todos.

## Cópia guardada

- `struct Guardada { dados: Dados, url_fonte: String, coletado_em: OffsetDateTime, expira_em: Duration }`, em que `expira_em` é medido no relógio monotônico injetado.
- `struct Entrada { dados: Dados, url_fonte: String, coletado_em: OffsetDateTime, desatualizado: bool, resultado: &'static str }`, em que `resultado` é `acerto`, `falta` ou `desatualizado`.
- `enum Dados { Ufs(Arc<Vec<Uf>>), Municipios(Arc<Vec<MunicipioResumido>>), Municipio(Arc<Municipio>) }`, para a cópia guardar os três recursos sem cópias profundas.

## Configuração

`struct Configuracao { ibge_url: String, prazo_fonte: Duration, validade: Duration, itens_max: u32, host: String, porta: u16 }`, lida de `LOCALIDADES_*` e validada na partida (research R11).

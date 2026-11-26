# Data Model: E1 — Serviço de localidades (IBGE)

**Data**: 2026-11-26 | **Spec**: [spec.md](spec.md) | **Contrato**: [contracts/localidades/openapi.yaml](../../contracts/localidades/openapi.yaml)

Entidades expostas pelo serviço e a origem de cada campo na resposta do IBGE (R1). Todos os códigos são texto de tamanho fixo (R7), e todos os nomes vêm exatamente como o IBGE os publica (FR-006).

## Entidades expostas

### Regiao (grande região)

| Campo | Tipo | Regra | Origem no IBGE |
|---|---|---|---|
| `codigo` | texto | `^\d$` | `regiao.id` |
| `sigla` | texto | `^[A-Z]{1,2}$` (`N`, `NE`, `SE`, `S`, `CO`) | `regiao.sigla` |
| `nome` | texto | não vazio | `regiao.nome` |

### UF (unidade federativa)

| Campo | Tipo | Regra | Origem no IBGE |
|---|---|---|---|
| `codigo` | texto | `^\d{2}$` | `id` |
| `sigla` | texto | `^[A-Z]{2}$` | `sigla` |
| `nome` | texto | não vazio | `nome` |
| `regiao` | Regiao | obrigatório | `regiao` |

Fonte: `GET {IBGE}/estados`. Há 27 UFs, ordenadas pelo nome dobrado (R8).

### UFResumida (dentro de Municipio)

| Campo | Tipo | Regra | Origem no IBGE |
|---|---|---|---|
| `codigo` | texto | `^\d{2}$` | `regiao-imediata.regiao-intermediaria.UF.id` |
| `sigla` | texto | `^[A-Z]{2}$` | `….UF.sigla` |
| `nome` | texto | não vazio | `….UF.nome` |

### RegiaoIntermediaria e RegiaoImediata

| Entidade | `codigo` | `nome` | Origem no IBGE |
|---|---|---|---|
| RegiaoIntermediaria | `^\d{4}$` | não vazio | `regiao-imediata.regiao-intermediaria` |
| RegiaoImediata | `^\d{6}$` | não vazio | `regiao-imediata` |

### MunicipioResumido (itens de lista)

| Campo | Tipo | Regra | Origem no IBGE |
|---|---|---|---|
| `codigo` | texto | `^\d{7}$` | `id` |
| `nome` | texto | não vazio | `nome` |

Fonte: `GET {IBGE}/estados/{codigo_uf}/municipios`.

### Municipio (consulta por código)

| Campo | Tipo | Regra | Origem no IBGE |
|---|---|---|---|
| `codigo` | texto | `^\d{7}$` | `id` |
| `nome` | texto | não vazio | `nome` |
| `uf` | UFResumida | obrigatório | `regiao-imediata.regiao-intermediaria.UF` |
| `regiao_imediata` | RegiaoImediata | obrigatório | `regiao-imediata` |
| `regiao_intermediaria` | RegiaoIntermediaria | obrigatório | `regiao-imediata.regiao-intermediaria` |

Fonte: `GET {IBGE}/municipios/{codigo}`. A `microrregiao` do IBGE é ignorada e pode vir `null` (R1: `5101837`).

### Meta (procedência)

| Campo | Tipo | Regra |
|---|---|---|
| `fonte` | texto | fixo: `IBGE — API de localidades` |
| `url_fonte` | texto (URI) | URL do IBGE consultada para obter o dado |
| `url_documentacao` | texto (URI) | fixo: `https://servicodados.ibge.gov.br/api/docs/localidades` |
| `coletado_em` | data e hora | ISO 8601, UTC, milissegundos, sufixo `Z`; momento da consulta original ao IBGE |
| `desatualizado` | booleano | `true` só quando a cópia vencida foi servida por falha da fonte |

### Paginacao

| Campo | Tipo | Regra |
|---|---|---|
| `pagina` | inteiro | ≥ 1, a pedida |
| `itens` | inteiro | 1 a `ITENS_MAX` (padrão 500), o pedido |
| `total` | inteiro | ≥ 0; total depois do filtro por nome |
| `paginas` | inteiro | `ceil(total / itens)`; 0 quando `total` = 0 |

### Problema (erro, RFC 9457)

| Campo | Tipo | Regra |
|---|---|---|
| `type` | texto (URN) | um dos 6 tipos de R11 |
| `title` | texto | fixo por tipo |
| `status` | inteiro | igual ao status HTTP |
| `detail` | texto | explicação para o consumidor, sem detalhes internos |
| `correlacao_id` | texto | o mesmo do cabeçalho `X-Correlation-Id` |

## Envelopes de resposta

| Rota | Corpo de sucesso |
|---|---|
| `GET /v1/ufs` | `{dados: [UF], meta}` |
| `GET /v1/ufs/{uf}` | `{dados: UF, meta}` |
| `GET /v1/ufs/{uf}/municipios` | `{dados: [MunicipioResumido], paginacao, meta}` |
| `GET /v1/municipios/{codigo}` | `{dados: Municipio, meta}` |

As respostas de `/v1/ufs/{uf}` e de `/v1/ufs/{uf}/municipios` dependem também da lista de UFs (R1). O `meta` descreve o recurso principal: a lista de UFs, na primeira; a lista de municípios da UF, na segunda.

## Validação de entrada (antes de consultar o IBGE, FR-012)

| Parâmetro | Regra | Erro |
|---|---|---|
| `{uf}` | aparado nas pontas; `^[A-Za-z]{2}$` (sigla, comparada em maiúsculas) ou `^\d{2}$` (código) | 400 `entrada-invalida` |
| `{uf}` bem formado e fora da lista oficial | — | 404 `nao-encontrado` |
| `{codigo}` | `^\d{7}$` | 400 `entrada-invalida` |
| `pagina` | inteiro ≥ 1 | 400 `entrada-invalida` |
| `itens` | inteiro de 1 a `ITENS_MAX` | 400, com o limite no `detail` |
| `nome` | aparado; de 2 a 60 caracteres | 400, com o mínimo no `detail` |

## Regras derivadas

- **Dobra** (R8): `dobrar(s) = casefold(remover_marcas(NFKD(s)))`, em que `remover_marcas` tira os caracteres da categoria Unicode `Mn`.
- **Ordenação de municípios e UFs**: pela chave `(dobrar(nome), codigo)`.
- **Busca**: um município combina quando `dobrar(nome_buscado.strip())` está contido em `dobrar(municipio.nome)`.
- **Paginação**: aplicada depois do filtro e da ordenação. Os itens vão de `(pagina-1)*itens` a `pagina*itens`.

## Estados de uma entrada da cópia guardada (R5)

```text
            consulta ok                       expira_em passou
 AUSENTE ───────────────▶ VÁLIDA ───────────────────────────────▶ VENCIDA
    │                       ▲                                         │
    │ consulta falha         │ consulta ok (renova coletado_em)        │ consulta falha
    ▼                       └──────────────────────────────────────────┤
 erro de fonte                                                         ▼
                                                   serve a cópia com desatualizado=true
                                                   (continua VENCIDA)
```

- **Chave**: o recurso do IBGE (`estados`, `estados/{codigo}/municipios` ou `municipios/{codigo}`).
- **Valor**: os dados normalizados, `url_fonte`, `coletado_em` e `expira_em = coletado_em + validade`.
- **"Não encontrado" e erros**: nunca entram na cópia guardada.
- **Concorrência**: uma trava por chave. Quem chega durante uma consulta em andamento espera e usa o resultado dela (R5).

## Validação da resposta do IBGE (normalização)

| Recurso | Forma esperada | Fora disso |
|---|---|---|
| `estados` | lista não vazia de objetos com `id`, `sigla`, `nome` e `regiao{id, sigla, nome}` | `resposta-inesperada-da-fonte` |
| `estados/{c}/municipios` | lista não vazia de objetos com `id` (7 dígitos) e `nome` | `[]` → `resposta-inesperada-da-fonte` |
| `municipios/{c}` | objeto com `id`, `nome` e `regiao-imediata{id, nome, regiao-intermediaria{id, nome, UF{id, sigla, nome}}}`, ou uma lista de exatamente 1 objeto assim | `[]` → `nao-encontrado`; outro formato → `resposta-inesperada-da-fonte` |

Campos extras do IBGE são ignorados, e campos obrigatórios ausentes tornam a resposta inesperada.

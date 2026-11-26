# Data Model: E0 — Inventário e conectividade das fontes

**Spec**: [spec.md](spec.md) | **Pesquisa**: [research.md](research.md)

Todas as entidades são imutáveis (dataclasses `frozen`). O relatório JSON é a serialização direta de `Execucao` e segue o contrato [contracts/relatorio.schema.json](contracts/relatorio.schema.json).

## Fonte (entrada do catálogo)

Lida de `discovery/sources.json` (`schema_version: 1`). A ferramenta nunca escreve no catálogo (FR-003).

| Campo (catálogo) | Atributo | Tipo | Obrigatório | Regra |
|---|---|---|---|---|
| `id` | `id` | texto | sim | único no catálogo; `[a-z0-9-]+` |
| `name` | `nome` | texto | sim | não vazio |
| `domain` | `dominio` | texto | sim | não vazio |
| `docs_url` | `url_documentacao` | URL ou nulo | sim (pode ser `null`) | se presente, `http(s)://`; nulo = documentação oficial ainda não localizada (ex.: `datajud`), exibido como tal no relatório |
| `probe_url` | `url_teste` | URL ou nulo | não | se presente, `http(s)://` |
| `data_type` | `tipos_dado` | lista de texto | sim | não vazia |
| `access_hypothesis` | `hipotese_acesso` | texto | sim | exibida, não comparada (R12) |
| `auth` | `auth_esperada` | texto | sim | origem da hipótese de autenticação (R12) |
| `verification` | `verificacao` | enum | sim | `confirmado` \| `parcial` \| `nao_verificado` |
| `round` | `rodada` | inteiro | sim | ≥ 1 |
| `notes` | `notas` | texto | não | |

**Validação (FR-002)**: o catálogo inteiro é validado antes de qualquer consulta. Cada problema é reportado como `fonte[i] (id): campo X ...`. Um único erro aborta a execução com código 1, sem gerar relatório. Campos desconhecidos são ignorados.

**Derivado**: `hipotese_auth` = `nao_exige` se `auth_esperada` começa com "nenhuma" (sem diferenciar maiúsculas); senão `exige`.

## ResultadoSondagem

Um por fonte selecionada pelo filtro. Toda fonte do filtro gera exatamente um resultado (SC-002).

| Atributo | Tipo | Quando | Descrição |
|---|---|---|---|
| `fonte_id`, `nome`, `dominio`, `url_documentacao`, `rodada` | copiados | sempre | identificação (princípio II) |
| `hipotese_acesso`, `auth_esperada` | copiados | sempre | |
| `verificacao_catalogo` | enum | sempre | grau no catálogo |
| `verificacao_sugerida` | enum | sempre | regra em R11 |
| `justificativa_verificacao` | texto | sempre | por que manteve ou mudou |
| `situacao` | enum | sempre | `respondeu` \| `falhou` \| `sem_teste` \| `nao_executada` |
| `causa` | enum ou nulo | `falhou` | ver R3 |
| `detalhe_causa` | texto ou nulo | `falhou` | mensagem curta, sem corpo da resposta |
| `url_teste` | URL ou nulo | sempre | |
| `url_final` | URL ou nulo | houve resposta | após redirecionamentos |
| `redirecionamentos` | lista de `{status, url}` | houve resposta | vazia se não houve |
| `status_http` | inteiro ou nulo | houve resposta | status final |
| `latencia_ms` | número ou nulo | houve consulta | do envio até o fim da leitura da amostra |
| `coletado_em` | data-hora UTC ou nulo | houve consulta | início da consulta |
| `formato_declarado` | texto ou nulo | houve resposta | `Content-Type` sem parâmetros |
| `formato_detectado` | enum ou nulo | houve corpo | `json` \| `csv` \| `xml` \| `html` \| `texto` \| `vazio` \| `outro` |
| `formato_divergente` | booleano | houve resposta | R4 |
| `tamanho_bytes` | inteiro ou nulo | houve resposta | bytes lidos |
| `tamanho_declarado_bytes` | inteiro ou nulo | houve resposta | `Content-Length`, se veio |
| `truncada` | booleano | houve resposta | teto de 1 MiB atingido |
| `auth_observada` | enum | sempre | `exige` \| `nao_exige` \| `indeterminado` |
| `indicio_autenticacao` | texto ou nulo | `exige` | ex.: "status 401", "redirecionado para sso.acesso.gov.br" |
| `retry_after` | texto ou nulo | 429 | valor bruto do cabeçalho |
| `amostra` | `EstruturaAmostra` ou nulo | `respondeu` com formato estruturado | |
| `divergencias` | lista de `Divergencia` | sempre | vazia se não houver |

**Transições de `situacao`**:

```text
(fonte selecionada)
   ├─ sem url_teste ───────────────► sem_teste
   ├─ interrompida antes da vez ───► nao_executada
   └─ consulta
        ├─ exceção de rede ────────► falhou (tempo_esgotado | indisponivel | erro_tls | erro_requisicao)
        ├─ status ≠ 2xx ───────────► falhou (exige_autenticacao | acesso_negado | limite_requisicoes | erro_fonte | erro_requisicao)
        ├─ 2xx, conteúdo ilegível ─► falhou (resposta_invalida)
        └─ 2xx, legível ───────────► respondeu
```

Observação: um 2xx que termina em página de login (R2) vira `falhou` / `exige_autenticacao`.

**Invariantes**:
- `situacao = falhou` ⇔ `causa` não nula.
- `situacao ∈ {sem_teste, nao_executada}` ⇒ nenhum campo de consulta preenchido e `auth_observada = indeterminado`.
- Nenhum atributo contém valores do corpo da resposta (FR-015).

## EstruturaAmostra

| Atributo | Tipo | Descrição |
|---|---|---|
| `registros_inspecionados` | inteiro | ≤ 5 |
| `caminho_registros` | texto ou nulo | onde está a lista de registros (ex.: `dados`), nulo se for a raiz |
| `campos` | lista de `CampoAmostra` | ordenada por caminho |
| `vazia` | booleano | lista sem registros ("sem registros na amostra") |
| `indisponivel_motivo` | texto ou nulo | ex.: "resposta truncada" |

## CampoAmostra

| Atributo | Tipo | Descrição |
|---|---|---|
| `caminho` | texto | notação de pontos; `[]` marca lista (`itens[].id`) |
| `tipos` | lista de enum | união de `texto`, `inteiro`, `decimal`, `booleano`, `nulo`, `data`, `objeto`, `lista` |

Não há atributo para valor, exemplo ou enumeração: é a garantia estrutural de FR-015.

## Divergencia

| Atributo | Tipo | Descrição |
|---|---|---|
| `aspecto` | enum | `autenticacao` \| `disponibilidade` \| `formato` |
| `hipotese` | texto | ex.: "nao_exige" |
| `observado` | texto | ex.: "exige (status 401)" |

`formato` só é gerado quando `formato_divergente` é verdadeiro (declarado × detectado).

## Execucao (raiz do relatório)

| Atributo | Tipo | Descrição |
|---|---|---|
| `versao_relatorio` | inteiro | `1` |
| `ferramenta` | texto | nome e versão |
| `catalogo` | `{caminho, schema_version}` | procedência do catálogo |
| `iniciada_em`, `finalizada_em` | data-hora UTC | |
| `interrompida` | booleano | |
| `filtros` | `{rodadas: [int], fontes: [texto]}` | vazios = todas |
| `configuracao` | `{intervalo_s, tempo_limite_s, teto_bytes, max_redirecionamentos}` | |
| `aviso` | texto | FR-020: sondagem ≠ confirmação de licença, limites e termos |
| `resumo` | `Resumo` | |
| `resultados` | lista de `ResultadoSondagem` | ordem do catálogo |

## Resumo

| Atributo | Tipo |
|---|---|
| `total` | inteiro |
| `responderam` | inteiro |
| `falharam` | inteiro |
| `falhas_por_causa` | mapa `causa → inteiro` |
| `sem_teste` | inteiro |
| `nao_executadas` | inteiro |
| `com_divergencia` | inteiro |

Invariante: `total = responderam + falharam + sem_teste + nao_executadas`.

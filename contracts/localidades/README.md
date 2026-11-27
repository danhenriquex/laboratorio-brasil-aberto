# Contrato: serviço de localidades (v1)

Contrato compartilhado entre o **E1** (Python, `experiments/python/localidades/`) e o **E4** (Java). As duas implementações cumprem o mesmo [`openapi.yaml`](openapi.yaml) e passam pela mesma suíte de verificação. Elas compartilham o contrato, nunca o código (Constituição VI).

- **Especificação:** [specs/002-servico-localidades/spec.md](../../specs/002-servico-localidades/spec.md)
- **Decisões:** [research.md](../../specs/002-servico-localidades/research.md), em especial R3 a R14
- **Modelo de dados:** [data-model.md](../../specs/002-servico-localidades/data-model.md)

## Rotas

| Rota | O que devolve |
|---|---|
| `GET /v1/ufs` | as 27 UFs |
| `GET /v1/ufs/{uf}` | uma UF, por sigla ou código |
| `GET /v1/ufs/{uf}/municipios?nome=&pagina=&itens=` | municípios da UF, paginados |
| `GET /v1/municipios/{codigo}` | um município pelo código de 7 dígitos |
| `GET /health` | saúde, sem consultar o IBGE |
| `GET /metrics` | métricas no formato do Prometheus |

## Configuração comum

Toda implementação lê as mesmas variáveis de ambiente (R14):

| Variável | Padrão | Uso |
|---|---|---|
| `LOCALIDADES_HOST` | `127.0.0.1` | endereço de escuta |
| `LOCALIDADES_PORTA` | `8000` | porta |
| `LOCALIDADES_IBGE_URL` | `https://servicodados.ibge.gov.br/api/v1/localidades` | base da fonte |
| `LOCALIDADES_PRAZO_FONTE_S` | `10` | prazo total por consulta ao IBGE |
| `LOCALIDADES_VALIDADE_S` | `86400` | validade da cópia guardada |
| `LOCALIDADES_ITENS_MAX` | `500` | tamanho máximo de página (mudar sai do contrato v1) |

## Verificação de caixa-preta

[`verificacao/`](verificacao/) é um projeto `uv` com:

- um **IBGE falso**, que serve as [fixtures gravadas](fixtures-ibge/) e aceita os modos `normal`, `fora`, `lento` e `invalido`;
- os **cenários das histórias US1 a US5**, que validam cada resposta contra o `openapi.yaml`.

O script `verificar.sh` recebe o comando que sobe o serviço, aplica o perfil de verificação (IBGE falso, prazo de 1 s e validade de 2 s), roda a suíte e encerra tudo:

```bash
# E1 (Python)
contracts/localidades/verificacao/verificar.sh "uv run --project experiments/python/localidades localidades"

# E4 (Java), quando existir
contracts/localidades/verificacao/verificar.sh "java -jar experiments/java/localidades/target/localidades.jar"
```

## Mudanças

Mudança compatível (campo novo opcional, rota nova) sobe a versão menor do `info.version`. Mudança incompatível exige `/v2` (FR-020).

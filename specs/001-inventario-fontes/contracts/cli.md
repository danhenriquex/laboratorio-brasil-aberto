# Contrato da linha de comando: `inventario`

Executável instalado pelo projeto em `experiments/python/discovery/`. A partir da raiz do repositório:

```bash
uv run --project experiments/python/discovery inventario [opções]
```

## Opções

| Opção | Padrão | Descrição |
|---|---|---|
| `--catalogo CAMINHO` | `discovery/sources.json` | catálogo de fontes (relativo ao diretório atual) |
| `--saida DIRETORIO` | `discovery/reports` | onde gravar os relatórios; criado se não existir |
| `--rodada N` | todas | limita a uma rodada; pode repetir (`--rodada 1 --rodada 2`) |
| `--fonte ID` | todas | limita a uma fonte pelo `id`; pode repetir; combina com `--rodada` por interseção |
| `--intervalo SEGUNDOS` | `2` | intervalo mínimo entre consultas; mínimo aceito `1` |
| `--tempo-limite SEGUNDOS` | `15` | tempo limite de cada consulta; entre `1` e `60` |
| `--versao` | | mostra a versão e sai |

Não há opção para enviar credenciais, cabeçalhos extras, mais de uma tentativa ou paralelismo (FR-004, FR-007).

## Saída

**Arquivos** (FR-017), com timestamp UTC do início da execução:

- `<saida>/inventario-AAAAMMDDTHHMMSSZ.json`: segue [relatorio.schema.json](relatorio.schema.json)
- `<saida>/inventario-AAAAMMDDTHHMMSSZ.html`: mesmo conteúdo, legível, autocontido

Se o arquivo já existir (duas execuções no mesmo segundo), um sufixo `-2`, `-3`... é acrescentado. Nada é sobrescrito.

**Terminal** (FR-021), no `stdout`, uma linha por fonte durante a execução e um resumo ao final:

```text
[1/4] ibge-localidades ........ respondeu  200  json  312 ms
[2/4] bcb-sgs ................. respondeu  200  json  845 ms
[3/4] bcb-ifdata .............. sem teste automatizado
[4/4] camara-dados-abertos .... respondeu  200  json  1203 ms

4 fontes: 3 responderam, 0 falharam, 1 sem teste, 0 com divergência
Relatórios:
  discovery/reports/inventario-20261124T130512Z.json
  discovery/reports/inventario-20261124T130512Z.html
```

Erros de uso e de catálogo vão para o `stderr`.

## Códigos de saída

| Código | Quando |
|---|---|
| `0` | execução concluída e relatórios gravados, **mesmo que fontes tenham falhado** |
| `1` | catálogo ausente, ilegível ou inválido; nada é consultado e nenhum relatório é gerado |
| `2` | uso incorreto (opção inválida, `--fonte` inexistente no catálogo, filtro sem nenhuma fonte) |
| `130` | interrompida pelo usuário; relatórios parciais gravados com `interrompida: true` |

# Quickstart: E8 — Serviço de localidades (IBGE), em Rust

Guia de validação ponta a ponta. As rotas e os formatos estão em [contracts/localidades/openapi.yaml](../../contracts/localidades/openapi.yaml), e o mapeamento para Rust, em [data-model.md](data-model.md). Todos os comandos partem da raiz do repositório.

## Pré-requisitos

- **Rust 1.100:** pelo `rustup`, o instalador oficial (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`). Confira com `rustc --version`; deve aparecer `rustc 1.100.x`.
- **Suíte de caixa-preta:** usa o `uv`, como nas outras (`uv sync --project contracts/localidades/verificacao`).

```bash
(cd experiments/rust/localidades && cargo build --release)
```

A primeira execução baixa as crates para `~/.cargo/registry` e compila tudo; as seguintes reaproveitam o `target/`.

## 1. Testes da implementação (sem rede externa)

```bash
(cd experiments/rust/localidades && cargo clippy --all-targets -- -D warnings && cargo test)
```

**Esperado**: todos passam. O IBGE é simulado por um servidor local dentro dos testes.

## 2. Verificação de caixa-preta (o mesmo critério das outras)

```bash
contracts/localidades/verificacao/verificar.sh "experiments/rust/localidades/target/release/localidades"
```

**Esperado**: os 82 cenários passam, os mesmos do E1, do E4 e do E7.

## 3. Sem rede externa (SC-004)

```bash
P='(version 1)(allow default)(deny network*)(allow network* (local ip "localhost:*"))(allow network* (remote ip "localhost:*"))'
sandbox-exec -p "$P" sh -c 'cd experiments/rust/localidades && cargo test --offline'
UV_OFFLINE=1 sandbox-exec -p "$P" contracts/localidades/verificacao/verificar.sh "experiments/rust/localidades/target/release/localidades"
```

**Esperado**: as duas execuções passam, e um `curl` ao IBGE dentro do mesmo sandbox falha.

## 4. Configuração inválida (FR-003)

```bash
LOCALIDADES_PRAZO_FONTE_S=inf experiments/rust/localidades/target/release/localidades; echo "saída=$?"
```

**Esperado**: o serviço não sobe, mostra `configuração inválida: LOCALIDADES_PRAZO_FONTE_S …` e sai com código 2. O mesmo vale para `NaN`, `0`, `-1`, `0.0001`, `abc` e URL que não começa com `http`.

## 5. Execução real contra o IBGE (manual)

```bash
experiments/rust/localidades/target/release/localidades   # 127.0.0.1:8000
```

As respostas devem ser equivalentes às das outras três. Só o `coletado_em` e o `X-Correlation-Id` mudam.

## 6. Comparação entre as quatro (US6)

Siga o método do [research.md, R15](research.md): mesma máquina e mesmo dia, com as outras três medidas de novo junto, caches populados e mediana de 3 execuções. O build do E8 é medido com o `target/` frio e quente. Preencha a tabela do `RESULTS.md` com as 9 medidas para as quatro implementações, e a tabela das 8 lições (FR-009).

# E8 — Serviço de localidades (IBGE), em Rust

**Pergunta do experimento:** como é construir e operar o mesmo serviço de localidades em Rust, do setup aos testes e ao cumprimento do mesmo contrato, comparado ao E1 (Python), ao E4 (Java) e ao E7 (Go)?

É o mesmo serviço do E1, do E4 e do E7, com o mesmo contrato: [`contracts/localidades/openapi.yaml`](../../../contracts/localidades/openapi.yaml). Foi feito com Rust 1.100, `axum` sobre `tokio`, `reqwest` para o IBGE, `serde_json` e o cliente `prometheus`.

## Pré-requisitos

- Rust 1.100 pelo `rustup`: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`. Confira com `rustc --version`.
- Para a suíte de caixa-preta, o `uv`, como nas outras implementações.

## Como rodar

Todos os comandos partem da raiz do repositório.

```bash
# testes da implementação (sem rede externa; o IBGE é simulado por um servidor local dentro dos testes)
(cd experiments/rust/localidades && cargo clippy --all-targets -- -D warnings && cargo test)

# gerar o binário otimizado e verificar o contrato com a mesma suíte de caixa-preta das outras
(cd experiments/rust/localidades && cargo build --release)
contracts/localidades/verificacao/verificar.sh "experiments/rust/localidades/target/release/localidades"

# execução real contra o IBGE, em 127.0.0.1:8000
experiments/rust/localidades/target/release/localidades
```

As variáveis `LOCALIDADES_*` são as mesmas das outras implementações ([contracts/localidades/README.md](../../../contracts/localidades/README.md)). O roteiro completo está em [`specs/005-localidades-rust/quickstart.md`](../../../specs/005-localidades-rust/quickstart.md).

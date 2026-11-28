#!/usr/bin/env bash
# Comparação E1 (Python) × E4 (Java) × E7 (Go) × E8 (Rust): as 9 medidas do FR-006, pelo método do R13 do E4 e do R15 do E7 e do E8.
# Uso, a partir da raiz do repositório:  specs/005-localidades-rust/medicao/medir.sh [execuções=3]
# Imprime uma tabela em Markdown. Usa o IBGE falso da suíte de verificação: nenhuma chamada ao IBGE real.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
export PATH="$HOME/.cargo/bin:$PATH"  # o rustup instala o cargo e o rustc aqui
exec python3 -I specs/005-localidades-rust/medicao/medir.py "${1:-3}"

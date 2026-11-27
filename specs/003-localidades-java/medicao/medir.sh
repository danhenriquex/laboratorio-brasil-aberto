#!/usr/bin/env bash
# Comparação E1 (Python) × E4 (Java): as 9 medidas do FR-006, pelo método do R13 (research.md).
# Uso, a partir da raiz do repositório:  specs/003-localidades-java/medicao/medir.sh [execuções=3]
# Imprime uma tabela em Markdown. Usa o IBGE falso da suíte de verificação: nenhuma chamada ao IBGE real.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
exec python3 -I specs/003-localidades-java/medicao/medir.py "${1:-3}"

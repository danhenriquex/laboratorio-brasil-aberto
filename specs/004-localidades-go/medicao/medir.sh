#!/usr/bin/env bash
# Comparação E1 (Python) × E4 (Java) × E7 (Go): as 9 medidas do FR-006, pelo método do R13 do E4 e do R15 do E7.
# Uso, a partir da raiz do repositório:  specs/004-localidades-go/medicao/medir.sh [execuções=3]
# Imprime uma tabela em Markdown. Usa o IBGE falso da suíte de verificação: nenhuma chamada ao IBGE real.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
exec python3 -I specs/004-localidades-go/medicao/medir.py "${1:-3}"

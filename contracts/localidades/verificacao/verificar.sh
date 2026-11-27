#!/usr/bin/env bash
# Verificação de caixa-preta do contrato de localidades (E1 e E4).
#
# Uso, a partir da raiz do repositório:
#   contracts/localidades/verificacao/verificar.sh "<comando que sobe o serviço>" [argumentos extras do pytest]
#
# Sobe o IBGE falso e o serviço com o perfil de verificação, espera o /health, roda a suíte e encerra os dois.
# Respeita UV_OFFLINE, se estiver definida.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "uso: $0 \"<comando que sobe o serviço>\" [argumentos do pytest]" >&2
  exit 2
fi

COMANDO_SERVICO="$1"
shift

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORTA_IBGE="${IBGE_FALSO_PORTA:-8099}"
PORTA_SERVICO="${LOCALIDADES_VERIFICACAO_PORTA:-8090}"
LOGS="$(mktemp -d)"
PIDS=()

encerrar() {
  for pid in "${PIDS[@]:-}"; do
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap encerrar EXIT INT TERM

esperar() {  # esperar <url> <nome> <arquivo de log>
  for _ in $(seq 1 120); do
    if curl -fsS -o /dev/null "$1" 2>/dev/null; then return 0; fi
    sleep 0.25
  done
  echo "$2 não respondeu em $1 em 30 s. Log:" >&2
  cat "$3" >&2
  exit 1
}

uv run --quiet --project "$AQUI" ibge-falso --porta "$PORTA_IBGE" >"$LOGS/ibge.log" 2>&1 &
PIDS+=($!)
esperar "http://127.0.0.1:$PORTA_IBGE/api/v1/localidades/estados" "IBGE falso" "$LOGS/ibge.log"

LOCALIDADES_HOST=127.0.0.1 \
LOCALIDADES_PORTA="$PORTA_SERVICO" \
LOCALIDADES_IBGE_URL="http://127.0.0.1:$PORTA_IBGE/api/v1/localidades" \
LOCALIDADES_PRAZO_FONTE_S=1 \
LOCALIDADES_VALIDADE_S=2 \
LOCALIDADES_ITENS_MAX=500 \
  bash -c "exec $COMANDO_SERVICO" >"$LOGS/servico.log" 2>&1 &
PIDS+=($!)
esperar "http://127.0.0.1:$PORTA_SERVICO/health" "Serviço" "$LOGS/servico.log"

set +e
LOCALIDADES_URL="http://127.0.0.1:$PORTA_SERVICO" \
IBGE_FALSO_URL="http://127.0.0.1:$PORTA_IBGE" \
  uv run --quiet --project "$AQUI" pytest "$AQUI/tests" "$@"
CODIGO=$?
set -e
echo "logs do serviço e do IBGE falso: $LOGS"
exit $CODIGO

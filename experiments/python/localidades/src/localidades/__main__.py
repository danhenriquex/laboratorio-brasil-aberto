"""Ponto de entrada: `localidades` ou `python -m localidades`."""

from __future__ import annotations

import sys


def main() -> int:
    import uvicorn

    from localidades.api import criar_app
    from localidades.config import Configuracao

    try:
        config = Configuracao.do_ambiente()
    except ValueError as erro:
        print(f"configuração inválida: {erro}", file=sys.stderr)
        return 2
    uvicorn.run(criar_app(config), host=config.host, port=config.porta, log_level="warning", access_log=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())

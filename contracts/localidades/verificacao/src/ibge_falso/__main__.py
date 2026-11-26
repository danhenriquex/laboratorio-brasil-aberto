"""`ibge-falso --porta 8099 [--fixtures PASTA]`: sobe o IBGE falso até ser interrompido."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ibge_falso.servidor import FIXTURES_PADRAO, criar_servidor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ibge-falso", description="IBGE falso para a verificação do contrato.")
    parser.add_argument("--porta", type=int, default=8099)
    parser.add_argument("--fixtures", type=Path, default=FIXTURES_PADRAO)
    args = parser.parse_args(argv)
    servidor = criar_servidor(args.porta, args.fixtures)
    print(f"IBGE falso em http://127.0.0.1:{args.porta}/api/v1/localidades (fixtures: {args.fixtures})", flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

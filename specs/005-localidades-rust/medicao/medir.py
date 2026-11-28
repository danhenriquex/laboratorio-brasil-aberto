"""Mede o E1 (Python), o E4 (Java), o E7 (Go) e o E8 (Rust) pelo mesmo método (FR-006 do E8; research do
E8, R15).

Cópia estendida do medir.py do E7 (specs/004-localidades-go/medicao/), que fica como registro da medição
do E7. Roda a partir da raiz do repositório (use medir.sh). Só a biblioteca padrão. Os serviços falam com o
IBGE falso da suíte de verificação (127.0.0.1), então nenhuma medida depende da rede externa nem do IBGE real.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

RAIZ = Path.cwd()
EXECUCOES = int(sys.argv[1]) if len(sys.argv) > 1 else 3
PORTA_IBGE = 8189
PORTA_SERVICO = 8195
IBGE_URL = f"http://127.0.0.1:{PORTA_IBGE}/api/v1/localidades"

E1 = {
    "nome": "E1 (Python)",
    "pasta": "experiments/python/localidades",
    "build": ["uv", "sync", "--quiet", "--project", "experiments/python/localidades"],
    "subir": ["uv", "run", "--quiet", "--project", "experiments/python/localidades", "localidades"],
    "testes": ["uv", "run", "--quiet", "--directory", "experiments/python/localidades", "pytest", "-q"],
    "prod": "experiments/python/localidades/src",
    "teste": "experiments/python/localidades/tests",
    "extensoes": (".py",),
}
E4 = {
    "nome": "E4 (Java)",
    "pasta": "experiments/java/localidades",
    "build": ["sh", "-c", "cd experiments/java/localidades && ./mvnw -q package -DskipTests"],
    "subir": ["java", "-jar", "experiments/java/localidades/target/localidades.jar"],
    "testes": ["sh", "-c", "cd experiments/java/localidades && ./mvnw -q test"],
    "prod": "experiments/java/localidades/src/main",
    "teste": "experiments/java/localidades/src/test",
    "extensoes": (".java", ".properties", ".xml"),
}
E7 = {
    "nome": "E7 (Go)",
    "pasta": "experiments/go/localidades",
    "build": ["sh", "-c", "cd experiments/go/localidades && go build -o localidades ./cmd/localidades"],
    "subir": ["experiments/go/localidades/localidades"],
    "testes": ["sh", "-c", "cd experiments/go/localidades && go test -count=1 ./..."],
    "prod": "experiments/go/localidades",
    "teste": "experiments/go/localidades",
    "extensoes": (".go",),
    "tocar": "experiments/go/localidades/internal/dominio/dominio.go",
}
E8 = {
    "nome": "E8 (Rust)",
    "pasta": "experiments/rust/localidades",
    "build": ["sh", "-c", "cd experiments/rust/localidades && cargo build --release --quiet"],
    "subir": ["experiments/rust/localidades/target/release/localidades"],
    "testes": ["sh", "-c", "cd experiments/rust/localidades && cargo test --quiet"],
    "prod": "experiments/rust/localidades/src",
    "teste": "experiments/rust/localidades/tests",
    "extensoes": (".rs",),
    "tocar": "experiments/rust/localidades/src/dominio.rs",
}
E1["tocar"] = "experiments/python/localidades/src/localidades/dominio.py"
E4["tocar"] = "experiments/java/localidades/src/main/java/io/github/danhenriquex/brasilaberto/localidades/dominio/Dobra.java"


def ambiente() -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        LOCALIDADES_HOST="127.0.0.1",
        LOCALIDADES_PORTA=str(PORTA_SERVICO),
        LOCALIDADES_IBGE_URL=IBGE_URL,
    )
    return env


def esperar(url: str, limite_s: float = 60) -> float:
    """Espera a primeira resposta 200 e devolve os segundos decorridos."""
    inicio = time.monotonic()
    while time.monotonic() - inicio < limite_s:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return time.monotonic() - inicio
        except OSError:
            pass
        time.sleep(0.02)
    raise RuntimeError(f"{url} não respondeu em {limite_s} s")


def pid_na_porta(porta: int) -> int:
    saida = subprocess.run(["lsof", "-ti", f"tcp:{porta}", "-sTCP:LISTEN"], capture_output=True, text=True).stdout
    return int(saida.split()[0])


def parar(processo: subprocess.Popen) -> None:
    try:
        os.killpg(processo.pid, signal.SIGTERM)
        processo.wait(timeout=15)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        os.killpg(processo.pid, signal.SIGKILL)
    for _ in range(100):  # espera a porta liberar
        if subprocess.run(["lsof", "-ti", f"tcp:{PORTA_SERVICO}"], capture_output=True).returncode != 0:
            return
        time.sleep(0.05)


def subir(impl: dict, cwd: Path) -> subprocess.Popen:
    return subprocess.Popen(impl["subir"], cwd=cwd, env=ambiente(), stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True)


def cronometrar(comando: list[str], cwd: Path = RAIZ) -> float:
    inicio = time.monotonic()
    subprocess.run(comando, cwd=cwd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return time.monotonic() - inicio


def do_clone_a_primeira_resposta(impl: dict) -> tuple[float, float]:
    """Clone local limpo → build → subir → primeira resposta de /v1/ufs. Devolve (total, só o build)."""
    with tempfile.TemporaryDirectory(prefix="medicao-") as pasta:
        clone = Path(pasta) / "repo"
        inicio = time.monotonic()
        subprocess.run(["git", "clone", "--quiet", "--local", str(RAIZ), str(clone)], check=True)
        build = cronometrar(impl["build"], cwd=clone)
        processo = subir(impl, clone)
        try:
            esperar(f"http://127.0.0.1:{PORTA_SERVICO}/v1/ufs")
            total = time.monotonic() - inicio
        finally:
            parar(processo)
        return total, build


def latencia_mediana(url: str, pedidos: int) -> float:
    tempos = []
    for _ in range(pedidos):
        inicio = time.perf_counter()
        urllib.request.urlopen(url, timeout=5).read()
        tempos.append((time.perf_counter() - inicio) * 1000)
    return statistics.median(tempos)


def partida_memoria_latencia(impl: dict) -> tuple[float, float, float, float]:
    """Partida até o /health, RSS depois de 10 pedidos, latência mediana de 20 pedidos com a cópia guardada e,
    como contexto, a mesma latência depois de 500 pedidos de aquecimento (JIT da JVM)."""
    processo = subir(impl, RAIZ)
    try:
        partida = esperar(f"http://127.0.0.1:{PORTA_SERVICO}/health")
        url = f"http://127.0.0.1:{PORTA_SERVICO}/v1/municipios/3304557"
        for _ in range(10):
            urllib.request.urlopen(url, timeout=5).read()
        rss_kb = int(subprocess.run(["ps", "-o", "rss=", "-p", str(pid_na_porta(PORTA_SERVICO))],
                                    capture_output=True, text=True).stdout.strip())
        fria = latencia_mediana(url, 20)
        for _ in range(500):
            urllib.request.urlopen(url, timeout=5).read()
        aquecida = latencia_mediana(url, 20)
        return partida, rss_kb / 1024, fria, aquecida
    finally:
        parar(processo)


def linhas(pasta: str, extensoes: tuple[str, ...], filtro=lambda arquivo: True) -> int:
    total = 0
    for arquivo in Path(pasta).rglob("*"):
        if arquivo.is_file() and arquivo.suffix in extensoes and "__pycache__" not in arquivo.parts and filtro(arquivo):
            total += sum(1 for linha in arquivo.read_text(encoding="utf-8").splitlines() if linha.strip())
    return total


def eh_teste_go(arquivo: Path) -> bool:
    """Em Go, os testes ficam ao lado do código: *_test.go, mais o pacote de apoio testeapoio."""
    return arquivo.name.endswith("_test.go") or "testeapoio" in arquivo.parts


def partes_rust(pasta: str) -> tuple[int, int]:
    """Em Rust, os testes de unidade ficam no próprio arquivo, num bloco #[cfg(test)] que vai até o fim dele
    (conferido em todos os arquivos de src/). O que vem antes é produção; o bloco conta como teste."""
    prod = teste = 0
    for arquivo in Path(pasta).rglob("*.rs"):
        em_teste = False
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            if linha.strip() == "#[cfg(test)]":
                em_teste = True
            if linha.strip():
                if em_teste:
                    teste += 1
                else:
                    prod += 1
    return prod, teste


def linhas_de(impl: dict) -> str:
    if impl is E8:
        prod, teste_unidade = partes_rust(impl["prod"])
        return f"{prod} / {teste_unidade + linhas(impl['teste'], impl['extensoes'])}"
    if impl is E7:
        prod = linhas(impl["prod"], impl["extensoes"], lambda a: not eh_teste_go(a))
        teste = linhas(impl["teste"], impl["extensoes"], eh_teste_go)
        return f"{prod} / {teste}"
    return f"{linhas(impl['prod'], impl['extensoes'])} / {linhas(impl['teste'], impl['extensoes'])}"


def tamanho_mb(impl: dict) -> float:
    if impl is E4:
        return Path("experiments/java/localidades/target/localidades.jar").stat().st_size / 1e6
    if impl is E7:
        return Path("experiments/go/localidades/localidades").stat().st_size / 1e6
    if impl is E8:
        return Path("experiments/rust/localidades/target/release/localidades").stat().st_size / 1e6
    pasta = Path(impl["pasta"])
    total = sum(f.stat().st_size for f in (pasta / ".venv").rglob("*") if f.is_file())
    total += sum(f.stat().st_size for f in (pasta / "src").rglob("*") if f.is_file())
    return total / 1e6


def dependencias(impl: dict) -> tuple[int, int]:
    """(runtime, teste) diretas, declaradas no pyproject.toml, no pom.xml, no go.mod ou no Cargo.toml."""
    if impl is E8:
        with open("experiments/rust/localidades/Cargo.toml", "rb") as f:
            cargo = tomllib.load(f)
        return len(cargo.get("dependencies", {})), len(cargo.get("dev-dependencies", {}))
    if impl is E7:
        # Diretas são as linhas de require sem "// indirect". Os testes usam só a biblioteca padrão.
        texto = Path("experiments/go/localidades/go.mod").read_text()
        blocos = re.findall(r"require \((.*?)\)", texto, re.S) + re.findall(r"^require ([^(\n]+)$", texto, re.M)
        diretas = [l for b in blocos for l in b.strip().splitlines() if l.strip() and "// indirect" not in l]
        return len(diretas), 0
    if impl is E1:
        texto = Path("experiments/python/localidades/pyproject.toml").read_text()
        runtime = re.search(r"dependencies = \[(.*?)\]", texto, re.S).group(1)
        dev = re.search(r"dev = \[(.*?)\]", texto, re.S).group(1)
        return len(re.findall(r'"[^"]+"', runtime)), len(re.findall(r'"[^"]+"', dev))
    texto = Path("experiments/java/localidades/pom.xml").read_text()
    blocos = re.findall(r"<dependency>(.*?)</dependency>", texto, re.S)
    teste = sum(1 for b in blocos if "<scope>test</scope>" in b)
    return len(blocos) - teste, teste


def depois_de_mudar(impl: dict, comando: list[str]) -> float:
    """Tempo de um comando depois de mudar um arquivo de produção (só o carimbo de data, conteúdo intacto).
    Mostra o custo de recompilar o próprio código com o cache de build quente."""
    os.utime(impl["tocar"])
    return cronometrar(comando)


def mediana(valores: list[float]) -> float:
    return statistics.median(valores)


def medir(impl: dict) -> dict[str, str]:
    print(f"medindo {impl['nome']}…", file=sys.stderr, flush=True)
    subprocess.run(impl["build"], cwd=RAIZ, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    clones = [do_clone_a_primeira_resposta(impl) for _ in range(EXECUCOES)]
    # Uma rodada antes de cronometrar: no Rust, a primeira compila os binários de teste (perfil dev).
    subprocess.run(impl["testes"], cwd=RAIZ, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    testes = [cronometrar(impl["testes"]) for _ in range(EXECUCOES)]
    build_quente = [depois_de_mudar(impl, impl["build"]) for _ in range(EXECUCOES)]
    testes_quentes = [depois_de_mudar(impl, impl["testes"]) for _ in range(EXECUCOES)]
    execucoes = [partida_memoria_latencia(impl) for _ in range(EXECUCOES)]
    runtime, teste = dependencias(impl)
    return {
        "clone": f"{mediana([c[0] for c in clones]):.1f} s",
        "build": f"{mediana([c[1] for c in clones]):.1f} s",
        "testes": f"{mediana(testes):.1f} s",
        "build_quente": f"{mediana(build_quente):.1f} s",
        "testes_quentes": f"{mediana(testes_quentes):.1f} s",
        "partida": f"{mediana([e[0] for e in execucoes]):.2f} s",
        "memoria": f"{mediana([e[1] for e in execucoes]):.0f} MB",
        "tamanho": f"{tamanho_mb(impl):.1f} MB",
        "linhas": linhas_de(impl),
        "deps": f"{runtime} + {teste}",
        "latencia": f"{mediana([e[2] for e in execucoes]):.2f} ms",
        "aquecida": f"{mediana([e[3] for e in execucoes]):.2f} ms",
    }


def versao(comando: list[str]) -> str:
    saida = subprocess.run(comando, capture_output=True, text=True)
    return (saida.stdout or saida.stderr).strip().splitlines()[0]


def main() -> None:
    ibge = subprocess.Popen(
        ["uv", "run", "--quiet", "--project", "contracts/localidades/verificacao", "ibge-falso", "--porta", str(PORTA_IBGE)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        esperar(f"{IBGE_URL}/estados")
        resultados = {"E1": medir(E1), "E4": medir(E4), "E7": medir(E7), "E8": medir(E8)}
    finally:
        os.killpg(ibge.pid, signal.SIGTERM)

    linhas_tabela = [
        ("Do clone local à primeira resposta (`/v1/ufs`)", "clone"),
        ("Build (dentro do clone)", "build"),
        ("Suíte de testes da implementação", "testes"),
        ("_Contexto:_ build depois de mudar um arquivo de produção", "build_quente"),
        ("_Contexto:_ suíte depois de mudar um arquivo de produção", "testes_quentes"),
        ("Partida até o `/health` responder", "partida"),
        ("Memória (RSS) depois de 10 pedidos", "memoria"),
        ("Tamanho do artefato", "tamanho"),
        ("Linhas de código (produção / testes, sem linhas em branco)", "linhas"),
        ("Dependências diretas (runtime + teste)", "deps"),
        ("Latência mediana com a cópia guardada (20 pedidos)", "latencia"),
        ("_Contexto:_ a mesma latência depois de 500 pedidos de aquecimento", "aquecida"),
    ]
    agora = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    print(f"# Medição E1 × E4 × E7 × E8 — {agora}\n")
    print(f"- **Máquina:** {platform.machine()}, macOS {platform.mac_ver()[0]}, {os.cpu_count()} CPUs")
    print(f"- **Versões:** {versao(['uv', 'run', '--quiet', '--project', E1['pasta'], 'python', '--version'])}; "
          f"{versao(['java', '-version'])}; {versao(['go', 'version'])}; {versao(['rustc', '--version'])}")
    print(f"- **Método:** research do E4, R13, do E7, R15, e do E8, R15. Mediana de {EXECUCOES} execuções por medida de tempo e memória; caches de "
          "dependências (`~/.cache/uv`, `~/.m2`, cache de módulos e de build do Go, registro de crates em `~/.cargo`) já populados; "
          "IBGE falso em 127.0.0.1, sem rede externa.")
    print("- **Build no clone:** o cache de build do Go é global, então o clone do E7 compila com o cache quente; o `target/` do Rust "
          "fica dentro do projeto, então o clone do E8 compila todas as dependências do zero (o `target/` frio). As linhas de contexto "
          "mostram o build e a suíte com o cache quente, depois de mudar só o carimbo de data de um arquivo de produção.")
    print("- **Artefato:** E1 = `.venv` + `src/`; E4 = `localidades.jar` (já inclui as dependências e o servidor); "
          "E7 e E8 = o binário `localidades` (já inclui tudo, sem runtime à parte).")
    print("- **Linhas:** E1 conta `.py`; E4 conta `.java`, `.properties` e `.xml` (configuração que no E1 fica no código); "
          "E7 conta `.go`, com `*_test.go` e o pacote `testeapoio` como testes; E8 conta `.rs`, com `tests/` e os blocos "
          "`#[cfg(test)]` como testes.\n")
    print("| Medida | E1 (Python) | E4 (Java) | E7 (Go) | E8 (Rust) |")
    print("|---|---|---|---|---|")
    for rotulo, chave in linhas_tabela:
        valores = " | ".join(resultados[e][chave] for e in ("E1", "E4", "E7", "E8"))
        print(f"| {rotulo} | {valores} |")


if __name__ == "__main__":
    main()

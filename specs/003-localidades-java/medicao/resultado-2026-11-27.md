# Medição E1 × E4 — 2026-11-27 19:39 UTC

- **Máquina:** arm64, macOS 27.2.1, 12 CPUs
- **Versões:** Python 3.12.15; openjdk version "25.0.5.1" 2026-11-17 LTS
- **Método:** research.md R13. Mediana de 3 execuções por medida de tempo e memória; caches de dependências (`~/.cache/uv`, `~/.m2`) já populados; IBGE falso em 127.0.0.1, sem rede externa.
- **Artefato:** E1 = `.venv` + `src/`; E4 = `localidades.jar` (já inclui as dependências e o servidor).
- **Linhas:** E1 conta `.py`; E4 conta `.java`, `.properties` e `.xml` (configuração que no E1 fica no código).

| Medida | E1 (Python) | E4 (Java) |
|---|---|---|
| Do clone local à primeira resposta (`/v1/ufs`) | 1.0 s | 2.9 s |
| Build (dentro do clone) | 0.2 s | 1.7 s |
| Suíte de testes da implementação | 1.0 s | 5.9 s |
| Partida até o `/health` responder | 0.14 s | 1.01 s |
| Memória (RSS) depois de 10 pedidos | 55 MB | 261 MB |
| Tamanho do artefato | 80.9 MB | 26.2 MB |
| Linhas de código (produção / testes, sem linhas em branco) | 799 / 817 | 1093 / 1331 |
| Dependências diretas (runtime + teste) | 4 + 2 | 4 + 3 |
| Latência mediana com a cópia guardada (20 pedidos) | 0.39 ms | 0.80 ms |
| _Contexto:_ a mesma latência depois de 500 pedidos de aquecimento | 0.37 ms | 0.41 ms |

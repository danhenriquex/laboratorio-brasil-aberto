# Medição E1 × E4 × E7 — 2026-11-28 15:49 UTC

- **Máquina:** arm64, macOS 27.2.1, 12 CPUs
- **Versões:** Python 3.12.15; openjdk version "25.0.5.1" 2026-11-17 LTS; go version go1.27.4 darwin/arm64
- **Método:** research do E4, R13, e do E7, R15. Mediana de 3 execuções por medida de tempo e memória; caches de dependências (`~/.cache/uv`, `~/.m2`, cache de módulos e de build do Go) já populados; IBGE falso em 127.0.0.1, sem rede externa.
- **Artefato:** E1 = `.venv` + `src/`; E4 = `localidades.jar` (já inclui as dependências e o servidor); E7 = o binário `localidades` (já inclui tudo, sem runtime à parte).
- **Linhas:** E1 conta `.py`; E4 conta `.java`, `.properties` e `.xml` (configuração que no E1 fica no código); E7 conta `.go`, com `*_test.go` e o pacote `testeapoio` como testes.

| Medida | E1 (Python) | E4 (Java) | E7 (Go) |
|---|---|---|---|
| Do clone local à primeira resposta (`/v1/ufs`) | 1.1 s | 3.0 s | 1.2 s |
| Build (dentro do clone) | 0.2 s | 1.9 s | 0.8 s |
| Suíte de testes da implementação | 0.9 s | 6.6 s | 1.0 s |
| Partida até o `/health` responder | 0.17 s | 1.04 s | 0.03 s |
| Memória (RSS) depois de 10 pedidos | 55 MB | 251 MB | 15 MB |
| Tamanho do artefato | 80.9 MB | 26.3 MB | 14.9 MB |
| Linhas de código (produção / testes, sem linhas em branco) | 799 / 817 | 1279 / 1513 | 1758 / 1996 |
| Dependências diretas (runtime + teste) | 4 + 2 | 4 + 3 | 3 + 0 |
| Latência mediana com a cópia guardada (20 pedidos) | 0.40 ms | 0.76 ms | 0.13 ms |
| _Contexto:_ a mesma latência depois de 500 pedidos de aquecimento | 0.37 ms | 0.38 ms | 0.09 ms |

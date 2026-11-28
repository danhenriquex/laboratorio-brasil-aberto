# Medição E1 × E4 × E7 × E8 — 2026-11-28 17:33 UTC

- **Máquina:** arm64, macOS 27.2.1, 12 CPUs
- **Versões:** Python 3.12.15; openjdk version "25.0.5.1" 2026-11-17 LTS; go version go1.27.4 darwin/arm64; rustc 1.100.1 (20ddd0171 2026-11-25)
- **Método:** research do E4, R13, do E7, R15, e do E8, R15. Mediana de 3 execuções por medida de tempo e memória; caches de dependências (`~/.cache/uv`, `~/.m2`, cache de módulos e de build do Go, registro de crates em `~/.cargo`) já populados; IBGE falso em 127.0.0.1, sem rede externa.
- **Build no clone:** o cache de build do Go é global, então o clone do E7 compila com o cache quente; o `target/` do Rust fica dentro do projeto, então o clone do E8 compila todas as dependências do zero (o `target/` frio). As linhas de contexto mostram o build e a suíte com o cache quente, depois de mudar só o carimbo de data de um arquivo de produção.
- **Artefato:** E1 = `.venv` + `src/`; E4 = `localidades.jar` (já inclui as dependências e o servidor); E7 e E8 = o binário `localidades` (já inclui tudo, sem runtime à parte).
- **Linhas:** E1 conta `.py`; E4 conta `.java`, `.properties` e `.xml` (configuração que no E1 fica no código); E7 conta `.go`, com `*_test.go` e o pacote `testeapoio` como testes; E8 conta `.rs`, com `tests/` e os blocos `#[cfg(test)]` como testes.

| Medida | E1 (Python) | E4 (Java) | E7 (Go) | E8 (Rust) |
|---|---|---|---|---|
| Do clone local à primeira resposta (`/v1/ufs`) | 1.2 s | 3.0 s | 1.3 s | 17.3 s |
| Build (dentro do clone) | 0.2 s | 1.7 s | 0.8 s | 16.9 s |
| Suíte de testes da implementação | 0.9 s | 6.1 s | 1.0 s | 0.7 s |
| _Contexto:_ build depois de mudar um arquivo de produção | 0.0 s | 1.5 s | 0.1 s | 1.9 s |
| _Contexto:_ suíte depois de mudar um arquivo de produção | 0.9 s | 6.5 s | 1.1 s | 5.2 s |
| Partida até o `/health` responder | 0.15 s | 0.98 s | 0.03 s | 0.02 s |
| Memória (RSS) depois de 10 pedidos | 55 MB | 252 MB | 15 MB | 11 MB |
| Tamanho do artefato | 80.9 MB | 26.3 MB | 14.9 MB | 8.9 MB |
| Linhas de código (produção / testes, sem linhas em branco) | 799 / 817 | 1279 / 1513 | 1766 / 2038 | 1753 / 2406 |
| Dependências diretas (runtime + teste) | 4 + 2 | 4 + 3 | 3 + 0 | 12 + 1 |
| Latência mediana com a cópia guardada (20 pedidos) | 0.38 ms | 0.76 ms | 0.12 ms | 0.12 ms |
| _Contexto:_ a mesma latência depois de 500 pedidos de aquecimento | 0.36 ms | 0.37 ms | 0.08 ms | 0.09 ms |

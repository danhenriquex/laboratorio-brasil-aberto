# Diário de ergonomia: E8 (Rust), comparado ao E1 (Python), ao E4 (Java) e ao E7 (Go)

Escrito durante a implementação, e não de memória no fim (FR-007; research R15). As notas de 1 a 5 entram na consolidação da US6 (T038).

## Setup

- **2026-11-28, instalação:** o usuário instalou o Rust pelo `rustup` no próprio terminal, antes da T001: `rustc 1.100.1 (20ddd0171 2026-11-25)` e `cargo 1.100.1`, a versão listada em rust-lang.org. Sem senha de administrador, como no Go.
- **2026-11-28, crate e dependências:** `cargo new` e `cargo add` das dependências do research levaram 12 s, incluindo o download do índice. O `Cargo.lock` é o *lockfile*. O `reqwest` 0.13 já vem com TLS em Rust puro (`rustls` com `aws-lc-rs`) por padrão, sem depender do OpenSSL do sistema.
- **2026-11-28, primeiro build otimizado:** `cargo build --release` do esqueleto levou **34 s com o cache frio** (25 s de compilação e o resto de download), e menos de 1 s quando só o crate muda. As 12 dependências diretas puxam **179 crates** ao todo. O binário do esqueleto tem 2,6 MB.
- **Aviso de dependência sem uso:** o cargo 1.100 avisa no build quando uma dependência declarada ainda não é usada (`warning: unused dependency`), o equivalente ao que o `go mod tidy` fazia no E7, mas sem remover nada.

## Testes

- **2026-11-28, fundação:** `cargo test` com `#[tokio::test]` e `assert_eq!`. O IBGE simulado é um servidor axum em `127.0.0.1:0` dentro do próprio teste, sem biblioteca de *mock*. Os testes de API chamam o roteador com `tower::ServiceExt::oneshot`, sem rede, e os pedidos crus vão a um servidor de verdade por `TcpStream`, como no E4 e no E7. Os testes de unidade ficam no próprio módulo (`#[cfg(test)]`), e os de integração em `tests/`.
- **Velocidade:** com o código já compilado, os 32 testes da fundação rodam em fração de segundo; recompilar o crate e os testes depois de uma mudança leva alguns segundos (medido na US6). É o ponto em que o Rust mais pesa no ciclo: cada mudança passa pelo compilador antes de qualquer teste rodar.
- **`clippy`:** com `-D warnings`, ele pegou dois pontos nos testes, e uma das sugestões (`cmp_owned`) mudaria a semântica, comparando um número JSON com um texto. Foi preciso reescrever em vez de aceitar a sugestão.

## Cumprir o contrato escrito à mão

- **2026-11-28, sondagem da pilha HTTP (T004):** com o esqueleto (só `GET /health`), pedidos crus mostraram que, ao contrário do Go, quase nada é decidido antes da aplicação:

  | Pedido | Resposta do esqueleto | Comparação |
  |---|---|---|
  | `GET /v1/municipios/%ZZ` | 404 vazio, do roteador | o `hyper` deixa passar; no E7, o `net/http` recusava antes do handler |
  | `GET //health`, `/./health`, `/x/../health` | 404 vazio | sem limpeza nem redirecionamento; no E7, o `ServeMux` redirecionava |
  | `GET /health;x` | 404 vazio | o `;` é texto; no E4, o Tomcat o descartava |
  | `POST /health`, `TRACE /health` | **405** com `Allow: GET,HEAD`, sem corpo | o mesmo 405 do E7, mas sem eco no `TRACE` |
  | `OPTIONS *` | 404 vazio, do roteador | chega à aplicação; no E7, o `http.Server` respondia sozinho |
  | `HEAD /health` | 200 | aceito, como no E4 e no E7 |
  | `GET /health` com `Accept: application/xml` | 200 em JSON | sem negociação |
  | `GET /health?x=%ZZ` | 200 | a *query* só é lida se o handler pedir |

- **2026-11-28, US1:** os 27 cenários da US1, da paridade de ordenação (os 645 municípios de SP) e de contrato passaram de primeira contra o binário. A paridade veio da dobra com `unicode-normalization` e `caseless`, sem ajuste, apesar da diferença entre a classe de combinação usada aqui e a categoria `Mn` do E1 (research R9).
- **Extratores e suas rejeições:** o axum lê os parâmetros por extratores tipados (`Path`, `Query`, `State`), o que deixa os handlers curtos. Mas cada extrator tem a sua resposta de erro pronta, fora do contrato: o `Path` recusaria `%ZZ` e o `Query` decodificaria de forma tolerante. A saída foi receber `Result<Path<String>, PathRejection>`, transformando a rejeição no texto literal do segmento, e ler a *query* do texto cru (`Uri::query()`), com a mesma regra do E7.
- **`serde_json`:** não escapa `<>&`, não põe quebra de linha no fim e escreve os campos na ordem da *struct*. As três armadilhas de JSON do Go não existem aqui.
- **2026-11-28, US2 e a lição da T044:** no Go, o `%ZZ` no caminho exigiu embrulhar o `net.Listener`, porque o `net/http` recusava o pedido antes de qualquer handler. Em Rust, o `hyper` entrega o pedido, e o único obstáculo é o extrator `Path`, que recusaria o segmento. Com a rejeição transformada no texto literal, `%ZZ`, `%` e `%E3` viram 400 `entrada-invalida` com correlação, como no E1. A barra codificada (`%2F`) decodifica para `/`, que também não é um código de 7 dígitos, e dá 400. A tarefa T020 previa 404, por analogia com o E7, mas o teste aceita 400 ou 404, como a suíte.
- **2026-11-28, configuração:** o `parse::<f64>()` do Rust aceita `inf`, `infinity` e `NaN` e transforma `1e400` em infinito sem erro. É a mesma lacuna da T049 do E4, a terceira linguagem seguida em que ela aparece. A recusa é explícita com `is_finite()`, e a mensagem sai igual à do E1.

  **Decisão (atualiza o R3):** não há `Ouvinte` como no E7. Basta o `fallback` e o `method_not_allowed_fallback` do roteador levarem ao 404 do contrato, e a camada de topo pôr a correlação e o formato. Fica um cuidado: o extrator `Path` do axum decodifica o segmento e, com `%ZZ`, recusaria o pedido com a sua própria resposta de erro. A rejeição dele precisa virar `entrada-invalida`.

## Tratamento de erros

- **2026-11-28, fundação:** o `ErroDominio` implementa `IntoResponse`, e os handlers devolvem `Result<_, ErroDominio>` com o operador `?`. É tão explícito quanto o erro como valor do Go, mas sem o `if err != nil` a cada chamada. A leitura do JSON do IBGE campo a campo saiu curta com um tipo de erro local (`Forma`) e `?`.
- **Correlação no corpo do erro:** como o `IntoResponse` não recebe o pedido, a correlação chega por um `task_local` do tokio, posto pela camada de topo. Funciona, mas a consulta ao IBGE roda noutra tarefa (US3), e lá o `task_local` não existe: será preciso levá-lo junto de forma explícita.
- **Panic:** um `catch_unwind` sobre o futuro do pedido, na camada de topo, transforma o `panic` em 500 sem rastro. Sem ele, o hyper derrubaria só a conexão.

## Métricas e registro

## Lições anteriores

Uma linha por comportamento fora do contrato achado antes, preenchida à medida que cada um aparecer (FR-009). A tabela final vai para o `RESULTS.md`.

| Lição | Apareceu em Rust? | Como foi tratada |
|---|---|---|
| T044 do E4 — caminho mal codificado fora do formato | Quase não: o `hyper` deixa o pedido chegar, e só o extrator `Path` recusaria o segmento com a sua própria resposta | A rejeição do `Path` vira o texto literal do segmento, que a validação recusa com 400 `entrada-invalida`. Sem saneamento da linha do pedido, ao contrário do E7 |
| T045 do E4 — `pagina` grande demais e parâmetro repetido | Em parte: `pagina=99999999999` cabe em `i64`, mas 30 dígitos estouram; o extrator `Query` não foi usado | Só dígitos que estouram `i64` valem como além do fim; a leitura da *query* crua usa o último valor repetido |
| T046 do E4 — *query* mal codificada virando 500 | Não viraria 500: o extrator `Query` decodificaria de forma tolerante, e a *query* chega crua ao handler | A leitura do texto cru recusa `%` sem dois dígitos hexadecimais e UTF-8 inválido com 400 `entrada-invalida` |
| T047 do E4 — `TRACE` fora do formato e ecoando o pedido | Em parte: o axum responde 405 com `Allow` e sem corpo, sem eco | `method_not_allowed_fallback` → 404 `nao-encontrado`; teste com pedido cru confere que nada é ecoado |
| T048 do E4 — `Accept` mudando o formato da resposta | Não: o axum não negocia conteúdo | Os handlers escrevem o `Content-Type`; um teste fixa isso para `/health` e para os erros |
| T049 do E4 — configuração infinita ou arredondada para zero | Sim: o `parse::<f64>()` aceita `inf`, `infinity` e `NaN` | Recusa explícita com `is_finite()`, mais os limites de 0,001 e 10⁹ s, com a mensagem do E1 |
| T050 do E4 — parâmetros de caminho (`;`) ignorados | Não: o `;` é texto, e o roteador não normaliza `//`, `.` nem `..` | Nada a fazer além do `fallback`: o caminho não casa rota nenhuma e cai no 404 do contrato |
| T044 do E7 — `OPTIONS *` respondido pelo próprio servidor | Não: o hyper entrega o `OPTIONS *` ao roteador | O `fallback` dá o 404 do contrato, com correlação; teste com pedido cru |

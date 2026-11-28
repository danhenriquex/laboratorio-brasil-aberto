//! Camada de topo, espelhando o test_api_base.py do E1 e o base_test.go do E7, mais as lições anteriores.

mod apoio;

use axum::Router;
use axum::body::{Body, to_bytes};
use axum::http::{Request, StatusCode};
use axum::routing::get;
use localidades::operacao::saude;
use localidades::topo::{Topo, com_camadas};
use tower::ServiceExt;

fn app() -> Router {
    let rotas = Router::new().route("/health", get(saude)).route(
        "/v1/_panico",
        get(|| async {
            if true {
                panic!("segredo interno /etc/passwd")
            }
        }),
    );
    com_camadas(rotas, Topo::default())
}

struct Resp {
    status: StatusCode,
    tipo: String,
    correlacao: String,
    corpo: String,
}

async fn pedir(metodo: &str, alvo: &str, cabecalhos: &[(&str, &str)]) -> Resp {
    let mut req = Request::builder().method(metodo).uri(alvo);
    for (k, v) in cabecalhos {
        req = req.header(*k, *v);
    }
    let r = app()
        .oneshot(req.body(Body::empty()).unwrap())
        .await
        .unwrap();
    let cab = |n: &str| {
        r.headers()
            .get(n)
            .and_then(|v| v.to_str().ok())
            .unwrap_or("")
            .to_string()
    };
    let (status, tipo, correlacao) = (r.status(), cab("content-type"), cab("x-correlation-id"));
    let corpo =
        String::from_utf8(to_bytes(r.into_body(), usize::MAX).await.unwrap().to_vec()).unwrap();
    Resp {
        status,
        tipo,
        correlacao,
        corpo,
    }
}

/// O assert_problema do E1: status, tipo, problem+json e correlação no corpo e no cabeçalho.
fn conferir_problema(
    status: u16,
    tipo_conteudo: &str,
    correlacao: &str,
    corpo: &str,
    esperado: u16,
    tipo: &str,
) -> serde_json::Value {
    assert_eq!(status, esperado, "corpo: {corpo}");
    assert_eq!(tipo_conteudo, "application/problem+json");
    let p: serde_json::Value =
        serde_json::from_str(corpo).unwrap_or_else(|_| panic!("não é JSON: {corpo}"));
    assert_eq!(p["type"], format!("urn:brasil-aberto:problema:{tipo}"));
    assert_eq!(p["status"], esperado);
    assert!(!p["detail"].as_str().unwrap_or("").is_empty());
    assert!(!correlacao.is_empty());
    assert_eq!(p["correlacao_id"], correlacao);
    p
}

fn uuid_v4(s: &str) -> bool {
    uuid::Uuid::parse_str(s)
        .map(|u| u.get_version_num() == 4)
        .unwrap_or(false)
}

#[tokio::test]
async fn health() {
    let r = pedir("GET", "/health", &[]).await;
    assert_eq!(
        (r.status, r.tipo.as_str(), r.corpo.as_str()),
        (StatusCode::OK, "application/json", r#"{"status":"ok"}"#)
    );
}

#[tokio::test]
async fn rota_inexistente_e_problema_404() {
    for alvo in ["/v2/ufs", "/ufs", "/nada", "/v1", "/"] {
        let r = pedir("GET", alvo, &[]).await;
        let p = conferir_problema(
            r.status.as_u16(),
            &r.tipo,
            &r.correlacao,
            &r.corpo,
            404,
            "nao-encontrado",
        );
        assert_eq!(p["detail"], format!("a rota {alvo} não existe"));
    }
}

/// O axum responderia 405 com Allow; o contrato pede o mesmo 404 do E1 (T047 do E4).
#[tokio::test]
async fn metodo_nao_suportado_tambem_e_404() {
    for metodo in ["POST", "PUT", "DELETE", "PATCH", "TRACE"] {
        let r = pedir(metodo, "/health", &[]).await;
        conferir_problema(
            r.status.as_u16(),
            &r.tipo,
            &r.correlacao,
            &r.corpo,
            404,
            "nao-encontrado",
        );
    }
}

/// Pedido cru num servidor de verdade: TRACE sem eco, caminhos irregulares e OPTIONS * (T050 do E4 e T044
/// do E7), todos no 404 do contrato e com correlação.
#[tokio::test]
async fn pedidos_crus_no_formato_do_contrato() {
    let endereco = apoio::servir(app()).await;
    let r = apoio::pedido_cru(
        &endereco,
        "TRACE",
        "/health",
        &["X-Correlation-Id: trace-123", "Cookie: segredo=abc"],
    )
    .await;
    conferir_problema(
        r.status,
        r.cabecalho("content-type"),
        r.cabecalho("x-correlation-id"),
        &r.corpo,
        404,
        "nao-encontrado",
    );
    assert_eq!(r.cabecalho("x-correlation-id"), "trace-123");
    assert!(
        !r.bruto.contains("segredo") && !r.bruto.contains("TRACE /health"),
        "o TRACE ecoou:\n{}",
        r.bruto
    );
    for (metodo, alvo) in [
        ("GET", "//health"),
        ("GET", "/./health"),
        ("GET", "/x/../health"),
        ("GET", "/health;x"),
        ("GET", "/health;jsessionid=1"),
        ("GET", "/v1/%2e%2e/health"),
        ("OPTIONS", "*"),
    ] {
        let r = apoio::pedido_cru(&endereco, metodo, alvo, &["X-Correlation-Id: caminho-1"]).await;
        assert!(
            !(300..400).contains(&r.status),
            "{metodo} {alvo}: redirecionou"
        );
        conferir_problema(
            r.status,
            r.cabecalho("content-type"),
            r.cabecalho("x-correlation-id"),
            &r.corpo,
            404,
            "nao-encontrado",
        );
    }
}

#[tokio::test]
async fn correlacao_valida_volta_igual_e_invalida_vira_uuid_v4() {
    assert_eq!(
        pedir("GET", "/health", &[("X-Correlation-Id", "teste-123_a.b")])
            .await
            .correlacao,
        "teste-123_a.b"
    );
    let longo = "x".repeat(65);
    for valor in ["com espaço", "acentuação", longo.as_str()] {
        let c = pedir("GET", "/health", &[("X-Correlation-Id", valor)])
            .await
            .correlacao;
        assert!(uuid_v4(&c), "{valor:?} virou {c:?}");
    }
    assert!(uuid_v4(&pedir("GET", "/health", &[]).await.correlacao));
    let max = "x".repeat(64);
    assert_eq!(
        pedir("GET", "/health", &[("X-Correlation-Id", max.as_str())])
            .await
            .correlacao,
        max
    );
}

#[tokio::test]
async fn panico_vira_500_sem_rastro() {
    let r = pedir("GET", "/v1/_panico", &[]).await;
    let p = conferir_problema(
        r.status.as_u16(),
        &r.tipo,
        &r.correlacao,
        &r.corpo,
        500,
        "erro-interno",
    );
    assert_eq!(p["detail"], "erro interno do serviço");
    assert!(
        !r.corpo.contains("segredo") && !r.corpo.contains(".rs"),
        "vazou: {}",
        r.corpo
    );
}

/// T048 do E4: o Accept não muda o formato.
#[tokio::test]
async fn accept_e_ignorado() {
    for aceita in [
        "application/xml",
        "text/html",
        "text/plain",
        "application/problem+json",
    ] {
        let r = pedir("GET", "/health", &[("Accept", aceita)]).await;
        assert_eq!(
            (r.status, r.tipo.as_str()),
            (StatusCode::OK, "application/json"),
            "Accept {aceita}"
        );
        let r = pedir("GET", "/nada", &[("Accept", aceita)]).await;
        conferir_problema(
            r.status.as_u16(),
            &r.tipo,
            &r.correlacao,
            &r.corpo,
            404,
            "nao-encontrado",
        );
    }
}

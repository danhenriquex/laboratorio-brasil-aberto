//! US5, com os casos do test_api_operacao.py do E1, do OperacaoTest.java do E4 e do operacao_test.go do E7.

mod apoio;

use std::io::Write;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use apoio::{Ibge, Resposta, fixture};
use axum::Router;
use axum::routing::get;
use localidades::fonte::Cliente;
use localidades::operacao::{Metricas, Registro, estado_atual, observador};
use localidades::servico::{Opcoes, Servico};
use localidades::topo::{self, Topo};
use tower::ServiceExt;

/// Junta as linhas do registro, que podem vir de tarefas diferentes.
#[derive(Clone, Default)]
struct Saida(Arc<Mutex<Vec<u8>>>);

impl Write for Saida {
    fn write(&mut self, b: &[u8]) -> std::io::Result<usize> {
        self.0.lock().unwrap().extend_from_slice(b);
        Ok(b.len())
    }
    fn flush(&mut self) -> std::io::Result<()> {
        Ok(())
    }
}

impl Saida {
    /// Cada linha como texto bruto e como JSON.
    fn linhas(&self) -> Vec<(String, serde_json::Value)> {
        let texto = String::from_utf8(self.0.lock().unwrap().clone()).unwrap();
        texto
            .lines()
            .filter(|l| !l.is_empty())
            .map(|l| {
                let v = serde_json::from_str(l)
                    .unwrap_or_else(|_| panic!("linha do registro não é JSON: {l:?}"));
                (l.to_string(), v)
            })
            .collect()
    }
}

/// Sobe o serviço como o main faz, com métricas e registro, contra o IBGE simulado.
async fn montar() -> (Router, Ibge, Saida) {
    let ibge = Ibge::novo().await;
    ibge.responder_fixture("/estados", "estados.json");
    let metricas = Metricas::novas();
    let saida = Saida::default();
    let registro = Arc::new(Registro::novo(Box::new(saida.clone())));
    let m = metricas.clone();
    let ao_medir = Arc::new(move |recurso: &str, s: f64| {
        m.observar_fonte(recurso, s);
        if let Some(estado) = estado_atual() {
            estado.somar_fonte(s);
        }
    });
    let cliente = Cliente::novo(&ibge.url(), Duration::from_secs(1), Some(ao_medir));
    let servico = Servico::novo(cliente, Opcoes::do_sistema(Duration::from_secs(3600), 500));
    let topo = Topo {
        observar: Some(observador(metricas.clone(), registro)),
        metricas: Some(metricas),
    };
    (localidades::app(servico, topo), ibge, saida)
}

struct Resp {
    status: u16,
    tipo: String,
    corpo: String,
}

async fn pedir(app: &Router, alvo: &str, cabecalhos: &[(&str, &str)]) -> Resp {
    let mut req = axum::http::Request::builder().uri(alvo);
    for (k, v) in cabecalhos {
        req = req.header(*k, *v);
    }
    let r = app
        .clone()
        .oneshot(req.body(axum::body::Body::empty()).unwrap())
        .await
        .unwrap();
    let status = r.status().as_u16();
    let tipo = r
        .headers()
        .get("content-type")
        .and_then(|v| v.to_str().ok())
        .unwrap_or("")
        .to_string();
    let bytes = axum::body::to_bytes(r.into_body(), usize::MAX)
        .await
        .unwrap();
    Resp {
        status,
        tipo,
        corpo: String::from_utf8(bytes.to_vec()).unwrap(),
    }
}

#[tokio::test]
async fn metricas_com_os_nomes_do_contrato() {
    let (app, _ibge, _) = montar().await;
    pedir(&app, "/v1/ufs", &[]).await;
    pedir(&app, "/v1/ufs/RJ", &[]).await; // mesma cópia: acerto
    pedir(&app, "/v1/municipios/12ab", &[]).await;
    pedir(&app, "/nada", &[]).await;
    let r = pedir(&app, "/metrics", &[]).await;
    assert_eq!(r.status, 200);
    assert!(r.tipo.starts_with("text/plain"), "{}", r.tipo);
    for esperado in [
        r#"localidades_pedidos_total{rota="/v1/ufs",status="200"} 1"#,
        r#"localidades_pedidos_total{rota="/v1/ufs/{uf}",status="200"} 1"#,
        r#"localidades_pedidos_total{rota="/v1/municipios/{codigo}",status="400"} 1"#,
        r#"localidades_pedidos_total{rota="nao-encontrado",status="404"} 1"#,
        r#"localidades_erros_total{tipo="entrada-invalida"} 1"#,
        r#"localidades_erros_total{tipo="nao-encontrado"} 1"#,
        r#"localidades_cache_total{resultado="falta"} 1"#,
        r#"localidades_cache_total{resultado="acerto"} 1"#,
        r#"localidades_fonte_duracao_segundos_count{recurso="estados"} 1"#,
    ] {
        assert!(r.corpo.contains(esperado), "faltou {esperado}\n{}", r.corpo);
    }
    // As mesmas faixas do E1, sem sufixo de unidade no nome.
    for faixa in ["0.05", "0.1", "0.25", "0.5", "1", "2.5", "5", "10", "+Inf"] {
        let linha = format!(
            r#"localidades_fonte_duracao_segundos_bucket{{recurso="estados",le="{faixa}"}}"#
        );
        assert!(r.corpo.contains(&linha), "faltou a faixa {faixa}");
    }
    assert!(
        !r.corpo
            .contains("localidades_fonte_duracao_segundos_seconds")
    );
}

#[tokio::test]
async fn metricas_em_texto_com_qualquer_accept() {
    let (app, _ibge, _) = montar().await;
    for aceita in [
        "application/json",
        "application/xml",
        "application/vnd.google.protobuf;proto=io.prometheus.client.MetricFamily;encoding=delimited",
        "application/openmetrics-text; version=1.0.0",
    ] {
        let r = pedir(&app, "/metrics", &[("accept", aceita)]).await;
        assert_eq!(r.status, 200, "{aceita}");
        assert!(r.tipo.starts_with("text/plain"), "{aceita}: {}", r.tipo);
    }
}

#[tokio::test]
async fn registro_uma_linha_json_por_pedido() {
    let (app, _ibge, saida) = montar().await;
    pedir(&app, "/v1/ufs", &[("x-correlation-id", "registro-1")]).await;
    pedir(&app, "/v1/ufs", &[("x-correlation-id", "registro-2")]).await;
    pedir(&app, "/nada", &[("x-correlation-id", "registro-3")]).await;
    let linhas = saida.linhas();
    assert_eq!(linhas.len(), 3, "{linhas:?}");
    let campos = [
        "momento",
        "nivel",
        "correlacao_id",
        "metodo",
        "rota",
        "status",
        "duracao_ms",
        "cache",
        "fonte_ms",
    ];
    for (bruto, l) in &linhas {
        let chaves: Vec<&str> = l.as_object().unwrap().keys().map(String::as_str).collect();
        let mut esperadas = campos.to_vec();
        esperadas.sort();
        let mut obtidas = chaves.clone();
        obtidas.sort();
        assert_eq!(obtidas, esperadas, "campos a mais ou a menos: {bruto}");
        // A ordem dos campos é a do E1.
        let posicoes: Vec<usize> = campos
            .iter()
            .map(|c| bruto.find(&format!("\"{c}\":")).unwrap())
            .collect();
        assert!(posicoes.is_sorted(), "fora de ordem: {bruto}");
        let momento = l["momento"].as_str().unwrap();
        assert!(
            momento.len() == 24 && momento.ends_with('Z') && &momento[19..20] == ".",
            "momento fora do formato: {momento}"
        );
    }
    let (b1, primeira) = &linhas[0];
    assert_eq!(
        (
            primeira["correlacao_id"].as_str(),
            primeira["rota"].as_str(),
            primeira["status"].as_u64(),
            primeira["nivel"].as_str(),
            primeira["metodo"].as_str(),
            primeira["cache"].as_str()
        ),
        (
            Some("registro-1"),
            Some("/v1/ufs"),
            Some(200),
            Some("info"),
            Some("GET"),
            Some("falta")
        ),
        "{b1}"
    );
    assert!(primeira["fonte_ms"].is_number(), "{b1}");
    assert!(primeira["duracao_ms"].is_number(), "{b1}");
    let (b2, segunda) = &linhas[1];
    assert_eq!(segunda["cache"].as_str(), Some("acerto"), "{b2}");
    assert!(
        segunda["fonte_ms"].is_null(),
        "com a cópia, não há tempo de fonte: {b2}"
    );
    let (b3, terceira) = &linhas[2];
    assert_eq!(
        (
            terceira["rota"].as_str(),
            terceira["status"].as_u64(),
            terceira["cache"].is_null()
        ),
        (Some("nao-encontrado"), Some(404), true),
        "{b3}"
    );
}

#[tokio::test]
async fn registro_com_nivel_error_no_500() {
    let saida = Saida::default();
    let registro = Arc::new(Registro::novo(Box::new(saida.clone())));
    let metricas = Metricas::novas();
    let rotas = Router::new().route(
        "/v1/_panico",
        get(|| async {
            let falhar = true;
            if falhar {
                panic!("falha");
            }
            ""
        }),
    );
    let topo = Topo {
        observar: Some(observador(metricas.clone(), registro)),
        metricas: None,
    };
    let app = topo::com_camadas(rotas, topo);
    let r = pedir(&app, "/v1/_panico", &[]).await;
    assert_eq!(r.status, 500);
    let linhas = saida.linhas();
    assert_eq!(linhas.len(), 1, "{linhas:?}");
    assert_eq!(
        (
            linhas[0].1["nivel"].as_str(),
            linhas[0].1["status"].as_u64()
        ),
        (Some("error"), Some(500))
    );
    assert!(
        metricas
            .texto()
            .contains(r#"localidades_erros_total{tipo="erro-interno"} 1"#)
    );
}

/// Paridade com o E7: o pedido que o cliente abandona é registrado com 499 e não conta como erro do serviço.
#[tokio::test]
async fn cliente_que_desiste_e_registrado_com_499() {
    let (app, ibge, saida) = montar().await;
    ibge.responder(
        "/estados",
        Resposta {
            atraso: Duration::from_millis(500),
            ..Resposta::ok(fixture("estados.json"))
        },
    );
    let pedido = pedir(&app, "/v1/ufs", &[("x-correlation-id", "desistiu")]);
    assert!(
        tokio::time::timeout(Duration::from_millis(50), pedido)
            .await
            .is_err()
    );
    let linhas = saida.linhas();
    assert_eq!(linhas.len(), 1, "{linhas:?}");
    let l = &linhas[0].1;
    assert_eq!(
        (
            l["correlacao_id"].as_str(),
            l["rota"].as_str(),
            l["status"].as_u64(),
            l["nivel"].as_str()
        ),
        (Some("desistiu"), Some("/v1/ufs"), Some(499), Some("info"))
    );
    let texto = pedir(&app, "/metrics", &[]).await.corpo;
    assert!(texto.contains(r#"localidades_pedidos_total{rota="/v1/ufs",status="499"} 1"#));
    assert!(!texto.contains("localidades_erros_total{"), "{texto}");
}

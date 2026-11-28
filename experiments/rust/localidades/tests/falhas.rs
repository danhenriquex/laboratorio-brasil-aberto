//! US3, espelhando o test_api_falhas.py do E1 e o falhas_test.go do E7.

mod apoio;

use std::sync::Arc;
use std::time::{Duration, Instant};

use apoio::{Ambiente, Resposta, conferir_meta, conferir_problema, fixture};
use tokio::sync::Notify;

#[tokio::test]
async fn falhas_da_fonte_sem_copia() {
    let html = Resposta {
        tipo: "text/html",
        ..Resposta::ok(fixture("erro.html"))
    };
    let lenta = Resposta {
        atraso: Duration::from_millis(500),
        ..Resposta::ok(fixture("estados.json"))
    };
    for (nome, resposta, status, tipo) in [
        (
            "fonte fora",
            Resposta::status(503, "fora"),
            502,
            "fonte-indisponivel",
        ),
        (
            "resposta inválida",
            html,
            502,
            "resposta-inesperada-da-fonte",
        ),
        ("fonte lenta", lenta, 504, "fonte-lenta"),
    ] {
        let a = Ambiente::com_prazo(Duration::from_millis(100)).await;
        a.ibge.responder("/estados", resposta);
        let inicio = Instant::now();
        let r = a.get("/v1/ufs", &[]).await;
        conferir_problema(r.status, &r.tipo, &r.correlacao, &r.corpo, status, tipo);
        assert!(
            inicio.elapsed() < Duration::from_millis(400),
            "{nome}: passou do prazo"
        );
        assert!(
            !r.corpo.to_lowercase().contains("<html"),
            "{nome}: o corpo do IBGE vazou"
        );
    }
}

#[tokio::test]
async fn copia_valida_nao_consulta_a_fonte() {
    let a = Ambiente::novo().await;
    a.estados();
    let primeira = a.get("/v1/ufs", &[]).await.json();
    a.relogio.avancar(Duration::from_secs(23 * 3600));
    let segunda = a.get("/v1/ufs", &[]).await.json();
    assert_eq!(a.ibge.pedidos("/estados"), 1);
    assert_eq!(
        segunda["meta"]["coletado_em"], primeira["meta"]["coletado_em"],
        "a cópia mantém o coletado_em original"
    );
    a.get("/v1/ufs/RJ", &[]).await;
    assert_eq!(
        a.ibge.pedidos("/estados"),
        1,
        "/v1/ufs e /v1/ufs/{{uf}} usam a mesma cópia"
    );
}

#[tokio::test]
async fn copia_vencida_servida_quando_a_fonte_cai() {
    let a = Ambiente::novo().await;
    a.estados();
    let primeira = a.get("/v1/ufs", &[]).await.json();
    a.relogio.avancar(Duration::from_secs(25 * 3600));
    a.ibge.responder("/estados", Resposta::status(503, "fora"));
    let r = a.get("/v1/ufs", &[]).await;
    assert_eq!(r.status, 200, "{}", r.corpo);
    let corpo = r.json();
    conferir_meta(&corpo, &format!("{}/estados", a.ibge.url()), true);
    assert_eq!(
        corpo["meta"]["coletado_em"],
        primeira["meta"]["coletado_em"]
    );
    assert_eq!(
        a.ibge.pedidos("/estados"),
        2,
        "com a cópia vencida, a fonte é consultada de novo"
    );
}

/// Pedidos simultâneos com a fonte travada não fazem fila: uma consulta só, e todos recebem 504 no prazo.
#[tokio::test]
async fn pedidos_simultaneos_com_a_fonte_travada() {
    let a = Arc::new(Ambiente::com_prazo(Duration::from_millis(200)).await);
    a.ibge.responder(
        "/estados",
        Resposta {
            bloquear: Some(Arc::new(Notify::new())),
            ..Resposta::ok(fixture("estados.json"))
        },
    );
    let inicio = Instant::now();
    let pedidos: Vec<_> = (0..5)
        .map(|_| {
            let a = a.clone();
            tokio::spawn(async move { a.get("/v1/ufs", &[]).await.status })
        })
        .collect();
    for p in pedidos {
        assert_eq!(p.await.unwrap(), 504);
    }
    assert!(
        inicio.elapsed() < Duration::from_millis(600),
        "demorou {:?}",
        inicio.elapsed()
    );
    assert_eq!(a.ibge.pedidos("/estados"), 1);
}

/// Um pedido cujo cliente desiste (o futuro é abandonado) não cancela a consulta dos outros.
#[tokio::test]
async fn cliente_que_desiste_nao_atrapalha_os_outros() {
    let a = Arc::new(Ambiente::novo().await);
    let soltar = Arc::new(Notify::new());
    a.ibge.responder(
        "/estados",
        Resposta {
            bloquear: Some(soltar.clone()),
            ..Resposta::ok(fixture("estados.json"))
        },
    );
    // O primeiro pedido inicia a consulta e desiste depois de 50 ms.
    let desistente = tokio::time::timeout(Duration::from_millis(50), a.get("/v1/ufs", &[])).await;
    assert!(
        desistente.is_err(),
        "o primeiro pedido deveria ter sido abandonado"
    );
    let outro = {
        let a = a.clone();
        tokio::spawn(async move { a.get("/v1/ufs", &[]).await.status })
    };
    tokio::time::sleep(Duration::from_millis(50)).await;
    soltar.notify_waiters();
    assert_eq!(outro.await.unwrap(), 200);
    assert_eq!(
        a.ibge.pedidos("/estados"),
        1,
        "a consulta do pedido que desistiu continuou e foi aproveitada"
    );
}

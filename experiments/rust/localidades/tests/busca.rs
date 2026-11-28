//! US4, com os casos do test_api_busca.py do E1, do ApiBuscaTest.java do E4 e do busca_test.go do E7,
//! mais a lição da T046.

mod apoio;

use apoio::{Ambiente, conferir_problema, nomes};
use percent_encoding::{NON_ALPHANUMERIC, utf8_percent_encode};

async fn buscar(a: &Ambiente, uf: &str, termo: &str, extra: &[&str]) -> serde_json::Value {
    let mut alvo = format!(
        "/v1/ufs/{uf}/municipios?nome={}",
        utf8_percent_encode(termo, NON_ALPHANUMERIC)
    );
    for e in extra {
        alvo.push('&');
        alvo.push_str(e);
    }
    let r = a.get(&alvo, &[]).await;
    assert_eq!(r.status, 200, "{alvo}: {}", r.corpo);
    r.json()
}

#[tokio::test]
async fn busca_sem_acento_e_sem_caixa() {
    let a = Ambiente::novo().await;
    a.rj();
    for termo in ["niteroi", "NITERÓI", "  Niterói  "] {
        let corpo = buscar(&a, "RJ", termo, &[]).await;
        let dados = corpo["dados"].as_array().unwrap();
        assert_eq!(dados.len(), 1, "{termo:?}: {dados:?}");
        assert_eq!(
            (dados[0]["codigo"].as_str(), dados[0]["nome"].as_str()),
            (Some("3303302"), Some("Niterói")),
            "{termo:?}"
        );
    }
}

#[tokio::test]
async fn busca_com_varios_resultados_em_ordem_e_paginados() {
    let a = Ambiente::novo().await;
    a.sp();
    let tudo = buscar(&a, "SP", "são", &["itens=500"]).await;
    let todos = nomes(&tudo["dados"]);
    assert_eq!(
        tudo["paginacao"]["total"].as_u64(),
        Some(todos.len() as u64)
    );
    assert!(todos.len() > 10, "{} nomes", todos.len());
    assert!(todos.iter().any(|n| n == "São Paulo"));
    assert!(todos.iter().any(|n| n == "São José dos Campos"));
    let pagina = buscar(&a, "SP", "SAO", &["itens=10", "pagina=2"]).await;
    assert_eq!(
        nomes(&pagina["dados"]),
        todos[10..20],
        "a página 2 não é a continuação da lista ordenada"
    );
}

#[tokio::test]
async fn busca_sem_resultado() {
    let a = Ambiente::novo().await;
    a.rj();
    let corpo = buscar(&a, "RJ", "xyzw", &[]).await;
    assert_eq!(corpo["dados"], serde_json::json!([]));
    assert_eq!(
        corpo["paginacao"],
        serde_json::json!({"pagina": 1, "itens": 100, "total": 0, "paginas": 0})
    );
    let r = a.get("/v1/ufs/RJ/municipios?nome=xyzw", &[]).await;
    assert!(
        r.corpo.contains(r#""dados":[]"#),
        "lista vazia sai como [], e não como null"
    );
}

#[tokio::test]
async fn busca_invalida_e_400_sem_consultar() {
    let a = Ambiente::novo().await;
    let longo = "x".repeat(61);
    for (termo, trecho) in [
        ("a", "pelo menos 2"),
        ("  a  ", "pelo menos 2"),
        ("", "pelo menos 2"),
        (longo.as_str(), "no máximo 60"),
    ] {
        let alvo = format!(
            "/v1/ufs/RJ/municipios?nome={}",
            utf8_percent_encode(termo, NON_ALPHANUMERIC)
        );
        let r = a.get(&alvo, &[]).await;
        let p = conferir_problema(
            r.status,
            &r.tipo,
            &r.correlacao,
            &r.corpo,
            400,
            "entrada-invalida",
        );
        let detalhe = p["detail"].as_str().unwrap();
        assert!(detalhe.contains(trecho), "{termo:?}: {detalhe}");
    }
    assert_eq!(a.ibge.total(), 0, "busca inválida não consulta o IBGE");
}

#[tokio::test]
async fn duas_buscas_na_mesma_uf_fazem_uma_consulta() {
    let a = Ambiente::novo().await;
    a.rj();
    buscar(&a, "RJ", "niteroi", &[]).await;
    buscar(&a, "rj", "são", &[]).await;
    assert_eq!(a.get("/v1/ufs/33/municipios", &[]).await.status, 200);
    assert_eq!(a.ibge.pedidos("/estados/33/municipios"), 1);
}

/// T046 do E4: nome com codificação inválida, enviado cru, é 400 entrada-invalida, nunca 500.
#[tokio::test]
async fn nome_mal_codificado_e_400() {
    let a = Ambiente::novo().await;
    a.rj();
    for consulta in ["nome=%ZZ", "nome=s%E3o", "nome=%"] {
        let r = a
            .cru(
                &format!("/v1/ufs/RJ/municipios?{consulta}"),
                &["X-Correlation-Id: nome-1"],
            )
            .await;
        conferir_problema(
            r.status,
            r.cabecalho("content-type"),
            r.cabecalho("x-correlation-id"),
            &r.corpo,
            400,
            "entrada-invalida",
        );
    }
    assert_eq!(a.ibge.total(), 0, "nome mal codificado não consulta o IBGE");
}

//! US2, com os casos do test_api_municipio.py do E1 e do municipio_test.go do E7, mais a lição da T044.

mod apoio;

use apoio::{Ambiente, Resposta, conferir_meta, conferir_problema};

#[tokio::test]
async fn municipio_rio_de_janeiro() {
    let a = Ambiente::novo().await;
    a.ibge
        .responder_municipio("municipios-uf-33.json", "3304557");
    let r = a.get("/v1/municipios/3304557", &[]).await;
    assert_eq!(r.status, 200, "{}", r.corpo);
    let corpo = r.json();
    let d = &corpo["dados"];
    assert_eq!(
        (d["codigo"].as_str(), d["nome"].as_str()),
        (Some("3304557"), Some("Rio de Janeiro"))
    );
    assert_eq!(
        (d["uf"]["sigla"].as_str(), d["uf"]["codigo"].as_str()),
        (Some("RJ"), Some("33"))
    );
    assert_eq!(
        (
            d["regiao_imediata"]["codigo"].as_str(),
            d["regiao_intermediaria"]["codigo"].as_str()
        ),
        (Some("330001"), Some("3301"))
    );
    assert!(corpo.get("paginacao").is_none());
    conferir_meta(
        &corpo,
        &format!("{}/municipios/3304557", a.ibge.url()),
        false,
    );
}

#[tokio::test]
async fn municipio_inexistente_e_404_com_o_detalhe_do_e1() {
    let a = Ambiente::novo().await;
    a.ibge.responder("/municipios/9999999", Resposta::ok("[]"));
    let r = a.get("/v1/municipios/9999999", &[]).await;
    let p = conferir_problema(
        r.status,
        &r.tipo,
        &r.correlacao,
        &r.corpo,
        404,
        "nao-encontrado",
    );
    assert_eq!(p["detail"], "não existe município com o código 9999999");
}

#[tokio::test]
async fn codigo_mal_formado_e_400_sem_consultar() {
    let a = Ambiente::novo().await;
    for codigo in ["12ab", "123456", "12345678", "330455%EF%BC%97"] {
        let r = a.get(&format!("/v1/municipios/{codigo}"), &[]).await;
        conferir_problema(
            r.status,
            &r.tipo,
            &r.correlacao,
            &r.corpo,
            400,
            "entrada-invalida",
        );
    }
    assert_eq!(a.ibge.total(), 0);
}

#[tokio::test]
async fn nome_com_apostrofo_sem_escape() {
    let a = Ambiente::novo().await;
    a.ibge
        .responder_municipio("municipios-uf-35.json", "3545803");
    let r = a.get("/v1/municipios/3545803", &[]).await;
    assert!(
        r.corpo.contains(r#""nome":"Santa Bárbara d'Oeste""#),
        "{}",
        r.corpo
    );
}

#[tokio::test]
async fn municipio_sem_microrregiao_e_brasilia() {
    let a = Ambiente::novo().await;
    a.ibge
        .responder_fixture("/municipios/5101837", "municipio-5101837.json");
    a.ibge
        .responder_municipio("municipios-uf-53.json", "5300108");
    for (codigo, sigla) in [("5101837", "MT"), ("5300108", "DF")] {
        let r = a.get(&format!("/v1/municipios/{codigo}"), &[]).await;
        assert_eq!(
            (r.status, r.json()["dados"]["uf"]["sigla"].as_str()),
            (200, Some(sigla)),
            "{codigo}"
        );
    }
}

/// T044 do E4: caminho mal codificado sai em problem+json com correlação, nunca em texto ou HTML. Em Rust,
/// o hyper deixa o pedido chegar, e a rejeição do extrator Path vira o texto literal do segmento.
#[tokio::test]
async fn caminho_mal_codificado_e_problema_com_correlacao() {
    let a = Ambiente::novo().await;
    for alvo in [
        "/v1/municipios/%ZZ",
        "/v1/municipios/%",
        "/v1/municipios/%E3",
        "/v1/ufs/R%ZZ/municipios",
    ] {
        let r = a.cru(alvo, &["X-Correlation-Id: mal-codificado"]).await;
        let p = conferir_problema(
            r.status,
            r.cabecalho("content-type"),
            r.cabecalho("x-correlation-id"),
            &r.corpo,
            400,
            "entrada-invalida",
        );
        assert_eq!(p["correlacao_id"], "mal-codificado", "{alvo}");
    }
    // A barra codificada decodifica para "/", que não é um código de 7 dígitos: 400 (o E4 dava 400 ou 404).
    let r = a
        .cru("/v1/municipios/%2F", &["X-Correlation-Id: barra"])
        .await;
    assert!(r.status == 400 || r.status == 404, "%2F: {}", r.status);
    assert_eq!(r.cabecalho("content-type"), "application/problem+json");
    assert_eq!(a.ibge.total(), 0);
}

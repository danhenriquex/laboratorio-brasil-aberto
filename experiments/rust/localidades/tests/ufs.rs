//! US1, com os casos do test_api_ufs.py do E1 e do ufs_test.go do E7, mais as lições anteriores.

mod apoio;

use apoio::{Ambiente, Resposta, conferir_meta, conferir_problema, nomes};

#[tokio::test]
async fn lista_as_27_ufs_ordenadas() {
    let a = Ambiente::novo().await;
    a.estados();
    let r = a.get("/v1/ufs", &[]).await;
    assert_eq!((r.status, r.tipo.as_str()), (200, "application/json"));
    let corpo = r.json();
    assert!(corpo.get("paginacao").is_none(), "/v1/ufs não é paginada");
    let n = nomes(&corpo["dados"]);
    assert_eq!(
        (n.len(), n[0].as_str(), n[26].as_str()),
        (27, "Acre", "Tocantins")
    );
    let rj = &corpo["dados"][18];
    assert_eq!(
        (
            rj["sigla"].as_str(),
            rj["codigo"].as_str(),
            rj["regiao"]["sigla"].as_str()
        ),
        (Some("RJ"), Some("33"), Some("SE"))
    );
    conferir_meta(&corpo, &format!("{}/estados", a.ibge.url()), false);
}

#[tokio::test]
async fn uf_por_sigla_ou_codigo() {
    let a = Ambiente::novo().await;
    a.estados();
    for alvo in ["/v1/ufs/rj", "/v1/ufs/33", "/v1/ufs/%20RJ%20"] {
        let r = a.get(alvo, &[]).await;
        assert_eq!(r.status, 200, "{alvo}: {}", r.corpo);
        let corpo = r.json();
        assert_eq!(
            (
                corpo["dados"]["nome"].as_str(),
                corpo["dados"]["codigo"].as_str()
            ),
            (Some("Rio de Janeiro"), Some("33"))
        );
        assert!(
            corpo.get("paginacao").is_none(),
            "{alvo}: um recurso único não leva paginacao"
        );
    }
}

#[tokio::test]
async fn uf_inexistente_ou_mal_formada_sem_consultar_o_ibge() {
    let a = Ambiente::novo().await;
    for (alvo, status, tipo) in [
        ("/v1/ufs/XX", 404, "nao-encontrado"),
        ("/v1/ufs/99", 404, "nao-encontrado"),
        ("/v1/ufs/R1", 400, "entrada-invalida"),
        ("/v1/ufs/XX/municipios", 404, "nao-encontrado"),
        ("/v1/ufs/R1/municipios", 400, "entrada-invalida"),
    ] {
        let r = a.get(alvo, &[]).await;
        conferir_problema(r.status, &r.tipo, &r.correlacao, &r.corpo, status, tipo);
    }
    assert_eq!(a.ibge.total(), 0, "o IBGE não pode ser consultado");
}

#[tokio::test]
async fn municipios_do_rj() {
    let a = Ambiente::novo().await;
    a.rj();
    let r = a.get("/v1/ufs/RJ/municipios", &[]).await;
    assert_eq!(r.status, 200, "{}", r.corpo);
    let corpo = r.json();
    let n = nomes(&corpo["dados"]);
    assert_eq!((n.len(), n[0].as_str()), (92, "Angra dos Reis"));
    assert_eq!(
        corpo["paginacao"],
        serde_json::json!({"pagina": 1, "itens": 100, "total": 92, "paginas": 1})
    );
    conferir_meta(
        &corpo,
        &format!("{}/estados/33/municipios", a.ibge.url()),
        false,
    );
    assert!(
        r.corpo.starts_with(r#"{"dados":"#) && r.corpo.contains(r#"],"paginacao":{"#),
        "ordem dos campos: {:.80}",
        r.corpo
    );
    assert!(r.corpo.find(r#""paginacao""#) < r.corpo.find(r#""meta""#));
}

#[tokio::test]
async fn paginacao_e_alem_do_fim() {
    let a = Ambiente::novo().await;
    a.rj();
    assert_eq!(
        a.get("/v1/ufs/RJ/municipios?itens=10&pagina=10", &[])
            .await
            .json()["dados"]
            .as_array()
            .unwrap()
            .len(),
        2
    );
    let corpo = a
        .get("/v1/ufs/RJ/municipios?itens=10&pagina=11", &[])
        .await
        .json();
    assert!(corpo["dados"].as_array().unwrap().is_empty());
    assert_eq!(corpo["paginacao"]["total"], 92);
}

#[tokio::test]
async fn paginacao_invalida_e_400_com_o_limite() {
    let a = Ambiente::novo().await;
    a.rj();
    for (consulta, detalhe) in [
        ("itens=0", "itens precisa estar entre 1 e 500, recebi 0"),
        ("itens=501", "itens precisa estar entre 1 e 500, recebi 501"),
        (
            "pagina=0",
            "pagina precisa ser maior ou igual a 1, recebi 0",
        ),
        (
            "itens=1.5",
            "itens precisa ser um número inteiro, recebi '1.5'",
        ),
        (
            "pagina=x",
            "pagina precisa ser um número inteiro, recebi 'x'",
        ),
    ] {
        let r = a
            .get(&format!("/v1/ufs/RJ/municipios?{consulta}"), &[])
            .await;
        let p = conferir_problema(
            r.status,
            &r.tipo,
            &r.correlacao,
            &r.corpo,
            400,
            "entrada-invalida",
        );
        assert_eq!(p["detail"], detalhe, "{consulta}");
    }
    assert_eq!(a.ibge.total(), 0, "entrada inválida não consulta o IBGE");
}

/// T045 do E4: o contrato não limita pagina, e parâmetro repetido vale o último, como no E1.
#[tokio::test]
async fn pagina_enorme_e_parametro_repetido() {
    let a = Ambiente::novo().await;
    a.rj();
    let corpo = a
        .get("/v1/ufs/RJ/municipios?pagina=99999999999", &[])
        .await
        .json();
    assert!(corpo["dados"].as_array().unwrap().is_empty());
    assert_eq!(
        (
            corpo["paginacao"]["pagina"].as_i64(),
            corpo["paginacao"]["total"].as_i64()
        ),
        (Some(99999999999), Some(92))
    );
    let r = a
        .get(
            &format!("/v1/ufs/RJ/municipios?pagina={}", "9".repeat(30)),
            &[],
        )
        .await;
    assert_eq!(r.status, 200, "{}", r.corpo);
    assert!(r.json()["dados"].as_array().unwrap().is_empty());
    let corpo = a
        .get("/v1/ufs/RJ/municipios?itens=10&itens=20", &[])
        .await
        .json();
    assert_eq!(
        (
            corpo["paginacao"]["itens"].as_i64(),
            corpo["dados"].as_array().unwrap().len()
        ),
        (Some(20), 20)
    );
}

/// T046 do E4: query mal codificada é erro do pedido (400), nunca 500.
#[tokio::test]
async fn query_mal_codificada_e_400() {
    let a = Ambiente::novo().await;
    a.rj();
    for consulta in ["itens=%ZZ", "pagina=%E3", "itens=%"] {
        let r = a
            .cru(
                &format!("/v1/ufs/RJ/municipios?{consulta}"),
                &["X-Correlation-Id: query-1"],
            )
            .await;
        let p = conferir_problema(
            r.status,
            r.cabecalho("content-type"),
            r.cabecalho("x-correlation-id"),
            &r.corpo,
            400,
            "entrada-invalida",
        );
        assert!(
            p["detail"]
                .as_str()
                .unwrap()
                .contains("codificação inválida"),
            "{consulta}: {}",
            p["detail"]
        );
    }
    assert_eq!(a.ibge.total(), 0);
}

/// T048 do E4: o Accept não muda o formato.
#[tokio::test]
async fn accept_nao_muda_o_formato_da_lista() {
    let a = Ambiente::novo().await;
    a.estados();
    for aceita in ["application/xml", "text/html", "application/problem+json"] {
        let r = a.get("/v1/ufs", &[("Accept", aceita)]).await;
        assert_eq!(
            (r.status, r.tipo.as_str()),
            (200, "application/json"),
            "Accept {aceita}"
        );
    }
}

/// T050 do E4: com ";" no caminho, a rota não casa (ou a UF é recusada), e o IBGE não é consultado.
#[tokio::test]
async fn parametro_de_caminho_nao_devolve_dados() {
    let a = Ambiente::novo().await;
    a.estados();
    a.rj();
    for (alvo, status) in [
        ("/v1/ufs;jsessionid=x", 404),
        ("/v1/ufs/RJ;x=1/municipios", 400),
        ("/v1/ufs/RJ/municipios;x", 404),
    ] {
        let r = a.cru(alvo, &["X-Correlation-Id: pv-1"]).await;
        let tipo = if status == 404 {
            "nao-encontrado"
        } else {
            "entrada-invalida"
        };
        conferir_problema(
            r.status,
            r.cabecalho("content-type"),
            r.cabecalho("x-correlation-id"),
            &r.corpo,
            status,
            tipo,
        );
    }
    assert_eq!(a.ibge.total(), 0);
}

#[tokio::test]
async fn json_sem_escape_html() {
    let a = Ambiente::novo().await;
    a.ibge.responder(
        "/estados/33/municipios",
        Resposta::ok(r#"[{"id": 3300100, "nome": "A <&> B"}]"#),
    );
    let r = a.get("/v1/ufs/RJ/municipios", &[]).await;
    assert!(r.corpo.contains(r#""nome":"A <&> B""#), "{}", r.corpo);
}

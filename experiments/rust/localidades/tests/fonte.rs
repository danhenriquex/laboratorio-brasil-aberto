//! Cliente do IBGE contra o IBGE simulado, espelhando o test_fonte_ibge.py do E1 e o ibge_test.go do E7.

mod apoio;

use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use apoio::{Ibge, Resposta, fixture};
use localidades::fonte::{Cliente, USER_AGENT};

/// Uma alteração na primeira UF da fixture.
type Mudanca = fn(&mut serde_json::Value);

fn cliente(ibge: &Ibge, prazo: Duration) -> (Cliente, Arc<Mutex<Vec<String>>>) {
    let medidos = Arc::new(Mutex::new(Vec::new()));
    let m = medidos.clone();
    let medir = Arc::new(move |recurso: &str, _s: f64| m.lock().unwrap().push(recurso.to_string()));
    (Cliente::novo(&ibge.url(), prazo, Some(medir)), medidos)
}

#[tokio::test]
async fn classificacao_das_falhas() {
    let ibge = Ibge::novo().await;
    let html = Resposta {
        tipo: "text/html",
        ..Resposta::ok(fixture("erro.html"))
    };
    let casos = [
        ("503", Resposta::status(503, "fora"), "fonte-indisponivel"),
        ("429", Resposta::status(429, "calma"), "fonte-indisponivel"),
        (
            "404",
            Resposta::status(404, "[]"),
            "resposta-inesperada-da-fonte",
        ),
        (
            "301",
            Resposta::status(301, ""),
            "resposta-inesperada-da-fonte",
        ),
        ("HTML com 200", html, "resposta-inesperada-da-fonte"),
        (
            "JSON sem campo",
            Resposta::ok(fixture("estados-sem-regiao.json")),
            "resposta-inesperada-da-fonte",
        ),
        (
            "lista vazia",
            Resposta::ok("[]"),
            "resposta-inesperada-da-fonte",
        ),
    ];
    for (nome, resposta, tipo) in casos {
        ibge.responder("/estados", resposta);
        let (c, _) = cliente(&ibge, Duration::from_secs(1));
        let erro = c.estados().await.expect_err(nome);
        assert_eq!(erro.tipo, tipo, "{nome}: {erro}");
        assert!(
            !erro.detalhe.contains("Página de erro"),
            "{nome}: o corpo do IBGE vazou"
        );
    }
}

#[tokio::test]
async fn conexao_recusada_e_fonte_indisponivel() {
    // Uma porta livre em que ninguém escuta.
    let ouvinte = std::net::TcpListener::bind("127.0.0.1:0").unwrap();
    let endereco = ouvinte.local_addr().unwrap();
    drop(ouvinte);
    let c = Cliente::novo(
        &format!("http://{endereco}/api/v1/localidades"),
        Duration::from_secs(1),
        None,
    );
    let erro = c.estados().await.unwrap_err();
    assert_eq!(
        (erro.tipo, erro.detalhe.as_str()),
        ("fonte-indisponivel", "não foi possível conectar ao IBGE")
    );
}

#[tokio::test]
async fn prazo_total_e_fonte_lenta() {
    let ibge = Ibge::novo().await;
    ibge.responder(
        "/estados",
        Resposta {
            atraso: Duration::from_millis(300),
            ..Resposta::ok(fixture("estados.json"))
        },
    );
    let (c, medidos) = cliente(&ibge, Duration::from_millis(50));
    let inicio = Instant::now();
    let erro = c.estados().await.unwrap_err();
    assert_eq!(
        (erro.tipo, erro.detalhe.as_str()),
        ("fonte-lenta", "o IBGE não respondeu em 0.05 s")
    );
    assert!(
        inicio.elapsed() < Duration::from_millis(300),
        "o prazo não foi respeitado: {:?}",
        inicio.elapsed()
    );
    assert_eq!(
        *medidos.lock().unwrap(),
        ["estados"],
        "a duração é medida também na falha"
    );
}

#[tokio::test]
async fn normalizacao_das_ufs() {
    let ibge = Ibge::novo().await;
    ibge.responder_fixture("/estados", "estados.json");
    let (c, medidos) = cliente(&ibge, Duration::from_secs(1));
    let (ufs, url) = c.estados().await.unwrap();
    assert_eq!((ufs.len(), url), (27, format!("{}/estados", ibge.url())));
    let ro = &ufs[0];
    assert_eq!(
        (ro.codigo.as_str(), ro.sigla.as_str(), ro.nome.as_str()),
        ("11", "RO", "Rondônia")
    );
    assert_eq!(
        (ro.regiao.codigo.as_str(), ro.regiao.sigla.as_str()),
        ("1", "N")
    );
    assert_eq!(
        ibge.pedidos("/estados"),
        1,
        "exatamente 1 pedido por chamada"
    );
    assert_eq!(ibge.user_agent(), USER_AGENT);
    assert_eq!(medidos.lock().unwrap().len(), 1);
}

#[tokio::test]
async fn normalizacao_dos_municipios_da_uf() {
    let ibge = Ibge::novo().await;
    ibge.responder_fixture("/estados/33/municipios", "municipios-uf-33.json");
    let (c, _) = cliente(&ibge, Duration::from_secs(1));
    let (municipios, _) = c.municipios_da_uf("33").await.unwrap();
    assert_eq!(municipios.len(), 92);
    assert_eq!(
        (municipios[0].codigo.as_str(), municipios[0].nome.as_str()),
        ("3300100", "Angra dos Reis")
    );
}

#[tokio::test]
async fn municipio_objeto_ou_lista_de_um_e_sem_microrregiao() {
    let ibge = Ibge::novo().await;
    let objeto = fixture("municipio-5101837.json");
    let lista = [b"[".as_slice(), &objeto, b"]"].concat();
    for (nome, corpo) in [("objeto", objeto), ("lista de 1", lista)] {
        ibge.responder("/municipios/5101837", Resposta::ok(corpo));
        let (c, _) = cliente(&ibge, Duration::from_secs(1));
        let (m, _) = c
            .municipio("5101837")
            .await
            .unwrap_or_else(|e| panic!("{nome}: {e}"));
        assert_eq!(m.nome, "Boa Esperança do Norte", "{nome}");
        assert_eq!(
            (
                m.uf.sigla.as_str(),
                m.regiao_imediata.codigo.as_str(),
                m.regiao_intermediaria.codigo.as_str()
            ),
            ("MT", "510008", "5103")
        );
    }
}

#[tokio::test]
async fn municipio_inexistente_sem_regiao_imediata_e_outro_municipio() {
    let ibge = Ibge::novo().await;
    let (c, _) = cliente(&ibge, Duration::from_secs(1));
    ibge.responder("/municipios/9999999", Resposta::ok("[]"));
    let erro = c.municipio("9999999").await.unwrap_err();
    assert_eq!(
        (erro.tipo, erro.detalhe.as_str()),
        (
            "nao-encontrado",
            "não existe município com o código 9999999"
        )
    );
    ibge.responder_fixture("/municipios/1100015", "municipio-sem-regiao-imediata.json");
    assert_eq!(
        c.municipio("1100015").await.unwrap_err().tipo,
        "resposta-inesperada-da-fonte"
    );
    ibge.responder_fixture("/municipios/5101838", "municipio-5101837.json");
    assert_eq!(
        c.municipio("5101838").await.unwrap_err().tipo,
        "resposta-inesperada-da-fonte"
    );
}

/// Formato exato de códigos e siglas (T048 e T049 do E1).
#[tokio::test]
async fn formato_exato_de_codigos_e_siglas() {
    let ibge = Ibge::novo().await;
    let (c, _) = cliente(&ibge, Duration::from_secs(1));
    let estados: Vec<serde_json::Value> = serde_json::from_slice(&fixture("estados.json")).unwrap();
    let mudancas: [(&str, Mudanca); 5] = [
        ("UF com id 1", |uf| uf["id"] = 1.into()),
        ("sigla minúscula", |uf| uf["sigla"] = "ro".into()),
        ("sigla com espaço", |uf| uf["sigla"] = "R O".into()),
        ("sigla de região longa", |uf| {
            uf["regiao"]["sigla"] = "Norte".into()
        }),
        ("id booleano", |uf| uf["id"] = true.into()),
    ];
    for (nome, mudar) in mudancas {
        let mut copia = estados.clone();
        mudar(&mut copia[0]);
        ibge.responder(
            "/estados",
            Resposta::ok(serde_json::to_vec(&copia).unwrap()),
        );
        assert_eq!(
            c.estados().await.unwrap_err().tipo,
            "resposta-inesperada-da-fonte",
            "{nome}"
        );
    }
    ibge.responder(
        "/estados/33/municipios",
        Resposta::ok(r#"[{"id": 33001, "nome": "Curto"}]"#),
    );
    assert_eq!(
        c.municipios_da_uf("33").await.unwrap_err().tipo,
        "resposta-inesperada-da-fonte"
    );
    let mut municipio: serde_json::Value =
        serde_json::from_slice(&fixture("municipio-5101837.json")).unwrap();
    municipio["regiao-imediata"]["id"] = 51000.into();
    ibge.responder(
        "/municipios/5101837",
        Resposta::ok(serde_json::to_vec(&municipio).unwrap()),
    );
    assert_eq!(
        c.municipio("5101837").await.unwrap_err().tipo,
        "resposta-inesperada-da-fonte"
    );
}

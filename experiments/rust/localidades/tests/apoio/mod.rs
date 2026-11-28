//! Apoio dos testes de integração: fixtures, relógio falso, IBGE simulado e pedido cru.
//! Nenhum teste fala com host externo (Constituição IV): o IBGE é sempre um servidor local, dentro do teste.
#![allow(dead_code)]

use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use axum::Router;
use axum::body::Body;
use axum::extract::{Request, State};
use axum::http::{HeaderMap, StatusCode, header};
use axum::response::{IntoResponse, Response};
use time::OffsetDateTime;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::sync::Notify;

/// A raiz do repositório: sobe a partir do crate até achar contracts/localidades.
pub fn raiz() -> PathBuf {
    let mut dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    loop {
        if dir.join("contracts/localidades").is_dir() {
            return dir;
        }
        assert!(dir.pop(), "não achei contracts/localidades acima do crate");
    }
}

/// Uma das gravações de contracts/localidades/fixtures-ibge, as mesmas das outras implementações.
pub fn fixture(nome: &str) -> Vec<u8> {
    std::fs::read(
        raiz()
            .join("contracts/localidades/fixtures-ibge")
            .join(nome),
    )
    .expect(nome)
}

/// Relógio falso: o instante começa em 2026-11-26T12:00:00.123Z e a fonte monotônica em zero.
#[derive(Clone)]
pub struct Relogio(Arc<Mutex<(OffsetDateTime, Duration)>>);

impl Relogio {
    pub fn novo() -> Self {
        let inicio = time::macros::datetime!(2026-11-26 12:00:00.123 UTC);
        Self(Arc::new(Mutex::new((inicio, Duration::ZERO))))
    }
    pub fn agora(&self) -> OffsetDateTime {
        self.0.lock().unwrap().0
    }
    pub fn monotonico(&self) -> Duration {
        self.0.lock().unwrap().1
    }
    pub fn avancar(&self, d: Duration) {
        let mut g = self.0.lock().unwrap();
        g.0 += d;
        g.1 += d;
    }
}

/// Resposta simulada de um caminho do IBGE.
#[derive(Clone)]
pub struct Resposta {
    pub status: u16,
    pub corpo: Vec<u8>,
    pub tipo: &'static str,
    pub atraso: Duration,
    /// Se houver, segura a resposta até `notify_waiters` (fonte "travada").
    pub bloquear: Option<Arc<Notify>>,
}

impl Resposta {
    pub fn ok(corpo: impl Into<Vec<u8>>) -> Self {
        Self {
            status: 200,
            corpo: corpo.into(),
            tipo: "application/json",
            atraso: Duration::ZERO,
            bloquear: None,
        }
    }
    pub fn status(status: u16, corpo: &str) -> Self {
        Self {
            status,
            ..Self::ok(corpo.as_bytes().to_vec())
        }
    }
}

#[derive(Default)]
struct Interno {
    respostas: HashMap<String, Resposta>,
    contagem: HashMap<String, usize>,
    user_agent: String,
}

/// Um servidor axum em 127.0.0.1, que responde pelos caminhos registrados e conta os pedidos.
#[derive(Clone)]
pub struct Ibge {
    pub endereco: String,
    interno: Arc<Mutex<Interno>>,
}

const PREFIXO: &str = "/api/v1/localidades";

impl Ibge {
    pub async fn novo() -> Self {
        let interno = Arc::new(Mutex::new(Interno::default()));
        let app = Router::new().fallback(atender).with_state(interno.clone());
        let ouvinte = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let endereco = ouvinte.local_addr().unwrap().to_string();
        tokio::spawn(async move { axum::serve(ouvinte, app).await.unwrap() });
        Self { endereco, interno }
    }

    /// A base que o serviço usa como LOCALIDADES_IBGE_URL.
    pub fn url(&self) -> String {
        format!("http://{}{PREFIXO}", self.endereco)
    }

    pub fn responder(&self, caminho: &str, resposta: Resposta) {
        self.interno
            .lock()
            .unwrap()
            .respostas
            .insert(caminho.to_string(), resposta);
    }

    pub fn responder_fixture(&self, caminho: &str, nome: &str) {
        self.responder(caminho, Resposta::ok(fixture(nome)));
    }

    /// Serve em /municipios/<codigo> o item de uma lista das fixtures, como o IBGE falso da suíte.
    pub fn responder_municipio(&self, lista: &str, codigo: &str) {
        let itens: Vec<serde_json::Value> = serde_json::from_slice(&fixture(lista)).unwrap();
        let item = itens
            .into_iter()
            .find(|m| m["id"].as_u64().map(|n| n.to_string()).as_deref() == Some(codigo))
            .expect(codigo);
        self.responder(
            &format!("/municipios/{codigo}"),
            Resposta::ok(serde_json::to_vec(&item).unwrap()),
        );
    }

    pub fn pedidos(&self, caminho: &str) -> usize {
        *self
            .interno
            .lock()
            .unwrap()
            .contagem
            .get(caminho)
            .unwrap_or(&0)
    }

    pub fn total(&self) -> usize {
        self.interno.lock().unwrap().contagem.values().sum()
    }

    pub fn user_agent(&self) -> String {
        self.interno.lock().unwrap().user_agent.clone()
    }
}

async fn atender(
    State(interno): State<Arc<Mutex<Interno>>>,
    headers: HeaderMap,
    req: Request,
) -> Response {
    let caminho = req
        .uri()
        .path()
        .strip_prefix(PREFIXO)
        .unwrap_or(req.uri().path())
        .to_string();
    let resposta = {
        let mut g = interno.lock().unwrap();
        *g.contagem.entry(caminho.clone()).or_default() += 1;
        g.user_agent = headers
            .get(header::USER_AGENT)
            .and_then(|v| v.to_str().ok())
            .unwrap_or("")
            .to_string();
        g.respostas.get(&caminho).cloned()
    };
    let Some(r) = resposta else {
        return (
            StatusCode::IM_A_TEAPOT,
            format!("caminho não simulado: {caminho}"),
        )
            .into_response();
    };
    if let Some(n) = &r.bloquear {
        n.notified().await;
    }
    if !r.atraso.is_zero() {
        tokio::time::sleep(r.atraso).await;
    }
    Response::builder()
        .status(r.status)
        .header(header::CONTENT_TYPE, r.tipo)
        .body(Body::from(r.corpo))
        .unwrap()
}

/// Resposta de um pedido escrito à mão: status, cabeçalhos (nomes em minúsculas), corpo e bytes brutos.
pub struct RespostaCrua {
    pub status: u16,
    pub cabecalhos: HashMap<String, String>,
    pub corpo: String,
    pub bruto: String,
}

impl RespostaCrua {
    pub fn cabecalho(&self, nome: &str) -> &str {
        self.cabecalhos
            .get(&nome.to_ascii_lowercase())
            .map(String::as_str)
            .unwrap_or("")
    }
    pub fn json(&self) -> serde_json::Value {
        serde_json::from_str(&self.corpo)
            .unwrap_or_else(|_| panic!("corpo não é JSON: {}", self.corpo))
    }
}

/// Escreve o pedido direto no socket, para caminho e query chegarem exatamente como escritos.
pub async fn pedido_cru(
    endereco: &str,
    metodo: &str,
    alvo: &str,
    cabecalhos: &[&str],
) -> RespostaCrua {
    let mut conexao = tokio::net::TcpStream::connect(endereco).await.unwrap();
    let mut pedido =
        format!("{metodo} {alvo} HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n");
    for c in cabecalhos {
        pedido.push_str(c);
        pedido.push_str("\r\n");
    }
    pedido.push_str("\r\n");
    conexao.write_all(pedido.as_bytes()).await.unwrap();
    let mut bruto = Vec::new();
    conexao.read_to_end(&mut bruto).await.unwrap();
    let bruto = String::from_utf8_lossy(&bruto).to_string();
    let (cabeca, corpo) = bruto.split_once("\r\n\r\n").unwrap_or((&bruto, ""));
    let mut linhas = cabeca.split("\r\n");
    let status = linhas
        .next()
        .unwrap()
        .split(' ')
        .nth(1)
        .unwrap()
        .parse()
        .unwrap();
    let cabecalhos: HashMap<String, String> = linhas
        .filter_map(|l| l.split_once(':'))
        .map(|(k, v)| (k.trim().to_ascii_lowercase(), v.trim().to_string()))
        .collect();
    let corpo = if cabecalhos.get("transfer-encoding").map(String::as_str) == Some("chunked") {
        sem_chunked(corpo)
    } else {
        corpo.to_string()
    };
    RespostaCrua {
        status,
        cabecalhos,
        corpo,
        bruto,
    }
}

fn sem_chunked(corpo: &str) -> String {
    let bytes = corpo.as_bytes();
    let mut saida = Vec::new();
    let mut i = 0;
    loop {
        let fim = i + bytes[i..].windows(2).position(|w| w == b"\r\n").unwrap();
        let tamanho =
            usize::from_str_radix(std::str::from_utf8(&bytes[i..fim]).unwrap().trim(), 16).unwrap();
        if tamanho == 0 {
            return String::from_utf8_lossy(&saida).to_string();
        }
        saida.extend_from_slice(&bytes[fim + 2..fim + 2 + tamanho]);
        i = fim + 2 + tamanho + 2;
    }
}

/// Sobe um roteador num servidor de verdade, em 127.0.0.1, e devolve o endereço.
pub async fn servir(app: Router) -> String {
    let ouvinte = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let endereco = ouvinte.local_addr().unwrap().to_string();
    tokio::spawn(async move { axum::serve(ouvinte, app).await.unwrap() });
    endereco
}

/// O serviço inteiro (cliente, serviço e roteador) contra o IBGE simulado, como o app de teste do E1.
pub struct Ambiente {
    pub ibge: Ibge,
    pub relogio: Relogio,
    pub app: Router,
}

impl Ambiente {
    pub async fn novo() -> Self {
        Self::com_prazo(Duration::from_secs(1)).await
    }

    pub async fn com_prazo(prazo: Duration) -> Self {
        let ibge = Ibge::novo().await;
        let relogio = Relogio::novo();
        let cliente = localidades::fonte::Cliente::novo(&ibge.url(), prazo, None);
        let (r1, r2) = (relogio.clone(), relogio.clone());
        let opcoes = localidades::servico::Opcoes {
            agora: Arc::new(move || r1.agora()),
            monotonico: Arc::new(move || r2.monotonico()),
            validade: Duration::from_secs(24 * 3600),
            itens_max: 500,
        };
        let servico = localidades::servico::Servico::novo(cliente, opcoes);
        let app = localidades::app(servico, localidades::topo::Topo::default());
        Self { ibge, relogio, app }
    }

    pub fn estados(&self) {
        self.ibge.responder_fixture("/estados", "estados.json");
    }
    pub fn rj(&self) {
        self.ibge
            .responder_fixture("/estados/33/municipios", "municipios-uf-33.json");
    }
    pub fn sp(&self) {
        self.ibge
            .responder_fixture("/estados/35/municipios", "municipios-uf-35.json");
    }

    /// Pedido pelo roteador, sem rede (`oneshot`).
    pub async fn get(&self, alvo: &str, cabecalhos: &[(&str, &str)]) -> Resp {
        use tower::ServiceExt;
        let mut req = axum::http::Request::builder().uri(alvo);
        for (k, v) in cabecalhos {
            req = req.header(*k, *v);
        }
        let r = self
            .app
            .clone()
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
        let (status, tipo, correlacao) = (
            r.status().as_u16(),
            cab("content-type"),
            cab("x-correlation-id"),
        );
        let bytes = axum::body::to_bytes(r.into_body(), usize::MAX)
            .await
            .unwrap();
        Resp {
            status,
            tipo,
            correlacao,
            corpo: String::from_utf8(bytes.to_vec()).unwrap(),
        }
    }

    /// Pedido cru num servidor de verdade, para caminho e query chegarem como escritos.
    pub async fn cru(&self, alvo: &str, cabecalhos: &[&str]) -> RespostaCrua {
        let endereco = servir(self.app.clone()).await;
        pedido_cru(&endereco, "GET", alvo, cabecalhos).await
    }
}

pub struct Resp {
    pub status: u16,
    pub tipo: String,
    pub correlacao: String,
    pub corpo: String,
}

impl Resp {
    pub fn json(&self) -> serde_json::Value {
        serde_json::from_str(&self.corpo)
            .unwrap_or_else(|_| panic!("corpo não é JSON: {}", self.corpo))
    }
}

/// O assert_problema do E1: status, tipo, problem+json e correlação no corpo e no cabeçalho.
pub fn conferir_problema(
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
    assert_eq!(
        p["type"],
        format!("urn:brasil-aberto:problema:{tipo}"),
        "corpo: {corpo}"
    );
    assert_eq!(p["status"], esperado);
    assert!(!p["detail"].as_str().unwrap_or("").is_empty());
    assert!(!correlacao.is_empty());
    assert_eq!(p["correlacao_id"], correlacao);
    p
}

/// O assert_meta do E1.
pub fn conferir_meta(corpo: &serde_json::Value, url_fonte: &str, desatualizado: bool) {
    let meta = &corpo["meta"];
    assert_eq!(meta["fonte"], "IBGE — API de localidades");
    assert_eq!(meta["url_fonte"], url_fonte);
    assert_eq!(
        meta["url_documentacao"],
        "https://servicodados.ibge.gov.br/api/docs/localidades"
    );
    assert_eq!(meta["desatualizado"], desatualizado);
    let c = meta["coletado_em"].as_str().unwrap_or("");
    assert!(
        c.len() == "2026-11-26T12:00:00.123Z".len() && c.ends_with('Z'),
        "coletado_em: {c}"
    );
}

pub fn nomes(dados: &serde_json::Value) -> Vec<String> {
    dados
        .as_array()
        .unwrap()
        .iter()
        .map(|d| d["nome"].as_str().unwrap().to_string())
        .collect()
}

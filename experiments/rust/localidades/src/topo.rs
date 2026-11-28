//! Camada de topo (research do E8, R3, atualizado depois da sondagem da T004).
//!
//! O hyper deixa chegar ao roteador tudo o que o contrato precisa tratar (`%ZZ`, `//`, `.`, `..`, `;` e
//! `OPTIONS *`), e o axum não limpa nem redireciona caminhos. O que foge do contrato é o roteador
//! responder 404 sem corpo e 405 para método não suportado. Esta camada põe a correlação e o formato em
//! toda resposta, e os *fallbacks* levam ao 404 nao-encontrado do contrato, como no E1.

use std::panic::AssertUnwindSafe;
use std::sync::Arc;
use std::time::{Duration, Instant};

use axum::Router;
use axum::extract::{MatchedPath, Request, State};
use axum::http::{HeaderValue, Method, Uri};
use axum::middleware::{self, Next};
use axum::response::{IntoResponse, Response};
use futures::FutureExt;
use percent_encoding::percent_decode_str;

use crate::erros::ErroDominio;
use crate::operacao::{CABECALHO_CORRELACAO, ESTADO, Estado, Metricas, correlacao_de};

/// Recebe cada pedido terminado, para métricas e registro (US5).
pub type Observador = Arc<dyn Fn(&Method, &Estado, u16, Duration) + Send + Sync>;

/// O status registrado quando o cliente desiste antes da resposta (a convenção do nginx, como no E7).
pub const CLIENTE_DESISTIU: u16 = 499;

#[derive(Clone, Default)]
pub struct Topo {
    pub observar: Option<Observador>,
    /// Com métricas, o roteador ganha o `GET /metrics`.
    pub metricas: Option<Arc<Metricas>>,
}

/// Quando o cliente desiste, o hyper descarta o futuro do pedido inteiro, inclusive esta camada, e nenhuma
/// linha depois do `await` roda. O `Drop` roda mesmo assim: se a resposta não saiu, o pedido é observado
/// com 499, sem contar como erro do serviço.
struct Guarda {
    observar: Option<Observador>,
    metodo: Method,
    estado: Arc<Estado>,
    inicio: Instant,
    respondido: bool,
}

impl Guarda {
    fn observar(&mut self, status: u16) {
        self.respondido = true;
        if let Some(observar) = &self.observar {
            observar(&self.metodo, &self.estado, status, self.inicio.elapsed());
        }
    }
}

impl Drop for Guarda {
    fn drop(&mut self) {
        if !self.respondido {
            self.observar(CLIENTE_DESISTIU);
        }
    }
}

/// Rota inexistente e método não suportado: o mesmo 404 do contrato, inclusive para TRACE, sem eco.
pub async fn nao_encontrado(uri: Uri) -> ErroDominio {
    let caminho = percent_decode_str(uri.path()).decode_utf8_lossy();
    ErroDominio::nao_encontrado(format!("a rota {caminho} não existe"))
}

/// Anota o modelo da rota (`/v1/municipios/{codigo}`) para as métricas e o registro. Roda só nas rotas que
/// casaram (`route_layer`), onde o `MatchedPath` existe.
async fn marcar_rota(caminho: MatchedPath, req: Request, next: Next) -> Response {
    if let Ok(estado) = ESTADO.try_with(Arc::clone) {
        estado.definir_rota(caminho.as_str());
    }
    next.run(req).await
}

async fn camada(State(topo): State<Topo>, req: Request, next: Next) -> Response {
    let inicio = Instant::now();
    let correlacao = correlacao_de(
        req.headers()
            .get(CABECALHO_CORRELACAO)
            .and_then(|v| v.to_str().ok()),
    );
    let estado = Arc::new(Estado::novo(correlacao.clone()));
    let mut guarda = Guarda {
        observar: topo.observar.clone(),
        metodo: req.method().clone(),
        estado: estado.clone(),
        inicio,
        respondido: false,
    };

    // Um panic vira 500 erro-interno, sem rastro, em vez de derrubar só a conexão.
    let resposta = ESTADO
        .scope(estado.clone(), async move {
            match AssertUnwindSafe(next.run(req)).catch_unwind().await {
                Ok(resposta) => resposta,
                Err(_) => ErroDominio::interno().into_response(),
            }
        })
        .await;

    let mut resposta = resposta;
    if let Ok(valor) = HeaderValue::from_str(&correlacao) {
        resposta.headers_mut().insert(CABECALHO_CORRELACAO, valor);
    }
    guarda.observar(resposta.status().as_u16());
    resposta
}

/// Põe a camada de topo e os *fallbacks* em volta das rotas.
pub fn com_camadas(rotas: Router, topo: Topo) -> Router {
    rotas
        .route_layer(middleware::from_fn(marcar_rota))
        .fallback(nao_encontrado)
        .method_not_allowed_fallback(nao_encontrado)
        .layer(middleware::from_fn_with_state(topo, camada))
}

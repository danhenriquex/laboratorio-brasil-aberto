//! E8 — serviço de localidades (IBGE) em Rust. O binário (`main.rs`) só monta e sobe; os módulos ficam
//! aqui para os testes de integração em `tests/`.

pub mod api;
pub mod cache;
pub mod config;
pub mod dominio;
pub mod erros;
pub mod fonte;
pub mod operacao;
pub mod servico;
pub mod topo;

use axum::Router;
use axum::routing::get;

use crate::servico::Servico;
use crate::topo::Topo;

/// O roteador completo do serviço, com a camada de topo.
pub fn app(servico: Servico, topo: Topo) -> Router {
    let mut rotas = Router::new()
        .route("/health", get(operacao::saude))
        .merge(api::rotas(servico));
    if let Some(metricas) = &topo.metricas {
        rotas = rotas.merge(
            Router::new()
                .route("/metrics", get(operacao::expor_metricas))
                .with_state(metricas.clone()),
        );
    }
    topo::com_camadas(rotas, topo)
}

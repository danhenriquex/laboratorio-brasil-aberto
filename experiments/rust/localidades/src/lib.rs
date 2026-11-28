//! E8 — serviço de localidades (IBGE) em Rust. O binário (`main.rs`) só monta e sobe; os módulos ficam
//! aqui para os testes de integração em `tests/`.

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
pub fn app(_servico: Servico, topo: Topo) -> Router {
    let rotas = Router::new().route("/health", get(operacao::saude));
    topo::com_camadas(rotas, topo)
}

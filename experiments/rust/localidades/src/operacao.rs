//! O que é da operação do serviço: correlação, estado do pedido e saúde (US5 do E1; research do E8, R12).
//! Métricas e registro entram na US5.

use std::sync::{Arc, Mutex};

use axum::http::header;
use axum::response::IntoResponse;

pub const CABECALHO_CORRELACAO: &str = "x-correlation-id";

/// Aplica a regra do R12 do E1: aceita de 1 a 64 caracteres em [A-Za-z0-9._-]; senão, gera um UUID v4.
pub fn correlacao_de(valor: Option<&str>) -> String {
    match valor {
        Some(v)
            if !v.is_empty()
                && v.len() <= 64
                && v.bytes()
                    .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'.' | b'_' | b'-')) =>
        {
            v.to_string()
        }
        _ => gerar_correlacao(),
    }
}

pub fn gerar_correlacao() -> String {
    uuid::Uuid::new_v4().to_string()
}

#[derive(Debug, Default, Clone)]
pub struct Leitura {
    pub rota: String,
    pub cache: Option<&'static str>,
    pub tipo_erro: Option<&'static str>,
    pub fonte_s: Option<f64>,
}

/// O que o registro e as métricas precisam saber de um pedido. Viaja num `task_local` do tokio, posto pela
/// camada de topo, e é levado junto para a tarefa da consulta ao IBGE.
#[derive(Debug)]
pub struct Estado {
    pub correlacao: String,
    interno: Mutex<Leitura>,
}

impl Estado {
    pub fn novo(correlacao: String) -> Self {
        Self {
            correlacao,
            interno: Mutex::new(Leitura {
                rota: "nao-encontrado".into(),
                ..Leitura::default()
            }),
        }
    }

    fn com<R>(&self, f: impl FnOnce(&mut Leitura) -> R) -> R {
        f(&mut self.interno.lock().unwrap_or_else(|e| e.into_inner()))
    }

    pub fn definir_rota(&self, rota: &str) {
        self.com(|l| l.rota = rota.to_string());
    }

    pub fn definir_cache(&self, resultado: &'static str) {
        self.com(|l| l.cache = Some(resultado));
    }

    pub fn definir_tipo_erro(&self, tipo: &'static str) {
        self.com(|l| l.tipo_erro = Some(tipo));
    }

    /// Acumula o tempo de uma consulta ao IBGE feita por este pedido.
    pub fn somar_fonte(&self, segundos: f64) {
        self.com(|l| l.fonte_s = Some(l.fonte_s.unwrap_or(0.0) + segundos));
    }

    pub fn leitura(&self) -> Leitura {
        self.com(|l| l.clone())
    }
}

tokio::task_local! {
    pub static ESTADO: Arc<Estado>;
}

/// O estado do pedido em andamento, se houver um.
pub fn estado_atual() -> Option<Arc<Estado>> {
    ESTADO.try_with(Arc::clone).ok()
}

/// GET /health: {"status":"ok"}, sempre em application/json, qualquer que seja o Accept.
pub async fn saude() -> impl IntoResponse {
    (
        [(header::CONTENT_TYPE, "application/json")],
        r#"{"status":"ok"}"#,
    )
}

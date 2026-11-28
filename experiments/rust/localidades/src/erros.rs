//! Erros de domínio e seus tipos de problema (RFC 9457), com os mesmos tipos, títulos e status do E1
//! (research do E1, R11; data-model do E8).

use axum::http::{StatusCode, header};
use axum::response::{IntoResponse, Response};
use serde::Serialize;

use crate::operacao::{estado_atual, gerar_correlacao};

pub const PREFIXO_URN: &str = "urn:brasil-aberto:problema:";

/// Um erro que o serviço sabe classificar. Rust não tem exceções: o erro é um valor que o `?` propaga, e o
/// `IntoResponse` o converte em application/problem+json.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ErroDominio {
    pub tipo: &'static str,
    pub titulo: &'static str,
    pub status: StatusCode,
    pub detalhe: String,
}

impl ErroDominio {
    fn novo(
        tipo: &'static str,
        titulo: &'static str,
        status: StatusCode,
        detalhe: impl Into<String>,
    ) -> Self {
        Self {
            tipo,
            titulo,
            status,
            detalhe: detalhe.into(),
        }
    }

    pub fn entrada_invalida(detalhe: impl Into<String>) -> Self {
        Self::novo(
            "entrada-invalida",
            "Entrada inválida",
            StatusCode::BAD_REQUEST,
            detalhe,
        )
    }

    pub fn nao_encontrado(detalhe: impl Into<String>) -> Self {
        Self::novo(
            "nao-encontrado",
            "Não encontrado",
            StatusCode::NOT_FOUND,
            detalhe,
        )
    }

    pub fn fonte_indisponivel(detalhe: impl Into<String>) -> Self {
        Self::novo(
            "fonte-indisponivel",
            "Fonte indisponível",
            StatusCode::BAD_GATEWAY,
            detalhe,
        )
    }

    pub fn fonte_lenta(detalhe: impl Into<String>) -> Self {
        Self::novo(
            "fonte-lenta",
            "Fonte lenta",
            StatusCode::GATEWAY_TIMEOUT,
            detalhe,
        )
    }

    pub fn resposta_inesperada(detalhe: impl Into<String>) -> Self {
        Self::novo(
            "resposta-inesperada-da-fonte",
            "Resposta inesperada da fonte",
            StatusCode::BAD_GATEWAY,
            detalhe,
        )
    }

    /// O 500 tem sempre o mesmo detalhe genérico, sem rastro de execução (FR-013 do E1).
    pub fn interno() -> Self {
        Self::novo(
            "erro-interno",
            "Erro interno do serviço",
            StatusCode::INTERNAL_SERVER_ERROR,
            "erro interno do serviço",
        )
    }

    pub fn urn(&self) -> String {
        format!("{PREFIXO_URN}{}", self.tipo)
    }

    /// Se o erro veio do IBGE (o equivalente ao ERROS_DE_FONTE do E1).
    pub fn de_fonte(&self) -> bool {
        matches!(
            self.tipo,
            "fonte-indisponivel" | "fonte-lenta" | "resposta-inesperada-da-fonte"
        )
    }
}

impl std::fmt::Display for ErroDominio {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.detalhe)
    }
}

impl std::error::Error for ErroDominio {}

/// O corpo do problema, com os campos na ordem do E1: type, title, status, detail, correlacao_id.
#[derive(Serialize)]
struct Problema<'a> {
    #[serde(rename = "type")]
    tipo: String,
    title: &'a str,
    status: u16,
    detail: &'a str,
    correlacao_id: String,
}

impl IntoResponse for ErroDominio {
    fn into_response(self) -> Response {
        // A correlação e o tipo de erro vêm do estado do pedido, que a camada de topo põe no contexto da tarefa.
        let correlacao = match estado_atual() {
            Some(estado) => {
                estado.definir_tipo_erro(self.tipo);
                estado.correlacao.clone()
            }
            None => gerar_correlacao(),
        };
        let corpo = Problema {
            tipo: self.urn(),
            title: self.titulo,
            status: self.status.as_u16(),
            detail: &self.detalhe,
            correlacao_id: correlacao,
        };
        let json = serde_json::to_vec(&corpo).unwrap_or_else(|_| b"{}".to_vec());
        (
            self.status,
            [(header::CONTENT_TYPE, "application/problem+json")],
            json,
        )
            .into_response()
    }
}

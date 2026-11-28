//! Casos de uso do serviço de localidades. Não depende do axum (portas e adaptadores, como nas outras).

use std::sync::Arc;
use std::time::Duration;

use serde::Serialize;
use time::OffsetDateTime;

use crate::dominio::{Municipio, MunicipioResumido, Paginacao, Uf};
use crate::erros::ErroDominio;
use crate::fonte::Cliente;

pub const FONTE: &str = "IBGE — API de localidades";
pub const URL_DOCUMENTACAO: &str = "https://servicodados.ibge.gov.br/api/docs/localidades";

/// ISO 8601 em UTC, sempre com milissegundos e o sufixo Z (data-model, Meta).
pub fn formatar_momento(momento: OffsetDateTime) -> String {
    let t = momento.to_offset(time::UtcOffset::UTC);
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.{:03}Z",
        t.year(),
        u8::from(t.month()),
        t.day(),
        t.hour(),
        t.minute(),
        t.second(),
        t.millisecond()
    )
}

/// A procedência de toda resposta (Constituição II), com os campos na ordem do contrato.
#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct Meta {
    pub fonte: &'static str,
    pub url_fonte: String,
    pub url_documentacao: &'static str,
    pub coletado_em: String,
    pub desatualizado: bool,
}

impl Meta {
    pub fn nova(url_fonte: String, coletado_em: OffsetDateTime, desatualizado: bool) -> Self {
        Self {
            fonte: FONTE,
            url_fonte,
            url_documentacao: URL_DOCUMENTACAO,
            coletado_em: formatar_momento(coletado_em),
            desatualizado,
        }
    }
}

/// Os três recursos do IBGE que o serviço guarda, compartilhados sem cópias profundas.
#[derive(Debug, Clone)]
pub enum Dados {
    Ufs(Arc<Vec<Uf>>),
    Municipios(Arc<Vec<MunicipioResumido>>),
    Municipio(Arc<Municipio>),
}

/// O que um caso de uso devolve ao adaptador HTTP. `cache` é acerto, falta ou desatualizado.
#[derive(Debug, Clone)]
pub struct Resultado<T> {
    pub dados: T,
    pub meta: Meta,
    pub paginacao: Option<Paginacao>,
    pub cache: &'static str,
}

pub type Agora = Arc<dyn Fn() -> OffsetDateTime + Send + Sync>;
pub type Monotonico = Arc<dyn Fn() -> Duration + Send + Sync>;

/// Opções da montagem. Os relógios são injetáveis para os testes não esperarem de verdade.
#[derive(Clone)]
pub struct Opcoes {
    pub agora: Agora,
    pub monotonico: Monotonico,
    pub validade: Duration,
    pub itens_max: u32,
}

impl Opcoes {
    pub fn do_sistema(validade: Duration, itens_max: u32) -> Self {
        let inicio = std::time::Instant::now();
        Self {
            agora: Arc::new(OffsetDateTime::now_utc),
            monotonico: Arc::new(move || inicio.elapsed()),
            validade,
            itens_max,
        }
    }
}

#[derive(Clone)]
#[allow(dead_code)] // os campos passam a ser lidos na US1 (T017)
pub struct Servico {
    pub(crate) fonte: Cliente,
    pub(crate) opcoes: Opcoes,
}

/// Um recurso do IBGE já normalizado, com a procedência e o uso da cópia guardada.
#[allow(dead_code)] // usado a partir da US1 (T017)
pub(crate) struct Obtido {
    pub dados: Dados,
    pub meta: Meta,
    pub cache: &'static str,
}

impl Servico {
    pub fn novo(fonte: Cliente, opcoes: Opcoes) -> Self {
        Self { fonte, opcoes }
    }

    /// Chama a fonte direto. A cópia guardada e a consulta compartilhada entram na US3 (T027).
    #[allow(dead_code)] // usado a partir da US1 (T017)
    pub(crate) async fn obter<F>(&self, _chave: String, buscar: F) -> Result<Obtido, ErroDominio>
    where
        F: std::future::Future<Output = Result<(Dados, String), ErroDominio>> + Send + 'static,
    {
        let coletado_em = (self.opcoes.agora)();
        let (dados, url) = buscar.await?;
        Ok(Obtido {
            dados,
            meta: Meta::nova(url, coletado_em, false),
            cache: "falta",
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use time::macros::datetime;

    #[test]
    fn momento_com_milissegundos_e_z() {
        assert_eq!(
            formatar_momento(datetime!(2026-11-26 12:00:00 UTC)),
            "2026-11-26T12:00:00.000Z"
        );
        assert_eq!(
            formatar_momento(datetime!(2026-11-26 12:00:00.123456789 UTC)),
            "2026-11-26T12:00:00.123Z"
        );
        assert_eq!(
            formatar_momento(datetime!(2026-11-26 09:00:00.005 -3)),
            "2026-11-26T12:00:00.005Z"
        );
    }

    #[test]
    fn meta_com_a_procedencia() {
        let m = Meta::nova(
            "https://exemplo/estados".into(),
            datetime!(2026-11-26 12:00:00 UTC),
            true,
        );
        assert_eq!(m.fonte, "IBGE — API de localidades");
        assert_eq!(
            m.url_documentacao,
            "https://servicodados.ibge.gov.br/api/docs/localidades"
        );
        assert_eq!(
            (m.coletado_em.as_str(), m.desatualizado),
            ("2026-11-26T12:00:00.000Z", true)
        );
    }
}

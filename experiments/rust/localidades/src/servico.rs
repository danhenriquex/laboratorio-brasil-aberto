//! Casos de uso do serviço de localidades. Não depende do axum (portas e adaptadores, como nas outras).

use std::sync::Arc;
use std::time::Duration;

use serde::Serialize;
use time::OffsetDateTime;

use crate::dominio::{
    Municipio, MunicipioResumido, Paginacao, Uf, filtrar_por_nome, ordenar, paginar, resolver_uf,
    validar_codigo_municipio, validar_nome, validar_paginacao,
};
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
pub struct Servico {
    pub(crate) fonte: Cliente,
    pub(crate) opcoes: Opcoes,
}

/// Um recurso do IBGE já normalizado, com a procedência e o uso da cópia guardada.
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

// --- US1 ---

impl Servico {
    async fn estados(&self) -> Result<(Arc<Vec<Uf>>, Meta, &'static str), ErroDominio> {
        let fonte = self.fonte.clone();
        let o = self
            .obter("estados".into(), async move {
                let (ufs, url) = fonte.estados().await?;
                Ok((Dados::Ufs(Arc::new(ufs)), url))
            })
            .await?;
        match o.dados {
            Dados::Ufs(ufs) => Ok((ufs, o.meta, o.cache)),
            _ => Err(ErroDominio::interno()),
        }
    }

    /// As 27 UFs ordenadas por nome.
    pub async fn listar_ufs(&self) -> Result<Resultado<Vec<Uf>>, ErroDominio> {
        let (ufs, meta, cache) = self.estados().await?;
        Ok(Resultado {
            dados: ordenar(&ufs),
            meta,
            paginacao: None,
            cache,
        })
    }

    /// Resolve a sigla ou o código antes de consultar, para entrada inválida não chegar ao IBGE.
    pub async fn obter_uf(&self, param: &str) -> Result<Resultado<Uf>, ErroDominio> {
        let codigo = resolver_uf(param)?;
        let (ufs, meta, cache) = self.estados().await?;
        let uf = ufs
            .iter()
            .find(|u| u.codigo == codigo)
            .cloned()
            .ok_or_else(|| {
                ErroDominio::resposta_inesperada(format!(
                    "a UF {codigo} não veio na lista de UFs do IBGE"
                ))
            })?;
        Ok(Resultado {
            dados: uf,
            meta,
            paginacao: None,
            cache,
        })
    }

    /// Valida, resolve a UF, consulta, filtra pelo nome (se houver), ordena e pagina, na ordem do E1.
    pub async fn listar_municipios(
        &self,
        param_uf: &str,
        pagina: i64,
        itens: i64,
        nome: Option<&str>,
    ) -> Result<Resultado<Vec<MunicipioResumido>>, ErroDominio> {
        validar_paginacao(pagina, itens, self.opcoes.itens_max)?;
        let filtro = nome.map(validar_nome).transpose()?;
        let codigo = resolver_uf(param_uf)?;
        let fonte = self.fonte.clone();
        let c = codigo.clone();
        let o = self
            .obter(format!("estados/{codigo}/municipios"), async move {
                let (municipios, url) = fonte.municipios_da_uf(&c).await?;
                Ok((Dados::Municipios(Arc::new(municipios)), url))
            })
            .await?;
        let Dados::Municipios(municipios) = o.dados else {
            return Err(ErroDominio::interno());
        };
        let selecionados = match &filtro {
            Some(nome) => filtrar_por_nome(&municipios, nome),
            None => municipios.as_ref().clone(),
        };
        let p = paginar(&ordenar(&selecionados), pagina, itens as u32);
        Ok(Resultado {
            dados: p.itens,
            meta: o.meta,
            paginacao: Some(p.paginacao),
            cache: o.cache,
        })
    }
}

// --- US2 ---

impl Servico {
    /// Valida o código antes de consultar o IBGE.
    pub async fn obter_municipio(&self, codigo: &str) -> Result<Resultado<Municipio>, ErroDominio> {
        let codigo = validar_codigo_municipio(codigo)?;
        let fonte = self.fonte.clone();
        let c = codigo.clone();
        let o = self
            .obter(format!("municipios/{codigo}"), async move {
                let (municipio, url) = fonte.municipio(&c).await?;
                Ok((Dados::Municipio(Arc::new(municipio)), url))
            })
            .await?;
        let Dados::Municipio(municipio) = o.dados else {
            return Err(ErroDominio::interno());
        };
        Ok(Resultado {
            dados: municipio.as_ref().clone(),
            meta: o.meta,
            paginacao: None,
            cache: o.cache,
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

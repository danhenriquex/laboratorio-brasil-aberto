//! Cliente da API de localidades do IBGE: prazo total, classificação de falhas e normalização, com as regras
//! do E1 (R1, R6 e R7) e do research do E8 (R6). Uma chamada por consulta, sem nova tentativa. As mensagens
//! de erro nunca carregam o corpo devolvido pelo IBGE.

use std::sync::Arc;
use std::time::{Duration, Instant};

use reqwest::{StatusCode, header};
use serde_json::Value;

use crate::dominio::{
    Municipio, MunicipioResumido, Regiao, RegiaoImediata, RegiaoIntermediaria, Uf, UfResumida,
};
use crate::erros::ErroDominio;

pub const USER_AGENT: &str = "laboratorio-brasil-aberto-localidades/0.1.0";

/// Recebe a duração de cada consulta (recurso, segundos), inclusive das que falham.
pub type AoMedir = Arc<dyn Fn(&str, f64) + Send + Sync>;

#[derive(Clone)]
pub struct Cliente {
    base: String,
    prazo: Duration,
    ao_medir: Option<AoMedir>,
    http: reqwest::Client,
}

impl Cliente {
    pub fn novo(base: &str, prazo: Duration, ao_medir: Option<AoMedir>) -> Self {
        let http = reqwest::Client::builder()
            // Sem seguir redirecionamentos: um 3xx do IBGE é uma resposta inesperada.
            .redirect(reqwest::redirect::Policy::none())
            .build()
            .expect("cliente HTTP");
        Self {
            base: base.trim_end_matches('/').to_string(),
            prazo,
            ao_medir,
            http,
        }
    }

    pub fn url(&self, caminho: &str) -> String {
        format!("{}/{caminho}", self.base)
    }

    fn lenta(&self) -> ErroDominio {
        ErroDominio::fonte_lenta(format!(
            "o IBGE não respondeu em {} s",
            formatar_segundos(self.prazo)
        ))
    }

    /// Uma consulta com prazo total: o `timeout` cobre conexão, cabeçalhos e leitura do corpo.
    async fn buscar_json(
        &self,
        caminho: &str,
        recurso: &str,
    ) -> Result<(Value, String), ErroDominio> {
        let url = self.url(caminho);
        let inicio = Instant::now();
        let consulta = async {
            let resposta = self
                .http
                .get(&url)
                .header(header::USER_AGENT, USER_AGENT)
                .header(header::ACCEPT, "application/json")
                .send()
                .await?;
            let status = resposta.status();
            let corpo = resposta.bytes().await?;
            Ok::<_, reqwest::Error>((status, corpo))
        };
        let resultado = tokio::time::timeout(self.prazo, consulta).await;
        if let Some(medir) = &self.ao_medir {
            medir(recurso, inicio.elapsed().as_secs_f64());
        }
        let (status, corpo) = match resultado {
            Err(_) => return Err(self.lenta()),
            Ok(Err(e)) if e.is_timeout() => return Err(self.lenta()),
            Ok(Err(_)) => {
                return Err(ErroDominio::fonte_indisponivel(
                    "não foi possível conectar ao IBGE",
                ));
            }
            Ok(Ok(par)) => par,
        };
        if status.is_server_error() || status == StatusCode::TOO_MANY_REQUESTS {
            return Err(ErroDominio::fonte_indisponivel(format!(
                "o IBGE respondeu com status {}",
                status.as_u16()
            )));
        }
        if status != StatusCode::OK {
            return Err(ErroDominio::resposta_inesperada(format!(
                "o IBGE respondeu com status {}",
                status.as_u16()
            )));
        }
        let dados = serde_json::from_slice(&corpo).map_err(|_| {
            ErroDominio::resposta_inesperada("o IBGE respondeu um conteúdo que não é JSON")
        })?;
        Ok((dados, url))
    }

    /// As 27 UFs, na ordem em que o IBGE mandou.
    pub async fn estados(&self) -> Result<(Vec<Uf>, String), ErroDominio> {
        let (dados, url) = self.buscar_json("estados", "estados").await?;
        let ler = || -> Result<Vec<Uf>, Forma> {
            let itens = lista(&dados)?;
            if itens.is_empty() {
                return Err(Forma::new("lista de UFs vazia"));
            }
            itens.iter().map(ler_uf).collect()
        };
        let ufs = ler().map_err(|e| {
            ErroDominio::resposta_inesperada(format!(
                "a lista de UFs do IBGE veio fora do formato esperado ({e})"
            ))
        })?;
        Ok((ufs, url))
    }

    /// Os municípios de uma UF existente.
    pub async fn municipios_da_uf(
        &self,
        codigo_uf: &str,
    ) -> Result<(Vec<MunicipioResumido>, String), ErroDominio> {
        let (dados, url) = self
            .buscar_json(
                &format!("estados/{codigo_uf}/municipios"),
                "municipios_da_uf",
            )
            .await?;
        let ler = || -> Result<Vec<MunicipioResumido>, Forma> {
            let itens = lista(&dados)?;
            if itens.is_empty() {
                return Err(Forma::new("lista vazia para uma UF existente"));
            }
            itens.iter().map(ler_municipio_resumido).collect()
        };
        let municipios = ler().map_err(|e| {
            ErroDominio::resposta_inesperada(format!(
                "a lista de municípios da UF {codigo_uf} veio fora do formato esperado ({e})"
            ))
        })?;
        Ok((municipios, url))
    }

    /// Um município pelo código. "Não encontrado" no IBGE é uma lista vazia.
    pub async fn municipio(&self, codigo: &str) -> Result<(Municipio, String), ErroDominio> {
        let (dados, url) = self
            .buscar_json(&format!("municipios/{codigo}"), "municipio")
            .await?;
        let objeto = match &dados {
            Value::Array(l) if l.is_empty() => {
                return Err(ErroDominio::nao_encontrado(format!(
                    "não existe município com o código {codigo}"
                )));
            }
            Value::Array(l) if l.len() == 1 => &l[0],
            Value::Array(_) => {
                return Err(ErroDominio::resposta_inesperada(format!(
                    "o município {codigo} veio fora do formato esperado (esperava um único município)"
                )));
            }
            outro => outro,
        };
        let m = ler_municipio(objeto).map_err(|e| {
            ErroDominio::resposta_inesperada(format!(
                "o município {codigo} veio fora do formato esperado ({e})"
            ))
        })?;
        if m.codigo != codigo {
            return Err(ErroDominio::resposta_inesperada(format!(
                "o IBGE devolveu outro município ao pedir {codigo}"
            )));
        }
        Ok((m, url))
    }
}

/// Segundos como o `:g` do Python: 10, 1, 0.05.
fn formatar_segundos(d: Duration) -> String {
    let s = d.as_secs_f64();
    if s.fract() == 0.0 {
        format!("{}", s as u64)
    } else {
        format!("{s}")
    }
}

// --- leitura da forma descrita no data-model ---

/// A resposta do IBGE não tem a forma descrita no data-model.
#[derive(Debug)]
struct Forma(String);

impl Forma {
    fn new(msg: impl Into<String>) -> Self {
        Self(msg.into())
    }
}

impl std::fmt::Display for Forma {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

fn lista(dados: &Value) -> Result<&Vec<Value>, Forma> {
    dados
        .as_array()
        .ok_or_else(|| Forma::new("esperava uma lista"))
}

fn campo<'a>(objeto: &'a Value, chave: &str) -> Result<&'a Value, Forma> {
    match objeto.get(chave) {
        Some(v) if !v.is_null() => Ok(v),
        _ => Err(Forma(format!("campo obrigatório ausente: {chave}"))),
    }
}

/// Quantidade exata de dígitos: completar com zeros inventaria um código que o IBGE não publicou (T048 do E1).
fn codigo(objeto: &Value, digitos: usize) -> Result<String, Forma> {
    let texto = match campo(objeto, "id")? {
        Value::Number(n) => n.to_string(),
        Value::String(s) => s.trim().to_string(),
        _ => return Err(Forma::new("id com tipo inesperado")),
    };
    if texto.len() != digitos || !texto.bytes().all(|b| b.is_ascii_digit()) {
        return Err(Forma(format!("id fora do formato de {digitos} dígitos")));
    }
    Ok(texto)
}

fn texto(objeto: &Value, chave: &str) -> Result<String, Forma> {
    match campo(objeto, chave)? {
        Value::String(s) if !s.trim().is_empty() => Ok(s.clone()),
        _ => Err(Forma(format!("campo {chave} vazio ou não textual"))),
    }
}

/// Regras do data-model para as siglas expostas (T049 do E1): UF com 2 maiúsculas, região com 1 ou 2.
fn sigla(objeto: &Value, minimo: usize, maximo: usize) -> Result<String, Forma> {
    let valor = texto(objeto, "sigla")?;
    let ok =
        (minimo..=maximo).contains(&valor.len()) && valor.bytes().all(|b| b.is_ascii_uppercase());
    if !ok {
        return Err(Forma::new("sigla fora do formato esperado"));
    }
    Ok(valor)
}

fn ler_uf(objeto: &Value) -> Result<Uf, Forma> {
    let regiao = campo(objeto, "regiao")?;
    Ok(Uf {
        codigo: codigo(objeto, 2)?,
        sigla: sigla(objeto, 2, 2)?,
        nome: texto(objeto, "nome")?,
        regiao: Regiao {
            codigo: codigo(regiao, 1)?,
            sigla: sigla(regiao, 1, 2)?,
            nome: texto(regiao, "nome")?,
        },
    })
}

fn ler_municipio_resumido(objeto: &Value) -> Result<MunicipioResumido, Forma> {
    Ok(MunicipioResumido {
        codigo: codigo(objeto, 7)?,
        nome: texto(objeto, "nome")?,
    })
}

fn ler_municipio(objeto: &Value) -> Result<Municipio, Forma> {
    let imediata = campo(objeto, "regiao-imediata")?;
    let intermediaria = campo(imediata, "regiao-intermediaria")?;
    let uf = campo(intermediaria, "UF")?;
    Ok(Municipio {
        codigo: codigo(objeto, 7)?,
        nome: texto(objeto, "nome")?,
        uf: UfResumida {
            codigo: codigo(uf, 2)?,
            sigla: sigla(uf, 2, 2)?,
            nome: texto(uf, "nome")?,
        },
        regiao_imediata: RegiaoImediata {
            codigo: codigo(imediata, 6)?,
            nome: texto(imediata, "nome")?,
        },
        regiao_intermediaria: RegiaoIntermediaria {
            codigo: codigo(intermediaria, 4)?,
            nome: texto(intermediaria, "nome")?,
        },
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn segundos_como_o_g_do_python() {
        assert_eq!(formatar_segundos(Duration::from_secs(10)), "10");
        assert_eq!(formatar_segundos(Duration::from_millis(50)), "0.05");
        assert_eq!(formatar_segundos(Duration::from_millis(1500)), "1.5");
    }
}

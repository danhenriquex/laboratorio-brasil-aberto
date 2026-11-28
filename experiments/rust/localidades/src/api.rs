//! Adaptador HTTP das rotas v1: envelope, leitura da query e extração dos parâmetros do caminho.
//! O contrato é o openapi.yaml escrito à mão em contracts/localidades/; nada aqui gera OpenAPI.

use std::collections::HashMap;

use axum::extract::rejection::PathRejection;
use axum::extract::{Path, State};
use axum::http::Uri;
use axum::routing::get;
use axum::{Json, Router};
use percent_encoding::percent_decode_str;
use serde::Serialize;

use crate::dominio::{Paginacao, repr};
use crate::erros::ErroDominio;
use crate::operacao::estado_atual;
use crate::servico::{Meta, Resultado, Servico};

/// O envelope do contrato, com os campos na ordem do E1: dados, paginacao (só nas listas paginadas) e meta.
#[derive(Serialize)]
pub struct Resposta<T: Serialize> {
    dados: T,
    #[serde(skip_serializing_if = "Option::is_none")]
    paginacao: Option<Paginacao>,
    meta: Meta,
}

/// Escreve o envelope e anota o uso da cópia guardada para as métricas e o registro.
fn responder<T: Serialize>(r: Resultado<T>) -> Json<Resposta<T>> {
    if let Some(estado) = estado_atual() {
        estado.definir_cache(r.cache);
    }
    Json(Resposta {
        dados: r.dados,
        paginacao: r.paginacao,
        meta: r.meta,
    })
}

pub fn rotas(servico: Servico) -> Router {
    Router::new()
        .route("/v1/ufs", get(listar_ufs))
        .route("/v1/ufs/{uf}", get(obter_uf))
        .route("/v1/ufs/{uf}/municipios", get(listar_municipios))
        .route("/v1/municipios/{codigo}", get(obter_municipio))
        .with_state(servico)
}

/// O parâmetro do caminho. O extrator `Path` decodifica o segmento e recusaria `%ZZ` ou UTF-8 inválido com a
/// sua própria resposta; aqui a recusa vira o texto literal do segmento, que a validação do domínio recusa
/// como entrada inválida, como no E1 (lição da T044 do E4).
pub(crate) fn segmento(
    extraido: Result<Path<String>, PathRejection>,
    uri: &Uri,
    posicao: usize,
) -> String {
    match extraido {
        Ok(Path(valor)) => valor,
        Err(_) => {
            let cru = uri.path().split('/').nth(posicao).unwrap_or("");
            percent_decode_str(cru).decode_utf8_lossy().into_owned()
        }
    }
}

async fn listar_ufs(
    State(s): State<Servico>,
) -> Result<Json<Resposta<Vec<crate::dominio::Uf>>>, ErroDominio> {
    Ok(responder(s.listar_ufs().await?))
}

async fn obter_uf(
    State(s): State<Servico>,
    uri: Uri,
    uf: Result<Path<String>, PathRejection>,
) -> Result<Json<Resposta<crate::dominio::Uf>>, ErroDominio> {
    Ok(responder(s.obter_uf(&segmento(uf, &uri, 3)).await?))
}

async fn listar_municipios(
    State(s): State<Servico>,
    uri: Uri,
    uf: Result<Path<String>, PathRejection>,
) -> Result<Json<Resposta<Vec<crate::dominio::MunicipioResumido>>>, ErroDominio> {
    let consulta = Consulta::ler(&uri)?;
    let pagina = consulta.inteiro("pagina", 1)?;
    let itens = consulta.inteiro("itens", 100)?;
    let nome = consulta.ultimo("nome");
    Ok(responder(
        s.listar_municipios(&segmento(uf, &uri, 3), pagina, itens, nome)
            .await?,
    ))
}

async fn obter_municipio(
    State(s): State<Servico>,
    uri: Uri,
    codigo: Result<Path<String>, PathRejection>,
) -> Result<Json<Resposta<crate::dominio::Municipio>>, ErroDominio> {
    Ok(responder(
        s.obter_municipio(&segmento(codigo, &uri, 3)).await?,
    ))
}

/// Os parâmetros da query, lidos do texto cru (research R4). O extrator `Query` decodifica de forma
/// tolerante; aqui a codificação inválida é recusada e vale o último valor de um parâmetro repetido.
pub(crate) struct Consulta(HashMap<String, String>);

fn mal_codificada() -> ErroDominio {
    ErroDominio::entrada_invalida("os parâmetros da consulta têm codificação inválida")
}

fn decodificar(parte: &str) -> Result<String, ErroDominio> {
    let bytes = parte.as_bytes();
    // Um "%" só vale seguido de dois dígitos hexadecimais.
    for (i, b) in bytes.iter().enumerate() {
        let escape_valido = i + 2 < bytes.len()
            && bytes[i + 1].is_ascii_hexdigit()
            && bytes[i + 2].is_ascii_hexdigit();
        if *b == b'%' && !escape_valido {
            return Err(mal_codificada());
        }
    }
    let com_espacos = parte.replace('+', " ");
    percent_decode_str(&com_espacos)
        .decode_utf8()
        .map(|s| s.into_owned())
        .map_err(|_| mal_codificada())
}

impl Consulta {
    pub(crate) fn ler(uri: &Uri) -> Result<Self, ErroDominio> {
        let mut valores = HashMap::new();
        for par in uri
            .query()
            .unwrap_or("")
            .split('&')
            .filter(|p| !p.is_empty())
        {
            let (chave, valor) = par.split_once('=').unwrap_or((par, ""));
            valores.insert(decodificar(chave)?, decodificar(valor)?);
        }
        Ok(Self(valores))
    }

    /// O último valor de um parâmetro, se veio.
    pub(crate) fn ultimo(&self, nome: &str) -> Option<&str> {
        self.0.get(nome).map(String::as_str)
    }

    /// Lê um inteiro como o int() do Python: aceita espaços nas pontas e sinal; vazio ou ausente usa o
    /// padrão. Só dígitos, mas grande demais para i64, vale como o maior valor: para pagina, é uma página
    /// além do fim, e não um erro (T045 do E4). A faixa fica com o domínio, para o detalhe citar o limite.
    pub(crate) fn inteiro(&self, nome: &str, padrao: i64) -> Result<i64, ErroDominio> {
        let Some(bruto) = self.ultimo(nome) else {
            return Ok(padrao);
        };
        let valor = bruto.trim();
        if valor.is_empty() {
            return Ok(padrao);
        }
        if let Ok(n) = valor.parse::<i64>() {
            return Ok(n);
        }
        let (sinal, digitos) = match valor.strip_prefix('-') {
            Some(resto) => (-1, resto),
            None => (1, valor.strip_prefix('+').unwrap_or(valor)),
        };
        if !digitos.is_empty() && digitos.bytes().all(|b| b.is_ascii_digit()) {
            return Ok(if sinal < 0 { i64::MIN } else { i64::MAX });
        }
        Err(ErroDominio::entrada_invalida(format!(
            "{nome} precisa ser um número inteiro, recebi {}",
            repr(bruto)
        )))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn consulta(q: &str) -> Result<Consulta, ErroDominio> {
        Consulta::ler(&format!("/x?{q}").parse::<Uri>().unwrap())
    }

    #[test]
    fn ultimo_valor_e_mais_como_espaco() {
        let c = consulta("itens=10&itens=20&nome=sao+goncalo&vazio=").unwrap();
        assert_eq!(
            (c.ultimo("itens"), c.ultimo("nome"), c.ultimo("vazio")),
            (Some("20"), Some("sao goncalo"), Some(""))
        );
        assert_eq!(
            consulta("nome=s%C3%A3o").unwrap().ultimo("nome"),
            Some("são")
        );
    }

    #[test]
    fn codificacao_invalida_e_400() {
        for q in ["nome=%ZZ", "nome=%", "nome=%4", "nome=s%E3o", "%ZZ=1"] {
            assert_eq!(
                consulta(q).err().map(|e| e.tipo),
                Some("entrada-invalida"),
                "{q}"
            );
        }
    }

    #[test]
    fn inteiros_como_no_python() {
        let c =
            consulta("a=+5&b=%205%20&c=99999999999999999999999999&d=-99999999999999999999&e=1.5")
                .unwrap();
        assert_eq!(c.inteiro("a", 0).unwrap(), 5);
        assert_eq!(c.inteiro("b", 0).unwrap(), 5);
        assert_eq!(c.inteiro("c", 0).unwrap(), i64::MAX);
        assert_eq!(c.inteiro("d", 0).unwrap(), i64::MIN);
        assert_eq!(
            c.inteiro("e", 0).unwrap_err().detalhe,
            "e precisa ser um número inteiro, recebi '1.5'"
        );
        assert_eq!(c.inteiro("ausente", 7).unwrap(), 7);
    }
}

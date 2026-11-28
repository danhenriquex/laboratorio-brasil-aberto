//! Configuração pelas variáveis LOCALIDADES_*, comuns às quatro implementações, com os padrões do E1 (R14)
//! e as regras de validação do E4 e do E7 (research do E8, R11).

use std::time::Duration;

use crate::dominio::repr;

pub const IBGE_URL_PADRAO: &str = "https://servicodados.ibge.gov.br/api/v1/localidades";

/// Prazo e validade ficam entre 1 ms e 10⁹ s: abaixo disso o valor arredonda para zero, acima não cabe com
/// folga no relógio monotônico, e o infinito deixaria a consulta ao IBGE sem prazo (T049 do E4).
const SEGUNDOS_MIN: f64 = 0.001;
const SEGUNDOS_MAX: f64 = 1e9;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Configuracao {
    pub ibge_url: String,
    pub prazo_fonte: Duration,
    pub validade: Duration,
    pub itens_max: u32,
    pub host: String,
    pub porta: u16,
}

/// Lê a configuração por uma função como `std::env::var`. Um valor inválido impede a partida: o erro cita a
/// variável e o valor recebido, e o main acrescenta "configuração inválida:", como no E1.
pub fn carregar(getenv: impl Fn(&str) -> Option<String>) -> Result<Configuracao, String> {
    let bruto = |nome: &str| {
        getenv(nome)
            .map(|v| v.trim().to_string())
            .unwrap_or_default()
    };
    let texto = |nome: &str, padrao: &str| {
        let v = bruto(nome);
        if v.is_empty() { padrao.to_string() } else { v }
    };

    let ibge_url = texto("LOCALIDADES_IBGE_URL", IBGE_URL_PADRAO)
        .trim_end_matches('/')
        .to_string();
    if !ibge_url.starts_with("http://") && !ibge_url.starts_with("https://") {
        return Err(format!(
            "LOCALIDADES_IBGE_URL precisa começar com http:// ou https://, recebi {}",
            repr(&ibge_url)
        ));
    }
    let porta = inteiro(
        "LOCALIDADES_PORTA",
        &bruto("LOCALIDADES_PORTA"),
        8000,
        65535,
    )?;
    let itens_max = inteiro(
        "LOCALIDADES_ITENS_MAX",
        &bruto("LOCALIDADES_ITENS_MAX"),
        500,
        i32::MAX as u64,
    )?;
    Ok(Configuracao {
        ibge_url,
        prazo_fonte: segundos(
            "LOCALIDADES_PRAZO_FONTE_S",
            &bruto("LOCALIDADES_PRAZO_FONTE_S"),
            10.0,
        )?,
        validade: segundos(
            "LOCALIDADES_VALIDADE_S",
            &bruto("LOCALIDADES_VALIDADE_S"),
            86400.0,
        )?,
        itens_max: itens_max as u32,
        host: texto("LOCALIDADES_HOST", "127.0.0.1"),
        porta: porta as u16,
    })
}

fn inteiro(nome: &str, valor: &str, padrao: u64, maximo: u64) -> Result<u64, String> {
    if valor.is_empty() {
        return Ok(padrao);
    }
    let recebi = repr(valor);
    let n: i128 = valor
        .parse()
        .map_err(|_| format!("{nome} precisa ser um número inteiro, recebi {recebi}"))?;
    if n <= 0 {
        return Err(format!(
            "{nome} precisa ser maior que zero, recebi {recebi}"
        ));
    }
    if n > maximo as i128 {
        return Err(if maximo == 65535 {
            format!("{nome} precisa estar entre 1 e 65535, recebi {recebi}")
        } else {
            format!("{nome} precisa ser de no máximo {maximo}, recebi {recebi}")
        });
    }
    Ok(n as u64)
}

/// Aceita o que o `parse::<f64>()` aceita, mas recusa NaN e infinito, que ele também aceita ("NaN", "inf",
/// "infinity" e números como 1e400, que viram infinito).
fn segundos(nome: &str, valor: &str, padrao: f64) -> Result<Duration, String> {
    if valor.is_empty() {
        return Ok(Duration::from_secs_f64(padrao));
    }
    let recebi = repr(valor);
    let s: f64 = valor
        .parse()
        .map_err(|_| format!("{nome} precisa ser um número, recebi {recebi}"))?;
    if !s.is_finite() {
        return Err(format!(
            "{nome} precisa ser um número finito, recebi {recebi}"
        ));
    }
    if s <= 0.0 {
        return Err(format!(
            "{nome} precisa ser maior que zero, recebi {recebi}"
        ));
    }
    if s < SEGUNDOS_MIN {
        return Err(format!(
            "{nome} precisa ser de pelo menos 0.001 (1 ms), recebi {recebi}"
        ));
    }
    if s > SEGUNDOS_MAX {
        return Err(format!(
            "{nome} precisa ser de no máximo 1000000000 (10⁹ s), recebi {recebi}"
        ));
    }
    Ok(Duration::from_nanos((s * 1e9).round() as u64))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    fn ambiente(pares: &[(&str, &str)]) -> impl Fn(&str) -> Option<String> {
        let mapa: HashMap<String, String> = pares
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect();
        move |nome| mapa.get(nome).cloned()
    }

    #[test]
    fn padroes_do_e1() {
        let c = carregar(ambiente(&[])).unwrap();
        assert_eq!(
            c,
            Configuracao {
                ibge_url: IBGE_URL_PADRAO.into(),
                prazo_fonte: Duration::from_secs(10),
                validade: Duration::from_secs(86400),
                itens_max: 500,
                host: "127.0.0.1".into(),
                porta: 8000,
            }
        );
    }

    #[test]
    fn leitura_das_variaveis_localidades() {
        let c = carregar(ambiente(&[
            (
                "LOCALIDADES_IBGE_URL",
                "http://127.0.0.1:8099/api/v1/localidades/",
            ),
            ("LOCALIDADES_PRAZO_FONTE_S", "1.5"),
            ("LOCALIDADES_VALIDADE_S", " 2 "),
            ("LOCALIDADES_ITENS_MAX", "50"),
            ("LOCALIDADES_PORTA", "8090"),
            ("LOCALIDADES_HOST", "0.0.0.0"),
        ]))
        .unwrap();
        assert_eq!(c.ibge_url, "http://127.0.0.1:8099/api/v1/localidades");
        assert_eq!(
            (c.prazo_fonte, c.validade),
            (Duration::from_millis(1500), Duration::from_secs(2))
        );
        assert_eq!(
            (c.itens_max, c.porta, c.host.as_str()),
            (50, 8090, "0.0.0.0")
        );
    }

    #[test]
    fn variavel_vazia_usa_o_padrao() {
        let c = carregar(ambiente(&[
            ("LOCALIDADES_PRAZO_FONTE_S", "  "),
            ("LOCALIDADES_HOST", ""),
        ]))
        .unwrap();
        assert_eq!(
            (c.prazo_fonte, c.host.as_str()),
            (Duration::from_secs(10), "127.0.0.1")
        );
    }

    #[test]
    fn valores_invalidos_impedem_a_partida() {
        let casos = [
            ("LOCALIDADES_PRAZO_FONTE_S", "abc", "precisa ser um número"),
            ("LOCALIDADES_PRAZO_FONTE_S", "0", "maior que zero"),
            ("LOCALIDADES_PRAZO_FONTE_S", "-1", "maior que zero"),
            ("LOCALIDADES_PRAZO_FONTE_S", "NaN", "finito"),
            ("LOCALIDADES_PRAZO_FONTE_S", "inf", "finito"),
            ("LOCALIDADES_PRAZO_FONTE_S", "infinity", "finito"),
            ("LOCALIDADES_PRAZO_FONTE_S", "0.0001", "pelo menos 0.001"),
            ("LOCALIDADES_VALIDADE_S", "x", "precisa ser um número"),
            ("LOCALIDADES_VALIDADE_S", "1e300", "no máximo 1000000000"),
            ("LOCALIDADES_VALIDADE_S", "1e400", "finito"),
            ("LOCALIDADES_VALIDADE_S", "0.0001", "pelo menos 0.001"),
            ("LOCALIDADES_ITENS_MAX", "0", "maior que zero"),
            (
                "LOCALIDADES_ITENS_MAX",
                "1.5",
                "precisa ser um número inteiro",
            ),
            (
                "LOCALIDADES_IBGE_URL",
                "ftp://ibge",
                "precisa começar com http:// ou https://",
            ),
            ("LOCALIDADES_PORTA", "abc", "precisa ser um número inteiro"),
            ("LOCALIDADES_PORTA", "99999", "entre 1 e 65535"),
        ];
        for (variavel, valor, trecho) in casos {
            let erro =
                carregar(ambiente(&[(variavel, valor)])).expect_err(&format!("{variavel}={valor}"));
            assert!(
                erro.starts_with(&format!("{variavel} "))
                    && erro.contains(trecho)
                    && erro.contains("recebi '"),
                "{variavel}={valor}: {erro}"
            );
        }
    }

    #[test]
    fn limites_aceitos() {
        let c = carregar(ambiente(&[
            ("LOCALIDADES_PRAZO_FONTE_S", "0.001"),
            ("LOCALIDADES_VALIDADE_S", "1000000000"),
        ]))
        .unwrap();
        assert_eq!(
            (c.prazo_fonte, c.validade),
            (Duration::from_millis(1), Duration::from_secs(1_000_000_000))
        );
    }
}

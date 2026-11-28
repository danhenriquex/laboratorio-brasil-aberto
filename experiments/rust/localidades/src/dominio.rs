//! Entidades e regras do serviço (data-model do E1 e do E8). Não depende do axum.

use serde::Serialize;
use unicode_normalization::UnicodeNormalization;
use unicode_normalization::char::is_combining_mark;

use crate::erros::ErroDominio;

/// Código e sigla das 27 UFs, usados só para validar e resolver a entrada (R1 do E1). Nomes e regiões vêm
/// sempre do IBGE.
pub const UFS_OFICIAIS: [(&str, &str); 27] = [
    ("11", "RO"),
    ("12", "AC"),
    ("13", "AM"),
    ("14", "RR"),
    ("15", "PA"),
    ("16", "AP"),
    ("17", "TO"),
    ("21", "MA"),
    ("22", "PI"),
    ("23", "CE"),
    ("24", "RN"),
    ("25", "PB"),
    ("26", "PE"),
    ("27", "AL"),
    ("28", "SE"),
    ("29", "BA"),
    ("31", "MG"),
    ("32", "ES"),
    ("33", "RJ"),
    ("35", "SP"),
    ("41", "PR"),
    ("42", "SC"),
    ("43", "RS"),
    ("50", "MS"),
    ("51", "MT"),
    ("52", "GO"),
    ("53", "DF"),
];

pub const NOME_MIN: usize = 2;
pub const NOME_MAX: usize = 60;

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct Regiao {
    pub codigo: String,
    pub sigla: String,
    pub nome: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct Uf {
    pub codigo: String,
    pub sigla: String,
    pub nome: String,
    pub regiao: Regiao,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct UfResumida {
    pub codigo: String,
    pub sigla: String,
    pub nome: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct RegiaoImediata {
    pub codigo: String,
    pub nome: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct RegiaoIntermediaria {
    pub codigo: String,
    pub nome: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct MunicipioResumido {
    pub codigo: String,
    pub nome: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct Municipio {
    pub codigo: String,
    pub nome: String,
    pub uf: UfResumida,
    pub regiao_imediata: RegiaoImediata,
    pub regiao_intermediaria: RegiaoIntermediaria,
}

/// Vai no envelope das listas. `pagina` é i64 porque `pagina=99999999999` estoura 32 bits (T045 do E4).
#[derive(Debug, Clone, Copy, Serialize, PartialEq, Eq)]
pub struct Paginacao {
    pub pagina: i64,
    pub itens: u32,
    pub total: usize,
    pub paginas: usize,
}

#[derive(Debug, Clone)]
pub struct Pagina<T> {
    pub itens: Vec<T>,
    pub paginacao: Paginacao,
}

/// O que pode ser ordenado por nome: UFs e municípios.
pub trait Nomeado {
    fn nome(&self) -> &str;
    fn codigo(&self) -> &str;
}

impl Nomeado for Uf {
    fn nome(&self) -> &str {
        &self.nome
    }
    fn codigo(&self) -> &str {
        &self.codigo
    }
}

impl Nomeado for MunicipioResumido {
    fn nome(&self) -> &str {
        &self.nome
    }
    fn codigo(&self) -> &str {
        &self.codigo
    }
}

/// A regra do R8 do E1: NFKD, sem marcas combinantes e casefold.
pub fn dobrar(texto: &str) -> String {
    let sem_marcas: String = texto.nfkd().filter(|c| !is_combining_mark(*c)).collect();
    caseless::default_case_fold_str(&sem_marcas)
}

/// Cópia ordenada por (nome dobrado, código), a mesma chave das outras implementações.
pub fn ordenar<T: Nomeado + Clone>(itens: &[T]) -> Vec<T> {
    let mut com_chave: Vec<(String, &T)> = itens.iter().map(|i| (dobrar(i.nome()), i)).collect();
    com_chave.sort_by(|(na, a), (nb, b)| na.cmp(nb).then_with(|| a.codigo().cmp(b.codigo())));
    com_chave.into_iter().map(|(_, i)| i.clone()).collect()
}

/// Mantém os municípios cujo nome dobrado contém o termo dobrado.
pub fn filtrar_por_nome(itens: &[MunicipioResumido], nome: &str) -> Vec<MunicipioResumido> {
    let alvo = dobrar(nome.trim());
    itens
        .iter()
        .filter(|m| dobrar(&m.nome).contains(&alvo))
        .cloned()
        .collect()
}

/// Fatia uma coleção já filtrada e ordenada. Página além do fim devolve lista vazia com o total correto,
/// sem estourar a conta mesmo com páginas enormes.
pub fn paginar<T: Clone>(colecao: &[T], pagina: i64, itens: u32) -> Pagina<T> {
    let total = colecao.len();
    let tamanho = itens.max(1) as usize;
    let paginas = total.div_ceil(tamanho);
    let fatia = if pagina >= 1 && (pagina as u64) <= paginas as u64 {
        let inicio = (pagina as usize - 1) * tamanho;
        colecao[inicio..(inicio + tamanho).min(total)].to_vec()
    } else {
        Vec::new()
    };
    Pagina {
        itens: fatia,
        paginacao: Paginacao {
            pagina,
            itens,
            total,
            paginas,
        },
    }
}

fn so_letras_ascii(s: &str, n: usize) -> bool {
    s.len() == n && s.bytes().all(|b| b.is_ascii_alphabetic())
}

fn so_digitos_ascii(s: &str, n: usize) -> bool {
    s.len() == n && s.bytes().all(|b| b.is_ascii_digit())
}

/// Sigla (sem diferenciar maiúsculas) ou código de 2 dígitos → código da UF.
pub fn resolver_uf(param: &str) -> Result<String, ErroDominio> {
    let valor = param.trim();
    let codigo = if so_letras_ascii(valor, 2) {
        let sigla = valor.to_ascii_uppercase();
        UFS_OFICIAIS
            .iter()
            .find(|(_, s)| *s == sigla)
            .map(|(c, _)| c.to_string())
    } else if so_digitos_ascii(valor, 2) {
        UFS_OFICIAIS
            .iter()
            .find(|(c, _)| *c == valor)
            .map(|(c, _)| c.to_string())
    } else {
        return Err(ErroDominio::entrada_invalida(format!(
            "UF inválida: use a sigla de 2 letras (ex.: RJ) ou o código de 2 dígitos (ex.: 33), recebi {}",
            repr(param)
        )));
    };
    codigo.ok_or_else(|| ErroDominio::nao_encontrado(format!("não existe UF {}", repr(valor))))
}

pub fn validar_codigo_municipio(codigo: &str) -> Result<String, ErroDominio> {
    if !so_digitos_ascii(codigo, 7) {
        return Err(ErroDominio::entrada_invalida(format!(
            "código de município inválido: precisa ter exatamente 7 dígitos, recebi {}",
            repr(codigo)
        )));
    }
    Ok(codigo.to_string())
}

pub fn validar_paginacao(pagina: i64, itens: i64, itens_max: u32) -> Result<(), ErroDominio> {
    if pagina < 1 {
        return Err(ErroDominio::entrada_invalida(format!(
            "pagina precisa ser maior ou igual a 1, recebi {pagina}"
        )));
    }
    if itens < 1 || itens > itens_max as i64 {
        return Err(ErroDominio::entrada_invalida(format!(
            "itens precisa estar entre 1 e {itens_max}, recebi {itens}"
        )));
    }
    Ok(())
}

/// Conta caracteres, não bytes, como o len() do Python.
pub fn validar_nome(nome: &str) -> Result<String, ErroDominio> {
    let valor = nome.trim();
    let n = valor.chars().count();
    if n < NOME_MIN {
        return Err(ErroDominio::entrada_invalida(format!(
            "nome precisa ter pelo menos {NOME_MIN} caracteres, sem contar espaços nas pontas"
        )));
    }
    if n > NOME_MAX {
        return Err(ErroDominio::entrada_invalida(format!(
            "nome pode ter no máximo {NOME_MAX} caracteres"
        )));
    }
    Ok(valor.to_string())
}

/// Imita o repr() do Python que o E1 usa nas mensagens ('R1', "d'Oeste"), para os detalhes saírem iguais.
pub fn repr(s: &str) -> String {
    let aspas = if s.contains('\'') && !s.contains('"') {
        '"'
    } else {
        '\''
    };
    let mut saida = String::with_capacity(s.len() + 2);
    saida.push(aspas);
    for c in s.chars() {
        match c {
            '\\' => saida.push_str("\\\\"),
            '\n' => saida.push_str("\\n"),
            '\r' => saida.push_str("\\r"),
            '\t' => saida.push_str("\\t"),
            c if c == aspas => {
                saida.push('\\');
                saida.push(c);
            }
            c if c.is_control() => saida.push_str(&format!("\\x{:02x}", c as u32)),
            c => saida.push(c),
        }
    }
    saida.push(aspas);
    saida
}

#[cfg(test)]
mod tests {
    use super::*;

    fn municipio(codigo: &str, nome: &str) -> MunicipioResumido {
        MunicipioResumido {
            codigo: codigo.into(),
            nome: nome.into(),
        }
    }

    #[test]
    fn dobrar_como_no_e1() {
        for (entrada, esperado) in [
            ("Niterói", "niteroi"),
            ("SÃO", "sao"),
            ("São João d'Aliança", "sao joao d'alianca"),
            ("Açu", "acu"),
            ("", ""),
        ] {
            assert_eq!(dobrar(entrada), esperado, "dobrar({entrada:?})");
        }
    }

    #[test]
    fn ordenar_por_nome_dobrado_e_desempate_pelo_codigo() {
        let itens = vec![
            municipio("3", "Ébano"),
            municipio("2", "abacate"),
            municipio("9", "Abacate"),
            municipio("1", "Zé"),
        ];
        let codigos: Vec<_> = ordenar(&itens).into_iter().map(|m| m.codigo).collect();
        assert_eq!(codigos, ["2", "9", "3", "1"]);
        assert_eq!(itens[0].codigo, "3", "ordenar não mexe na lista original");
    }

    #[test]
    fn filtrar_por_nome_sem_acento_nem_caixa() {
        let itens = vec![
            municipio("1", "Niterói"),
            municipio("2", "São Gonçalo"),
            municipio("3", "Rio de Janeiro"),
        ];
        let codigos = |termo: &str| -> Vec<String> {
            filtrar_por_nome(&itens, termo)
                .into_iter()
                .map(|m| m.codigo)
                .collect()
        };
        assert_eq!(codigos("niteroi"), ["1"]);
        assert_eq!(codigos("  NITERÓI "), ["1"]);
        assert_eq!(codigos("sao"), ["2"]);
        assert_eq!(codigos("o"), ["1", "2", "3"]);
        assert!(codigos("xyz").is_empty());
    }

    #[test]
    fn paginar_sem_estourar() {
        let numeros: Vec<u32> = (0..92).collect();
        let p = paginar(&numeros, 1, 100);
        assert_eq!(
            (p.itens.len(), p.paginacao.total, p.paginacao.paginas),
            (92, 92, 1)
        );
        let p = paginar(&numeros, 10, 10);
        assert_eq!(
            (p.itens.len(), p.itens[0], p.paginacao.paginas),
            (2, 90, 10)
        );
        let p = paginar(&numeros, 11, 10);
        assert!(p.itens.is_empty());
        assert_eq!(p.paginacao.total, 92);
        let p = paginar(&numeros, i64::MAX, 500);
        assert!(p.itens.is_empty());
        assert_eq!(p.paginacao.pagina, i64::MAX);
        let vazio: Vec<u32> = Vec::new();
        let p = paginar(&vazio, 1, 10);
        assert_eq!((p.paginacao.total, p.paginacao.paginas), (0, 0));
    }

    #[test]
    fn resolver_uf_por_sigla_ou_codigo() {
        for (entrada, codigo) in [(" rj ", "33"), ("RJ", "33"), ("33", "33"), ("df", "53")] {
            assert_eq!(resolver_uf(entrada).unwrap(), codigo);
        }
        for entrada in ["XX", "99"] {
            assert_eq!(resolver_uf(entrada).unwrap_err().tipo, "nao-encontrado");
        }
        for entrada in ["R1", "123", "", "３３"] {
            assert_eq!(
                resolver_uf(entrada).unwrap_err().tipo,
                "entrada-invalida",
                "{entrada:?}"
            );
        }
        assert!(
            resolver_uf("R1")
                .unwrap_err()
                .detalhe
                .ends_with("recebi 'R1'")
        );
        assert_eq!(resolver_uf("XX").unwrap_err().detalhe, "não existe UF 'XX'");
    }

    #[test]
    fn validar_codigo_de_municipio() {
        assert!(validar_codigo_municipio("3304557").is_ok());
        for invalido in ["12ab", "123456", "12345678", "330455７", "", " 3304557"] {
            assert_eq!(
                validar_codigo_municipio(invalido).unwrap_err().tipo,
                "entrada-invalida",
                "{invalido:?}"
            );
        }
        assert_eq!(
            validar_codigo_municipio("12ab").unwrap_err().detalhe,
            "código de município inválido: precisa ter exatamente 7 dígitos, recebi '12ab'"
        );
    }

    #[test]
    fn validar_paginacao_com_o_limite() {
        assert!(validar_paginacao(1, 100, 500).is_ok());
        assert!(validar_paginacao(i64::MAX, 500, 500).is_ok());
        assert_eq!(
            validar_paginacao(0, 100, 500).unwrap_err().detalhe,
            "pagina precisa ser maior ou igual a 1, recebi 0"
        );
        assert_eq!(
            validar_paginacao(1, 0, 500).unwrap_err().detalhe,
            "itens precisa estar entre 1 e 500, recebi 0"
        );
        assert_eq!(
            validar_paginacao(1, 501, 500).unwrap_err().detalhe,
            "itens precisa estar entre 1 e 500, recebi 501"
        );
    }

    #[test]
    fn validar_nome_em_caracteres() {
        assert_eq!(validar_nome("  são  ").unwrap(), "são");
        for (entrada, trecho) in [
            ("a", "pelo menos 2"),
            ("  a  ", "pelo menos 2"),
            ("", "pelo menos 2"),
        ] {
            assert!(validar_nome(entrada).unwrap_err().detalhe.contains(trecho));
        }
        assert!(
            validar_nome(&"x".repeat(61))
                .unwrap_err()
                .detalhe
                .contains("no máximo 60")
        );
        assert!(
            validar_nome(&"ã".repeat(60)).is_ok(),
            "60 caracteres, não bytes"
        );
    }

    #[test]
    fn repr_como_no_python() {
        assert_eq!(repr("R1"), "'R1'");
        assert_eq!(repr("d'Oeste"), "\"d'Oeste\"");
        assert_eq!(repr("a\\b"), "'a\\\\b'");
        assert_eq!(repr("linha\nnova"), "'linha\\nnova'");
    }
}

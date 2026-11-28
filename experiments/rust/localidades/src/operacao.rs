//! O que é da operação do serviço: correlação, estado do pedido, saúde, métricas e registro (US5 do E1;
//! research do E8, R10 e R12).

use std::io::Write;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use axum::extract::State;
use axum::http::{Method, header};
use axum::response::IntoResponse;
use prometheus::{
    Encoder, HistogramOpts, HistogramVec, IntCounterVec, Opts, Registry, TextEncoder,
};
use serde::Serialize;

use crate::servico::formatar_momento;
use crate::topo::Observador;

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

/// As mesmas faixas do histograma do E1.
const FAIXAS_FONTE_S: [f64; 8] = [0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0];

/// Métricas num registro próprio, e não no global, para cada montagem ter as suas séries (research R10).
/// O `prometheus` não impõe sufixo de unidade: os nomes saem exatamente como no contrato.
pub struct Metricas {
    registro: Registry,
    pedidos: IntCounterVec,
    erros: IntCounterVec,
    cache: IntCounterVec,
    fonte: HistogramVec,
}

impl Metricas {
    pub fn novas() -> Arc<Self> {
        let contador = |nome: &str, ajuda: &str, rotulos: &[&str]| {
            IntCounterVec::new(Opts::new(nome, ajuda), rotulos).expect("métrica válida")
        };
        let m = Self {
            registro: Registry::new(),
            pedidos: contador(
                "localidades_pedidos_total",
                "Pedidos atendidos, por modelo de rota e status.",
                &["rota", "status"],
            ),
            erros: contador(
                "localidades_erros_total",
                "Erros devolvidos, por tipo de problema.",
                &["tipo"],
            ),
            cache: contador(
                "localidades_cache_total",
                "Uso da cópia guardada: acerto, falta ou desatualizado.",
                &["resultado"],
            ),
            fonte: HistogramVec::new(
                HistogramOpts::new(
                    "localidades_fonte_duracao_segundos",
                    "Duração das consultas ao IBGE, por recurso.",
                )
                .buckets(FAIXAS_FONTE_S.to_vec()),
                &["recurso"],
            )
            .expect("métrica válida"),
        };
        for c in [&m.pedidos, &m.erros, &m.cache] {
            m.registro.register(Box::new(c.clone())).expect("registro");
        }
        m.registro
            .register(Box::new(m.fonte.clone()))
            .expect("registro");
        Arc::new(m)
    }

    pub fn observar_fonte(&self, recurso: &str, segundos: f64) {
        self.fonte.with_label_values(&[recurso]).observe(segundos);
    }

    pub fn registrar_pedido(
        &self,
        rota: &str,
        status: u16,
        tipo_erro: Option<&str>,
        cache: Option<&str>,
    ) {
        self.pedidos
            .with_label_values(&[rota, &status.to_string()])
            .inc();
        if let Some(tipo) = tipo_erro {
            self.erros.with_label_values(&[tipo]).inc();
        }
        if let Some(resultado) = cache {
            self.cache.with_label_values(&[resultado]).inc();
        }
    }

    /// O formato texto do Prometheus.
    pub fn texto(&self) -> String {
        TextEncoder::new()
            .encode_to_string(&self.registro.gather())
            .unwrap_or_default()
    }
}

/// GET /metrics: sempre o formato texto do Prometheus, qualquer que seja o Accept (T048 do E4). O
/// `TextEncoder` não negocia, então não há o que retirar, ao contrário do `promhttp` do E7.
pub async fn expor_metricas(State(m): State<Arc<Metricas>>) -> impl IntoResponse {
    (
        [(
            header::CONTENT_TYPE,
            TextEncoder::new().format_type().to_string(),
        )],
        m.texto(),
    )
}

/// Uma linha do registro, com os campos do E1 na ordem da *struct*. Sem IP nem cabeçalhos além da
/// correlação (Constituição VII).
#[derive(Serialize)]
struct Linha<'a> {
    momento: String,
    nivel: &'static str,
    correlacao_id: &'a str,
    metodo: &'a str,
    rota: &'a str,
    status: u16,
    duracao_ms: f64,
    cache: Option<&'a str>,
    fonte_ms: Option<f64>,
}

fn uma_casa(x: f64) -> f64 {
    (x * 10.0).round() / 10.0
}

/// Uma linha JSON por pedido, escrita com `serde_json` (research R12). O `tracing-subscriber` usaria
/// nomes de campo próprios.
pub struct Registro {
    saida: Mutex<Box<dyn Write + Send>>,
}

impl Registro {
    pub fn novo(saida: Box<dyn Write + Send>) -> Self {
        Self {
            saida: Mutex::new(saida),
        }
    }

    pub fn na_saida_padrao() -> Self {
        Self::novo(Box::new(std::io::stdout()))
    }

    /// Escreve a linha de um pedido terminado. 5xx sai com nivel "error", o resto com "info".
    pub fn pedido(&self, metodo: &str, estado: &Estado, status: u16, duracao: Duration) {
        let l = estado.leitura();
        let linha = Linha {
            momento: formatar_momento(time::OffsetDateTime::now_utc()),
            nivel: if status >= 500 { "error" } else { "info" },
            correlacao_id: &estado.correlacao,
            metodo,
            rota: &l.rota,
            status,
            duracao_ms: uma_casa(duracao.as_secs_f64() * 1000.0),
            cache: l.cache,
            fonte_ms: l.fonte_s.map(|s| uma_casa(s * 1000.0)),
        };
        let Ok(mut texto) = serde_json::to_vec(&linha) else {
            return;
        };
        texto.push(b'\n');
        let mut saida = self.saida.lock().unwrap_or_else(|e| e.into_inner());
        // Uma escrita só por linha, para linhas de pedidos simultâneos não se misturarem.
        let _ = saida.write_all(&texto).and_then(|_| saida.flush());
    }
}

/// Junta métricas e registro no fim de cada pedido. A assinatura é a do `topo::Observador`.
pub fn observador(metricas: Arc<Metricas>, registro: Arc<Registro>) -> Observador {
    Arc::new(
        move |metodo: &Method, estado: &Estado, status: u16, duracao: Duration| {
            let l = estado.leitura();
            metricas.registrar_pedido(&l.rota, status, l.tipo_erro, l.cache);
            registro.pedido(metodo.as_str(), estado, status, duracao);
        },
    )
}

//! Cópia guardada com validade, consulta única por chave e cópia vencida quando a fonte falha (R5 do E1;
//! research do E8, R7). Em memória do processo (Constituição X).
//!
//! Estados de uma entrada (data-model do E1): ausente → válida → vencida. "Não encontrado" e erros nunca
//! entram na cópia.
//!
//! Consulta única (T050 do E1): pedidos simultâneos pelo mesmo recurso aguardam a mesma consulta e recebem
//! o mesmo resultado, inclusive o erro. Em Rust, um futuro abandonado é cancelado, então a consulta roda num
//! `tokio::spawn`, que não morre com o pedido que a iniciou (o `shield` do E1), e o `Shared` entrega o
//! resultado a todos os que esperam.

use std::collections::HashMap;
use std::future::Future;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use futures::FutureExt;
use futures::future::{BoxFuture, Shared};
use time::OffsetDateTime;

use crate::erros::ErroDominio;
use crate::operacao::{ESTADO, estado_atual};
use crate::servico::{Agora, Dados, Monotonico};

/// O que o serviço recebe: os dados, a procedência e o uso da cópia (acerto, falta ou desatualizado).
#[derive(Debug, Clone)]
pub struct Entrada {
    pub dados: Dados,
    pub url_fonte: String,
    pub coletado_em: OffsetDateTime,
    pub desatualizado: bool,
    pub resultado: &'static str,
}

#[derive(Clone)]
struct Guardada {
    dados: Dados,
    url_fonte: String,
    coletado_em: OffsetDateTime,
    expira_em: Duration, // no relógio monotônico
}

impl Guardada {
    fn entrada(&self, desatualizado: bool, resultado: &'static str) -> Entrada {
        Entrada {
            dados: self.dados.clone(),
            url_fonte: self.url_fonte.clone(),
            coletado_em: self.coletado_em,
            desatualizado,
            resultado,
        }
    }
}

type Consulta = Shared<BoxFuture<'static, Result<Entrada, ErroDominio>>>;

pub struct Cache {
    agora: Agora,
    monotonico: Monotonico,
    validade: Duration,
    // Os dois mapas usam std::sync::Mutex, nunca segurado durante um await.
    guardadas: Mutex<HashMap<String, Guardada>>,
    em_andamento: Mutex<HashMap<String, Consulta>>,
}

fn travar<T>(m: &Mutex<T>) -> std::sync::MutexGuard<'_, T> {
    m.lock().unwrap_or_else(|e| e.into_inner())
}

impl Cache {
    pub fn novo(agora: Agora, monotonico: Monotonico, validade: Duration) -> Arc<Self> {
        Arc::new(Self {
            agora,
            monotonico,
            validade,
            guardadas: Mutex::new(HashMap::new()),
            em_andamento: Mutex::new(HashMap::new()),
        })
    }

    fn valida(&self, chave: &str) -> Option<Guardada> {
        let agora = (self.monotonico)();
        travar(&self.guardadas)
            .get(chave)
            .filter(|g| agora < g.expira_em)
            .cloned()
    }

    /// Devolve a cópia válida ou consulta a fonte. Cada pedido espera a consulta; se ele desistir, o futuro
    /// dele é abandonado, mas a consulta continua para os outros.
    pub async fn obter<F>(
        self: &Arc<Self>,
        chave: String,
        buscar: F,
    ) -> Result<Entrada, ErroDominio>
    where
        F: Future<Output = Result<(Dados, String), ErroDominio>> + Send + 'static,
    {
        if let Some(g) = self.valida(&chave) {
            return Ok(g.entrada(false, "acerto"));
        }
        let (consulta, iniciou) = {
            let mut andamento = travar(&self.em_andamento);
            match andamento.get(&chave) {
                Some(c) => (c.clone(), false),
                None => {
                    let c = self.iniciar(chave.clone(), buscar);
                    andamento.insert(chave.clone(), c.clone());
                    (c, true)
                }
            }
        };
        match consulta.await {
            Ok(mut entrada) => {
                if !iniciou {
                    entrada.resultado = "acerto";
                }
                Ok(entrada)
            }
            Err(erro) => self.vencida_ou_erro(&chave, erro),
        }
    }

    /// Dispara a consulta numa tarefa própria. O estado do pedido que a iniciou vai junto, para o tempo da
    /// fonte ser anotado nele (o `task_local` não passa sozinho para outra tarefa).
    fn iniciar<F>(self: &Arc<Self>, chave: String, buscar: F) -> Consulta
    where
        F: Future<Output = Result<(Dados, String), ErroDominio>> + Send + 'static,
    {
        let cache = Arc::clone(self);
        let tarefa = async move {
            let coletado_em = (cache.agora)();
            let resultado = buscar.await;
            let entrada = resultado.map(|(dados, url_fonte)| {
                let g = Guardada {
                    dados,
                    url_fonte,
                    coletado_em,
                    expira_em: (cache.monotonico)() + cache.validade,
                };
                travar(&cache.guardadas).insert(chave.clone(), g.clone());
                g.entrada(false, "falta")
            });
            travar(&cache.em_andamento).remove(&chave);
            entrada
        };
        let tarefa: BoxFuture<'static, _> = match estado_atual() {
            Some(estado) => ESTADO.scope(estado, tarefa).boxed(),
            None => tarefa.boxed(),
        };
        let handle = tokio::spawn(tarefa);
        async move { handle.await.unwrap_or_else(|_| Err(ErroDominio::interno())) }
            .boxed()
            .shared()
    }

    /// Serve a cópia vencida quando a falha é da fonte; qualquer outro erro sobe.
    fn vencida_ou_erro(&self, chave: &str, erro: ErroDominio) -> Result<Entrada, ErroDominio> {
        if !erro.de_fonte() {
            return Err(erro);
        }
        match travar(&self.guardadas).get(chave) {
            Some(g) => Ok(g.entrada(true, "desatualizado")),
            None => Err(erro),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
    use tokio::sync::Notify;

    const VALIDADE: Duration = Duration::from_secs(24 * 3600);

    #[derive(Clone)]
    struct Relogio(Arc<Mutex<(OffsetDateTime, Duration)>>);

    impl Relogio {
        fn avancar(&self, d: Duration) {
            let mut g = self.0.lock().unwrap();
            g.0 += d;
            g.1 += d;
        }
    }

    fn novo_cache() -> (Arc<Cache>, Relogio) {
        let r = Relogio(Arc::new(Mutex::new((
            time::macros::datetime!(2026-11-26 12:00:00.123 UTC),
            Duration::ZERO,
        ))));
        let (a, m) = (r.clone(), r.clone());
        (
            Cache::novo(
                Arc::new(move || a.0.lock().unwrap().0),
                Arc::new(move || m.0.lock().unwrap().1),
                VALIDADE,
            ),
            r,
        )
    }

    fn dados() -> Dados {
        Dados::Ufs(Arc::new(Vec::new()))
    }

    /// Uma fonte que conta as chamadas e responde com dados ou com um erro.
    fn fonte(
        n: &Arc<AtomicUsize>,
        erro: Option<ErroDominio>,
    ) -> impl Future<Output = Result<(Dados, String), ErroDominio>> + Send + 'static {
        let n = n.clone();
        async move {
            n.fetch_add(1, Ordering::SeqCst);
            match erro {
                Some(e) => Err(e),
                None => Ok((dados(), "https://ibge/estados".to_string())),
            }
        }
    }

    #[tokio::test]
    async fn acerto_dentro_da_validade() {
        let (c, r) = novo_cache();
        let n = Arc::new(AtomicUsize::new(0));
        let primeira = c.obter("estados".into(), fonte(&n, None)).await.unwrap();
        assert_eq!(
            (primeira.resultado, primeira.url_fonte.as_str()),
            ("falta", "https://ibge/estados")
        );
        r.avancar(VALIDADE - Duration::from_secs(1));
        let segunda = c.obter("estados".into(), fonte(&n, None)).await.unwrap();
        assert_eq!(
            (
                segunda.resultado,
                segunda.coletado_em,
                segunda.desatualizado
            ),
            ("acerto", primeira.coletado_em, false)
        );
        assert_eq!(n.load(Ordering::SeqCst), 1);
    }

    #[tokio::test]
    async fn falta_depois_da_validade() {
        let (c, r) = novo_cache();
        let n = Arc::new(AtomicUsize::new(0));
        let primeira = c.obter("estados".into(), fonte(&n, None)).await.unwrap();
        r.avancar(VALIDADE);
        let segunda = c.obter("estados".into(), fonte(&n, None)).await.unwrap();
        assert_eq!(segunda.resultado, "falta");
        assert!(segunda.coletado_em > primeira.coletado_em);
        assert_eq!(n.load(Ordering::SeqCst), 2);
    }

    #[tokio::test]
    async fn copia_vencida_quando_a_fonte_falha() {
        let (c, r) = novo_cache();
        let n = Arc::new(AtomicUsize::new(0));
        let primeira = c.obter("estados".into(), fonte(&n, None)).await.unwrap();
        r.avancar(VALIDADE + Duration::from_secs(3600));
        let vencida = c
            .obter(
                "estados".into(),
                fonte(&n, Some(ErroDominio::fonte_indisponivel("fora"))),
            )
            .await
            .unwrap();
        assert_eq!(
            (
                vencida.desatualizado,
                vencida.resultado,
                vencida.coletado_em
            ),
            (true, "desatualizado", primeira.coletado_em)
        );
    }

    #[tokio::test]
    async fn erros_e_nao_encontrado_nao_sao_guardados() {
        let (c, r) = novo_cache();
        let n = Arc::new(AtomicUsize::new(0));
        for _ in 0..2 {
            let erro = c
                .obter(
                    "m/1".into(),
                    fonte(&n, Some(ErroDominio::fonte_lenta("lenta"))),
                )
                .await
                .unwrap_err();
            assert_eq!(erro.tipo, "fonte-lenta");
        }
        for _ in 0..2 {
            let erro = c
                .obter(
                    "m/9".into(),
                    fonte(&n, Some(ErroDominio::nao_encontrado("não existe"))),
                )
                .await
                .unwrap_err();
            assert_eq!(erro.tipo, "nao-encontrado");
        }
        assert_eq!(n.load(Ordering::SeqCst), 4);
        // "Não encontrado" não é erro de fonte: com uma cópia vencida, ele não vira resposta desatualizada.
        c.obter("x".into(), fonte(&n, None)).await.unwrap();
        r.avancar(VALIDADE + Duration::from_secs(1));
        let erro = c
            .obter(
                "x".into(),
                fonte(&n, Some(ErroDominio::nao_encontrado("sumiu"))),
            )
            .await
            .unwrap_err();
        assert_eq!(erro.tipo, "nao-encontrado");
    }

    /// Consulta única (T050 do E1): 20 pedidos simultâneos fazem uma consulta e recebem o mesmo resultado,
    /// inclusive o mesmo erro; só quem iniciou conta como falta.
    #[tokio::test(flavor = "multi_thread", worker_threads = 4)]
    async fn pedidos_simultaneos_fazem_uma_consulta() {
        for falha in [
            None,
            Some(ErroDominio::fonte_lenta("o IBGE não respondeu em 10 s")),
        ] {
            let (c, _) = novo_cache();
            let n = Arc::new(AtomicUsize::new(0));
            let soltar = Arc::new(Notify::new());
            let pedidos: Vec<_> = (0..20)
                .map(|_| {
                    let (c, n, soltar, falha) =
                        (c.clone(), n.clone(), soltar.clone(), falha.clone());
                    tokio::spawn(async move {
                        c.obter("estados".into(), async move {
                            n.fetch_add(1, Ordering::SeqCst);
                            soltar.notified().await;
                            match falha {
                                Some(e) => Err(e),
                                None => Ok((dados(), "u".to_string())),
                            }
                        })
                        .await
                    })
                })
                .collect();
            tokio::time::sleep(Duration::from_millis(50)).await;
            soltar.notify_waiters();
            let mut faltas = 0;
            for p in pedidos {
                match (p.await.unwrap(), &falha) {
                    (Ok(e), None) => faltas += usize::from(e.resultado == "falta"),
                    (Err(e), Some(f)) => assert_eq!(&e, f, "o mesmo erro da consulta"),
                    (outro, _) => panic!("resultado inesperado: {outro:?}"),
                }
            }
            assert_eq!(n.load(Ordering::SeqCst), 1, "uma consulta só");
            if falha.is_none() {
                assert_eq!(faltas, 1, "só quem iniciou a consulta conta como falta");
            }
        }
    }

    /// Um pedido que desiste não cancela a consulta que os outros esperam (o shield do E1).
    #[tokio::test]
    async fn pedido_que_desiste_nao_cancela_a_consulta() {
        let (c, _) = novo_cache();
        let soltar = Arc::new(Notify::new());
        let terminou = Arc::new(AtomicBool::new(false));
        let (s, t) = (soltar.clone(), terminou.clone());
        let consulta = async move {
            s.notified().await;
            t.store(true, Ordering::SeqCst);
            Ok((dados(), "u".to_string()))
        };
        let desistiu =
            tokio::time::timeout(Duration::from_millis(30), c.obter("k".into(), consulta)).await;
        assert!(desistiu.is_err(), "o primeiro pedido foi abandonado");
        let outro = {
            let c = c.clone();
            tokio::spawn(async move {
                c.obter("k".into(), async {
                    panic!("não deveria consultar de novo")
                })
                .await
            })
        };
        tokio::time::sleep(Duration::from_millis(30)).await;
        soltar.notify_waiters();
        let e = outro.await.unwrap().unwrap();
        assert_eq!(e.resultado, "acerto");
        assert!(
            terminou.load(Ordering::SeqCst),
            "a consulta abandonada continuou até o fim"
        );
    }
}

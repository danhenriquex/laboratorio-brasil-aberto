//! Comando `localidades`: lê a configuração LOCALIDADES_*, monta as peças e sobe o servidor HTTP.
//! Configuração inválida impede a partida, com a mensagem do E1 e código de saída 2.

use std::process::ExitCode;
use std::sync::Arc;

use localidades::config;
use localidades::fonte::Cliente;
use localidades::operacao::{Metricas, Registro, estado_atual, observador};
use localidades::servico::{Opcoes, Servico};
use localidades::topo::Topo;

#[tokio::main]
async fn main() -> ExitCode {
    let cfg = match config::carregar(|nome| std::env::var(nome).ok()) {
        Ok(cfg) => cfg,
        Err(erro) => {
            eprintln!("configuração inválida: {erro}");
            return ExitCode::from(2);
        }
    };

    let metricas = Metricas::novas();
    let m = metricas.clone();
    let ao_medir = Arc::new(move |recurso: &str, segundos: f64| {
        m.observar_fonte(recurso, segundos);
        if let Some(estado) = estado_atual() {
            estado.somar_fonte(segundos);
        }
    });
    let cliente = Cliente::novo(&cfg.ibge_url, cfg.prazo_fonte, Some(ao_medir));
    let servico = Servico::novo(cliente, Opcoes::do_sistema(cfg.validade, cfg.itens_max));
    let topo = Topo {
        observar: Some(observador(
            metricas.clone(),
            Arc::new(Registro::na_saida_padrao()),
        )),
        metricas: Some(metricas),
    };
    let app = localidades::app(servico, topo);

    let endereco = format!("{}:{}", cfg.host, cfg.porta);
    let ouvinte = match tokio::net::TcpListener::bind(&endereco).await {
        Ok(o) => o,
        Err(erro) => {
            eprintln!("não foi possível subir o servidor: {erro} ({endereco})");
            return ExitCode::from(1);
        }
    };
    // Encerra com SIGTERM ou Ctrl-C, terminando os pedidos em andamento (o verificar.sh manda SIGTERM).
    let encerrar = async {
        let mut termino = tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("sinal");
        tokio::select! {
            _ = termino.recv() => {}
            _ = tokio::signal::ctrl_c() => {}
        }
    };
    if let Err(erro) = axum::serve(ouvinte, app)
        .with_graceful_shutdown(encerrar)
        .await
    {
        eprintln!("o servidor parou com erro: {erro}");
        return ExitCode::from(1);
    }
    ExitCode::SUCCESS
}

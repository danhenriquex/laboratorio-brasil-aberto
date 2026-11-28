// Comando localidades: o serviço de localidades do E7. Lê a configuração LOCALIDADES_*, monta as peças e
// sobe o servidor HTTP. Configuração inválida impede a partida, com a mensagem do E1 e código de saída 2.
package main

import (
	"context"
	"errors"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/api"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/config"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/fonte"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/operacao"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/servico"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/transporte"
)

func main() {
	os.Exit(executar())
}

func executar() int {
	cfg, err := config.Carregar(os.Getenv)
	if err != nil {
		fmt.Fprintf(os.Stderr, "configuração inválida: %v\n", err)
		return 2
	}

	metricas := operacao.NovasMetricas()
	registro := operacao.NovoRegistro(os.Stdout)
	cliente := fonte.NovoCliente(cfg.IBGEURL, cfg.PrazoFonte, func(ctx context.Context, recurso string, segundos float64) {
		metricas.ObservarFonte(recurso, segundos)
		operacao.EstadoDe(ctx).SomarFonte(segundos)
	})
	servicoLocalidades := servico.Novo(cliente, servico.Opcoes{Validade: cfg.Validade, ItensMax: cfg.ItensMax})

	roteador := api.NovoRoteador(operacao.Observador(metricas, registro))
	roteador.RotaHTTP("GET /health", http.HandlerFunc(operacao.Saude))
	roteador.RotaHTTP("GET /metrics", metricas.Handler())
	api.RegistrarV1(roteador, servicoLocalidades)

	servidor := &http.Server{
		Addr:              net.JoinHostPort(cfg.Host, strconv.Itoa(cfg.Porta)),
		Handler:           roteador,
		ReadHeaderTimeout: 10 * time.Second,
	}

	// Encerra com SIGTERM ou SIGINT, terminando os pedidos em andamento (o verificar.sh manda SIGTERM).
	ctx, parar := signal.NotifyContext(context.Background(), syscall.SIGTERM, os.Interrupt)
	defer parar()
	ouvinte, err := net.Listen("tcp", servidor.Addr)
	if err != nil {
		fmt.Fprintf(os.Stderr, "não foi possível subir o servidor: %v\n", err)
		return 1
	}
	erro := make(chan error, 1)
	// O Ouvinte saneia a linha de cada pedido antes do net/http (lição da T044 do E4).
	go func() { erro <- servidor.Serve(transporte.Ouvinte(ouvinte)) }()

	select {
	case err := <-erro:
		if !errors.Is(err, http.ErrServerClosed) {
			fmt.Fprintf(os.Stderr, "não foi possível subir o servidor: %v\n", err)
			return 1
		}
	case <-ctx.Done():
		encerrar, cancelar := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancelar()
		_ = servidor.Shutdown(encerrar)
	}
	return 0
}

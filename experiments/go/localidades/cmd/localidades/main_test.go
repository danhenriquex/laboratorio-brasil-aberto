package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/api"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/operacao"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/testeapoio"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/transporte"
)

// servidorComoNoMain sobe um servidor de teste com as mesmas opções do http.Server do main.
func servidorComoNoMain(t *testing.T) *httptest.Server {
	t.Helper()
	rt := api.NovoRoteador(nil)
	rt.RotaHTTP("GET /health", http.HandlerFunc(operacao.Saude))
	srv := httptest.NewUnstartedServer(rt)
	srv.Config = novoServidor("", rt)
	srv.Listener = transporte.Ouvinte(srv.Listener)
	srv.Start()
	t.Cleanup(srv.Close)
	return srv
}

// Convergência do E7 (T044): sem DisableGeneralOptionsHandler, o http.Server responde sozinho ao
// "OPTIONS *" com 200 vazio, sem passar pelo handler de topo e, portanto, sem correlação.
func TestOptionsAsteriscoPassaPeloHandlerDeTopo(t *testing.T) {
	srv := servidorComoNoMain(t)
	r := testeapoio.PedidoCru(t, srv, "OPTIONS", "*", "X-Correlation-Id: asterisco-1")
	if r.StatusCode != 404 || r.Header.Get("Content-Type") != "application/problem+json" {
		t.Fatalf("OPTIONS * = %d %q %q", r.StatusCode, r.Header.Get("Content-Type"), r.Corpo)
	}
	if r.Header.Get(operacao.Cabecalho) != "asterisco-1" {
		t.Errorf("correlação %q", r.Header.Get(operacao.Cabecalho))
	}
	var p map[string]any
	if err := json.Unmarshal(r.Corpo, &p); err != nil || p["type"] != "urn:brasil-aberto:problema:nao-encontrado" || p["correlacao_id"] != "asterisco-1" {
		t.Errorf("problema %v (%v)", p, err)
	}
	if h := testeapoio.PedidoCru(t, srv, "GET", "/health"); h.StatusCode != 200 {
		t.Errorf("o /health continua respondendo: %d", h.StatusCode)
	}
}

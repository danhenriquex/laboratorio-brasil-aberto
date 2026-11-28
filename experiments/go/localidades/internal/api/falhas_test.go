package api

import (
	"context"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/testeapoio"
)

// Mesmos casos do test_api_falhas.py do E1 e do ApiFalhasTest.java do E4 (US3).

func TestFalhasDaFonteSemCopia(t *testing.T) {
	casos := []struct {
		nome     string
		resposta testeapoio.Resposta
		status   int
		tipo     string
	}{
		{"fonte fora", testeapoio.Resposta{Status: 503, Corpo: []byte("fora")}, 502, "fonte-indisponivel"},
		{"resposta inválida", testeapoio.Resposta{Corpo: testeapoio.Fixture(t, "erro.html"), Tipo: "text/html"}, 502, "resposta-inesperada-da-fonte"},
		{"fonte lenta", testeapoio.Resposta{Corpo: testeapoio.Fixture(t, "estados.json"), Atraso: 500 * time.Millisecond}, 504, "fonte-lenta"},
	}
	for _, c := range casos {
		a := novoAmbienteComPrazo(t, 100*time.Millisecond)
		a.ibge.Responder("/estados", c.resposta)
		inicio := time.Now()
		w := a.get("/v1/ufs")
		conferirProblema(t, w.Code, w.Header(), w.Body.Bytes(), c.status, c.tipo)
		if time.Since(inicio) > 400*time.Millisecond {
			t.Errorf("%s: o pedido passou do prazo: %v", c.nome, time.Since(inicio))
		}
		if strings.Contains(strings.ToLower(w.Body.String()), "<html") {
			t.Errorf("%s: o corpo do IBGE vazou: %s", c.nome, w.Body)
		}
	}
}

func TestCopiaValidaNaoConsultaAFonte(t *testing.T) {
	a := novoAmbiente(t)
	a.estados()
	primeira := corpoJSON(t, a.get("/v1/ufs").Body.Bytes())
	a.relogio.Avancar(23 * time.Hour)
	segunda := corpoJSON(t, a.get("/v1/ufs").Body.Bytes())
	if a.ibge.Pedidos("/estados") != 1 {
		t.Errorf("a fonte foi consultada %d vezes", a.ibge.Pedidos("/estados"))
	}
	if segunda["meta"].(map[string]any)["coletado_em"] != primeira["meta"].(map[string]any)["coletado_em"] {
		t.Error("a cópia mantém o coletado_em da consulta original")
	}
	// /v1/ufs e /v1/ufs/{uf} usam o mesmo recurso do IBGE
	a.get("/v1/ufs/RJ")
	if a.ibge.Pedidos("/estados") != 1 {
		t.Errorf("/v1/ufs/RJ deveria usar a mesma cópia: %d consultas", a.ibge.Pedidos("/estados"))
	}
}

func TestCopiaVencidaServidaQuandoAFonteCai(t *testing.T) {
	a := novoAmbiente(t)
	a.estados()
	primeira := corpoJSON(t, a.get("/v1/ufs").Body.Bytes())
	a.relogio.Avancar(25 * time.Hour)
	a.ibge.Responder("/estados", testeapoio.Resposta{Status: 503, Corpo: []byte("fora")})
	w := a.get("/v1/ufs")
	if w.Code != 200 {
		t.Fatalf("status %d %s", w.Code, w.Body)
	}
	corpo := corpoJSON(t, w.Body.Bytes())
	conferirMeta(t, corpo, a.ibge.URL()+"/estados", true)
	if corpo["meta"].(map[string]any)["coletado_em"] != primeira["meta"].(map[string]any)["coletado_em"] {
		t.Error("a cópia vencida mantém o coletado_em original")
	}
	if a.ibge.Pedidos("/estados") != 2 {
		t.Errorf("com a cópia vencida, a fonte é consultada de novo: %d", a.ibge.Pedidos("/estados"))
	}
}

// Pedidos simultâneos com a fonte travada não fazem fila: uma consulta só, e todos recebem 504 no prazo.
func TestPedidosSimultaneosComAFonteTravada(t *testing.T) {
	a := novoAmbienteComPrazo(t, 200*time.Millisecond)
	a.ibge.Responder("/estados", testeapoio.Resposta{Corpo: testeapoio.Fixture(t, "estados.json"), Bloquear: make(chan struct{})})
	var wg sync.WaitGroup
	status := make([]int, 5)
	inicio := time.Now()
	for i := range 5 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			status[i] = a.get("/v1/ufs").Code
		}()
	}
	wg.Wait()
	for i, s := range status {
		if s != 504 {
			t.Errorf("pedido %d: status %d", i, s)
		}
	}
	if time.Since(inicio) > 600*time.Millisecond || a.ibge.Pedidos("/estados") != 1 {
		t.Errorf("demorou %v e fez %d consultas", time.Since(inicio), a.ibge.Pedidos("/estados"))
	}
}

// Um pedido cujo cliente desiste não cancela a consulta dos outros, e não conta como erro interno.
func TestClienteQueDesisteNaoAtrapalhaOsOutros(t *testing.T) {
	a := novoAmbiente(t)
	soltar := make(chan struct{})
	a.ibge.Responder("/estados", testeapoio.Resposta{Corpo: testeapoio.Fixture(t, "estados.json"), Bloquear: soltar})

	ctx, desistir := context.WithCancel(context.Background())
	desistente := httptest.NewRecorder()
	feito := make(chan struct{})
	go func() {
		a.handler.ServeHTTP(desistente, httptest.NewRequest("GET", "/v1/ufs", nil).WithContext(ctx))
		close(feito)
	}()
	time.Sleep(30 * time.Millisecond)
	outro := make(chan int, 1)
	go func() { outro <- a.get("/v1/ufs").Code }()
	time.Sleep(30 * time.Millisecond)
	desistir()
	<-feito
	close(soltar)
	if s := <-outro; s != 200 {
		t.Errorf("o outro pedido recebeu %d", s)
	}
	if desistente.Code == 500 {
		t.Error("cliente que desiste não é erro interno")
	}
	if a.ibge.Pedidos("/estados") != 1 {
		t.Errorf("%d consultas", a.ibge.Pedidos("/estados"))
	}
}

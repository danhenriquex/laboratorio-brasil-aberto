package testeapoio

import (
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"
)

// Resposta simulada para um caminho do IBGE.
type Resposta struct {
	Status int
	Corpo  []byte
	Tipo   string
	Atraso time.Duration
	// Bloquear, se não for nil, segura a resposta até o canal ser fechado (fonte "travada").
	Bloquear chan struct{}
}

// IBGE é um httptest.Server em 127.0.0.1 que responde pelos caminhos registrados e conta os pedidos.
type IBGE struct {
	Servidor *httptest.Server

	mu        sync.Mutex
	respostas map[string]Resposta
	contagem  map[string]int
	userAgent string
}

const prefixo = "/api/v1/localidades"

func NovoIBGE(t testing.TB) *IBGE {
	t.Helper()
	i := &IBGE{respostas: map[string]Resposta{}, contagem: map[string]int{}}
	i.Servidor = httptest.NewServer(http.HandlerFunc(i.atender))
	t.Cleanup(i.Servidor.Close)
	return i
}

// URL é a base que o serviço usa como LOCALIDADES_IBGE_URL.
func (i *IBGE) URL() string { return i.Servidor.URL + prefixo }

// Responder registra a resposta de um caminho relativo à base, como "/estados".
func (i *IBGE) Responder(caminho string, r Resposta) {
	i.mu.Lock()
	defer i.mu.Unlock()
	if r.Status == 0 {
		r.Status = http.StatusOK
	}
	if r.Tipo == "" {
		r.Tipo = "application/json"
	}
	i.respostas[caminho] = r
}

// ResponderFixture serve uma fixture de contracts/localidades/fixtures-ibge com status 200.
func (i *IBGE) ResponderFixture(t testing.TB, caminho, fixture string) {
	t.Helper()
	i.Responder(caminho, Resposta{Corpo: Fixture(t, fixture)})
}

// Pedidos devolve quantos pedidos chegaram a um caminho relativo à base.
func (i *IBGE) Pedidos(caminho string) int {
	i.mu.Lock()
	defer i.mu.Unlock()
	return i.contagem[caminho]
}

// Total devolve quantos pedidos chegaram, em qualquer caminho.
func (i *IBGE) Total() int {
	i.mu.Lock()
	defer i.mu.Unlock()
	total := 0
	for _, n := range i.contagem {
		total += n
	}
	return total
}

// UserAgent do último pedido recebido.
func (i *IBGE) UserAgent() string {
	i.mu.Lock()
	defer i.mu.Unlock()
	return i.userAgent
}

// Zerar esquece as respostas e a contagem.
func (i *IBGE) Zerar() {
	i.mu.Lock()
	defer i.mu.Unlock()
	i.respostas = map[string]Resposta{}
	i.contagem = map[string]int{}
}

func (i *IBGE) atender(w http.ResponseWriter, r *http.Request) {
	caminho := r.URL.Path
	if len(caminho) >= len(prefixo) && caminho[:len(prefixo)] == prefixo {
		caminho = caminho[len(prefixo):]
	}
	i.mu.Lock()
	i.contagem[caminho]++
	i.userAgent = r.Header.Get("User-Agent")
	resposta, ok := i.respostas[caminho]
	i.mu.Unlock()

	if !ok {
		http.Error(w, "caminho não simulado: "+caminho, http.StatusTeapot)
		return
	}
	if resposta.Bloquear != nil {
		select {
		case <-resposta.Bloquear:
		case <-r.Context().Done():
			return
		}
	}
	if resposta.Atraso > 0 {
		select {
		case <-time.After(resposta.Atraso):
		case <-r.Context().Done():
			return
		}
	}
	w.Header().Set("Content-Type", resposta.Tipo)
	w.WriteHeader(resposta.Status)
	_, _ = w.Write(resposta.Corpo)
}

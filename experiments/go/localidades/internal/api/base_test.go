package api

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"regexp"
	"strings"
	"testing"
	"time"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/operacao"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/testeapoio"
)

var uuid4 = regexp.MustCompile(`^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$`)

// roteadorDeTeste tem o /health e duas rotas que falham: uma com panic e outra com erro comum.
func roteadorDeTeste() *Roteador {
	rt := NovoRoteador(nil)
	rt.RotaHTTP("GET /health", http.HandlerFunc(operacao.Saude))
	rt.Rota("GET /v1/_panico", func(http.ResponseWriter, *http.Request) error {
		panic("segredo interno /etc/passwd")
	})
	rt.Rota("GET /v1/_erro", func(http.ResponseWriter, *http.Request) error {
		return errors.New("segredo interno /etc/passwd")
	})
	return rt
}

func pedir(rt http.Handler, metodo, alvo string, cabecalhos ...string) *httptest.ResponseRecorder {
	r := httptest.NewRequest(metodo, alvo, nil)
	for i := 0; i+1 < len(cabecalhos); i += 2 {
		r.Header.Set(cabecalhos[i], cabecalhos[i+1])
	}
	w := httptest.NewRecorder()
	rt.ServeHTTP(w, r)
	return w
}

// conferirProblema é o assert_problema do E1: status, tipo, problem+json e correlação no corpo e no cabeçalho.
func conferirProblema(t *testing.T, status int, cabecalho http.Header, corpo []byte, statusEsperado int, tipo string) map[string]any {
	t.Helper()
	if status != statusEsperado {
		t.Fatalf("status %d, esperado %d; corpo %s", status, statusEsperado, corpo)
	}
	if ct := cabecalho.Get("Content-Type"); ct != "application/problem+json" {
		t.Errorf("Content-Type %q", ct)
	}
	var p map[string]any
	if err := json.Unmarshal(corpo, &p); err != nil {
		t.Fatalf("corpo não é JSON: %s", corpo)
	}
	if p["type"] != "urn:brasil-aberto:problema:"+tipo || p["status"] != float64(statusEsperado) {
		t.Errorf("problema %v", p)
	}
	if d, _ := p["detail"].(string); d == "" {
		t.Errorf("detail vazio: %v", p)
	}
	if p["correlacao_id"] != cabecalho.Get(operacao.Cabecalho) || cabecalho.Get(operacao.Cabecalho) == "" {
		t.Errorf("correlação %v no corpo e %q no cabeçalho", p["correlacao_id"], cabecalho.Get(operacao.Cabecalho))
	}
	return p
}

func TestHealth(t *testing.T) {
	w := pedir(roteadorDeTeste(), "GET", "/health")
	if w.Code != 200 || w.Body.String() != `{"status":"ok"}` || w.Header().Get("Content-Type") != "application/json" {
		t.Errorf("health = %d %q %q", w.Code, w.Header().Get("Content-Type"), w.Body.String())
	}
}

func TestRotaInexistenteEProblema404(t *testing.T) {
	for _, alvo := range []string{"/v2/ufs", "/ufs", "/nada", "/v1", "/"} {
		w := pedir(roteadorDeTeste(), "GET", alvo)
		p := conferirProblema(t, w.Code, w.Header(), w.Body.Bytes(), 404, "nao-encontrado")
		if p["detail"] != "a rota "+alvo+" não existe" {
			t.Errorf("%s: detail %v", alvo, p["detail"])
		}
	}
}

// O ServeMux responderia 405 para método não suportado; o contrato pede o mesmo 404 do E1.
func TestMetodoNaoSuportadoTambemE404(t *testing.T) {
	for _, metodo := range []string{"POST", "PUT", "DELETE", "PATCH"} {
		w := pedir(roteadorDeTeste(), metodo, "/health")
		conferirProblema(t, w.Code, w.Header(), w.Body.Bytes(), 404, "nao-encontrado")
	}
}

// T047 do E4: o TRACE é tratado como qualquer método não suportado, e nada do pedido volta ecoado.
func TestTraceE404SemEco(t *testing.T) {
	srv := httptest.NewServer(roteadorDeTeste())
	defer srv.Close()
	r := testeapoio.PedidoCru(t, srv, "TRACE", "/health", "X-Correlation-Id: trace-123", "Cookie: segredo=abc")
	conferirProblema(t, r.StatusCode, r.Header, r.Corpo, 404, "nao-encontrado")
	if r.Header.Get(operacao.Cabecalho) != "trace-123" {
		t.Errorf("correlação %q", r.Header.Get(operacao.Cabecalho))
	}
	if strings.Contains(r.Bruto, "segredo") || strings.Contains(r.Bruto, "TRACE /health") {
		t.Errorf("o TRACE ecoou o pedido:\n%s", r.Bruto)
	}
}

// O ServeMux redirecionaria esses caminhos (301/307); o contrato pede 404. T050 do E4: ";" não some.
func TestCaminhoIrregularE404SemRedirecionamento(t *testing.T) {
	srv := httptest.NewServer(roteadorDeTeste())
	defer srv.Close()
	for _, alvo := range []string{"//health", "/./health", "/x/../health", "/health;x", "/health;jsessionid=1", "/v1/%2e%2e/health"} {
		r := testeapoio.PedidoCru(t, srv, "GET", alvo, "X-Correlation-Id: caminho-1")
		if r.StatusCode >= 300 && r.StatusCode < 400 {
			t.Errorf("%s: redirecionou com %d para %q", alvo, r.StatusCode, r.Header.Get("Location"))
			continue
		}
		conferirProblema(t, r.StatusCode, r.Header, r.Corpo, 404, "nao-encontrado")
	}
}

func TestCorrelacaoValidaVoltaIgual(t *testing.T) {
	w := pedir(roteadorDeTeste(), "GET", "/health", operacao.Cabecalho, "teste-123_a.b")
	if w.Header().Get(operacao.Cabecalho) != "teste-123_a.b" {
		t.Errorf("correlação %q", w.Header().Get(operacao.Cabecalho))
	}
}

func TestCorrelacaoInvalidaETrocadaPorUUIDv4(t *testing.T) {
	for _, valor := range []string{"com espaço", "acentuação", strings.Repeat("x", 65), ""} {
		w := pedir(roteadorDeTeste(), "GET", "/health", operacao.Cabecalho, valor)
		if c := w.Header().Get(operacao.Cabecalho); !uuid4.MatchString(c) {
			t.Errorf("%q virou %q, esperado um UUID v4", valor, c)
		}
	}
	w := pedir(roteadorDeTeste(), "GET", "/health", operacao.Cabecalho, strings.Repeat("x", 64))
	if w.Header().Get(operacao.Cabecalho) != strings.Repeat("x", 64) {
		t.Error("64 caracteres ainda valem")
	}
}

func TestFalhaInternaE500SemRastro(t *testing.T) {
	for _, alvo := range []string{"/v1/_panico", "/v1/_erro"} {
		w := pedir(roteadorDeTeste(), "GET", alvo)
		p := conferirProblema(t, w.Code, w.Header(), w.Body.Bytes(), 500, "erro-interno")
		corpo := w.Body.String()
		if p["detail"] != "erro interno do serviço" || strings.Contains(corpo, "segredo") || strings.Contains(corpo, ".go") || strings.Contains(corpo, "goroutine") {
			t.Errorf("%s: o 500 vazou detalhe interno: %s", alvo, corpo)
		}
	}
}

// T048 do E4: o Accept não muda o formato; sucesso em application/json e erro em application/problem+json.
func TestAcceptEIgnorado(t *testing.T) {
	for _, aceita := range []string{"application/xml", "text/html", "text/plain", "application/problem+json"} {
		w := pedir(roteadorDeTeste(), "GET", "/health", "Accept", aceita)
		if w.Code != 200 || w.Header().Get("Content-Type") != "application/json" {
			t.Errorf("Accept %s: /health = %d %q", aceita, w.Code, w.Header().Get("Content-Type"))
		}
		w = pedir(roteadorDeTeste(), "GET", "/nada", "Accept", aceita)
		conferirProblema(t, w.Code, w.Header(), w.Body.Bytes(), 404, "nao-encontrado")
	}
}

func TestObservadorRecebeRotaEStatus(t *testing.T) {
	var rotas []string
	var status []int
	rt := NovoRoteador(func(_ *http.Request, e *operacao.Estado, s int, _ time.Duration) {
		rota, _, _, _, _ := e.Leitura()
		rotas = append(rotas, rota)
		status = append(status, s)
	})
	rt.RotaHTTP("GET /health", http.HandlerFunc(operacao.Saude))
	pedir(rt, "GET", "/health")
	pedir(rt, "GET", "/nada")
	pedir(rt, "POST", "/health")
	if strings.Join(rotas, ",") != "/health,nao-encontrado,nao-encontrado" || status[0] != 200 || status[1] != 404 || status[2] != 404 {
		t.Errorf("rotas %v, status %v", rotas, status)
	}
}

package operacao_test

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"regexp"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/api"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/fonte"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/operacao"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/servico"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/testeapoio"
)

// Mesmos casos do test_api_operacao.py do E1 e do OperacaoTest.java do E4 (US5).

// saidaSegura junta as linhas do registro, que podem vir de goroutines diferentes.
type saidaSegura struct {
	mu  sync.Mutex
	buf bytes.Buffer
}

func (s *saidaSegura) Write(p []byte) (int, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.buf.Write(p)
}

func (s *saidaSegura) linhas(t *testing.T) []map[string]any {
	s.mu.Lock()
	defer s.mu.Unlock()
	var linhas []map[string]any
	for _, l := range strings.Split(strings.TrimSpace(s.buf.String()), "\n") {
		if l == "" {
			continue
		}
		var m map[string]any
		if err := json.Unmarshal([]byte(l), &m); err != nil {
			t.Fatalf("linha do registro não é JSON: %q", l)
		}
		m["_bruto"] = l
		linhas = append(linhas, m)
	}
	return linhas
}

// montar sobe o serviço como o main faz, com métricas e registro, contra o IBGE simulado.
func montar(t *testing.T) (http.Handler, *testeapoio.IBGE, *saidaSegura) {
	t.Helper()
	ibge := testeapoio.NovoIBGE(t)
	ibge.ResponderFixture(t, "/estados", "estados.json")
	metricas := operacao.NovasMetricas()
	saida := &saidaSegura{}
	registro := operacao.NovoRegistro(saida)
	cliente := fonte.NovoCliente(ibge.URL(), time.Second, func(ctx context.Context, recurso string, s float64) {
		metricas.ObservarFonte(recurso, s)
		operacao.EstadoDe(ctx).SomarFonte(s)
	})
	s := servico.Novo(cliente, servico.Opcoes{Validade: time.Hour, ItensMax: 500})
	rt := api.NovoRoteador(operacao.Observador(metricas, registro))
	rt.RotaHTTP("GET /health", http.HandlerFunc(operacao.Saude))
	rt.RotaHTTP("GET /metrics", metricas.Handler())
	api.RegistrarV1(rt, s)
	return rt, ibge, saida
}

func pedir(h http.Handler, alvo string, cabecalhos ...string) *httptest.ResponseRecorder {
	r := httptest.NewRequest("GET", alvo, nil)
	for i := 0; i+1 < len(cabecalhos); i += 2 {
		r.Header.Set(cabecalhos[i], cabecalhos[i+1])
	}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}

func TestMetricasComOsNomesDoContrato(t *testing.T) {
	h, _, _ := montar(t)
	pedir(h, "/v1/ufs")
	pedir(h, "/v1/ufs/RJ") // mesma cópia: acerto
	pedir(h, "/v1/municipios/12ab")
	pedir(h, "/nada")
	w := pedir(h, "/metrics")
	if w.Code != 200 || !strings.HasPrefix(w.Header().Get("Content-Type"), "text/plain") {
		t.Fatalf("/metrics = %d %q", w.Code, w.Header().Get("Content-Type"))
	}
	texto := w.Body.String()
	esperados := []string{
		`localidades_pedidos_total{rota="/v1/ufs",status="200"} 1`,
		`localidades_pedidos_total{rota="/v1/ufs/{uf}",status="200"} 1`,
		`localidades_pedidos_total{rota="/v1/municipios/{codigo}",status="400"} 1`,
		`localidades_pedidos_total{rota="nao-encontrado",status="404"} 1`,
		`localidades_erros_total{tipo="entrada-invalida"} 1`,
		`localidades_erros_total{tipo="nao-encontrado"} 1`,
		`localidades_cache_total{resultado="falta"} 1`,
		`localidades_cache_total{resultado="acerto"} 1`,
		`localidades_fonte_duracao_segundos_count{recurso="estados"} 1`,
	}
	for _, e := range esperados {
		if !strings.Contains(texto, e) {
			t.Errorf("faltou %s", e)
		}
	}
	// As mesmas faixas do E1, sem sufixo de unidade no nome.
	for _, faixa := range []string{"0.05", "0.1", "0.25", "0.5", "1", "2.5", "5", "10", "+Inf"} {
		if !strings.Contains(texto, `localidades_fonte_duracao_segundos_bucket{recurso="estados",le="`+faixa+`"}`) {
			t.Errorf("faltou a faixa %s do histograma", faixa)
		}
	}
	if strings.Contains(texto, "localidades_fonte_duracao_segundos_seconds") {
		t.Error("o nome do histograma ganhou sufixo de unidade")
	}
}

func TestMetricasEmTextoComQualquerAccept(t *testing.T) {
	h, _, _ := montar(t)
	for _, aceita := range []string{"application/json", "application/xml",
		"application/vnd.google.protobuf;proto=io.prometheus.client.MetricFamily;encoding=delimited",
		"application/openmetrics-text; version=1.0.0"} {
		w := pedir(h, "/metrics", "Accept", aceita)
		if w.Code != 200 || !strings.HasPrefix(w.Header().Get("Content-Type"), "text/plain") {
			t.Errorf("Accept %s: %d %q", aceita, w.Code, w.Header().Get("Content-Type"))
		}
	}
}

var momento = regexp.MustCompile(`^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$`)

func TestRegistroUmaLinhaJSONPorPedido(t *testing.T) {
	h, _, saida := montar(t)
	pedir(h, "/v1/ufs", "X-Correlation-Id", "registro-1")
	pedir(h, "/v1/ufs", "X-Correlation-Id", "registro-2")
	pedir(h, "/nada", "X-Correlation-Id", "registro-3")
	linhas := saida.linhas(t)
	if len(linhas) != 3 {
		t.Fatalf("%d linhas, esperado 3", len(linhas))
	}
	campos := []string{"momento", "nivel", "correlacao_id", "metodo", "rota", "status", "duracao_ms", "cache", "fonte_ms"}
	for _, l := range linhas {
		for _, c := range campos {
			if _, tem := l[c]; !tem {
				t.Errorf("linha sem %s: %s", c, l["_bruto"])
			}
		}
		if len(l) != len(campos)+1 {
			t.Errorf("campos a mais (IP, cabeçalhos?): %s", l["_bruto"])
		}
		if !momento.MatchString(l["momento"].(string)) {
			t.Errorf("momento fora do formato: %v", l["momento"])
		}
		if !strings.HasPrefix(l["_bruto"].(string), `{"momento":`) {
			t.Errorf("os campos não começam por momento: %s", l["_bruto"])
		}
	}
	primeira, segunda, terceira := linhas[0], linhas[1], linhas[2]
	if primeira["correlacao_id"] != "registro-1" || primeira["rota"] != "/v1/ufs" || primeira["status"] != 200.0 ||
		primeira["nivel"] != "info" || primeira["metodo"] != "GET" || primeira["cache"] != "falta" || primeira["fonte_ms"] == nil {
		t.Errorf("primeira linha: %s", primeira["_bruto"])
	}
	if segunda["cache"] != "acerto" || segunda["fonte_ms"] != nil {
		t.Errorf("com a cópia, não há tempo de fonte: %s", segunda["_bruto"])
	}
	if terceira["rota"] != "nao-encontrado" || terceira["status"] != 404.0 || terceira["cache"] != nil {
		t.Errorf("rota inexistente: %s", terceira["_bruto"])
	}
}

func TestRegistroComNivelErrorNo500(t *testing.T) {
	saida := &saidaSegura{}
	registro := operacao.NovoRegistro(saida)
	rt := api.NovoRoteador(operacao.Observador(operacao.NovasMetricas(), registro))
	rt.Rota("GET /v1/_panico", func(http.ResponseWriter, *http.Request) error { panic("falha") })
	pedir(rt, "/v1/_panico")
	linhas := saida.linhas(t)
	if len(linhas) != 1 || linhas[0]["nivel"] != "error" || linhas[0]["status"] != 500.0 {
		t.Errorf("registro do 500: %v", linhas)
	}
	_ = io.Discard
}

package operacao

import (
	"net/http"
	"strconv"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/collectors"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// faixasFonteS são as mesmas faixas do histograma do E1.
var faixasFonteS = []float64{0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10}

// Metricas usa um registro próprio, e não o global, para cada montagem ter as suas séries (research R10).
// O cliente do Go não impõe sufixo de unidade: os nomes saem exatamente como no contrato.
type Metricas struct {
	registro *prometheus.Registry
	pedidos  *prometheus.CounterVec
	erros    *prometheus.CounterVec
	cache    *prometheus.CounterVec
	fonte    *prometheus.HistogramVec
}

func NovasMetricas() *Metricas {
	m := &Metricas{
		registro: prometheus.NewRegistry(),
		pedidos: prometheus.NewCounterVec(prometheus.CounterOpts{
			Name: "localidades_pedidos_total", Help: "Pedidos atendidos, por modelo de rota e status.",
		}, []string{"rota", "status"}),
		erros: prometheus.NewCounterVec(prometheus.CounterOpts{
			Name: "localidades_erros_total", Help: "Erros devolvidos, por tipo de problema.",
		}, []string{"tipo"}),
		cache: prometheus.NewCounterVec(prometheus.CounterOpts{
			Name: "localidades_cache_total", Help: "Uso da cópia guardada: acerto, falta ou desatualizado.",
		}, []string{"resultado"}),
		fonte: prometheus.NewHistogramVec(prometheus.HistogramOpts{
			Name: "localidades_fonte_duracao_segundos", Help: "Duração das consultas ao IBGE, por recurso.",
			Buckets: faixasFonteS,
		}, []string{"recurso"}),
	}
	// Os coletores de runtime do Go entram como o E4 expõe os da JVM.
	m.registro.MustRegister(m.pedidos, m.erros, m.cache, m.fonte,
		collectors.NewGoCollector(), collectors.NewProcessCollector(collectors.ProcessCollectorOpts{}))
	return m
}

func (m *Metricas) ObservarFonte(recurso string, segundos float64) {
	m.fonte.WithLabelValues(recurso).Observe(segundos)
}

func (m *Metricas) RegistrarPedido(rota string, status int, tipoErro, cache string) {
	m.pedidos.WithLabelValues(rota, strconv.Itoa(status)).Inc()
	if tipoErro != "" {
		m.erros.WithLabelValues(tipoErro).Inc()
	}
	if cache != "" {
		m.cache.WithLabelValues(cache).Inc()
	}
}

// Handler expõe as métricas sempre no formato texto do Prometheus. O promhttp negocia pelo Accept (pode
// devolver protobuf ou OpenMetrics); o Accept é retirado antes, como em todo o serviço (T048 do E4).
func (m *Metricas) Handler() http.Handler {
	h := promhttp.HandlerFor(m.registro, promhttp.HandlerOpts{})
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		r = r.Clone(r.Context())
		r.Header.Del("Accept")
		h.ServeHTTP(w, r)
	})
}

package operacao

import (
	"context"
	"io"
	"log/slog"
	"math"
	"net/http"
	"time"
)

// Registro escreve uma linha JSON por pedido, com os campos do E1: momento, nivel, correlacao_id, metodo,
// rota, status, duracao_ms, cache e fonte_ms. Não registra IP nem cabeçalhos além da correlação
// (Constituição VII). Usa o log/slog da biblioteca padrão (research R12).
type Registro struct {
	logger *slog.Logger
}

func NovoRegistro(saida io.Writer) *Registro {
	h := slog.NewJSONHandler(saida, &slog.HandlerOptions{
		ReplaceAttr: func(grupos []string, a slog.Attr) slog.Attr {
			if len(grupos) > 0 {
				return a
			}
			switch a.Key {
			case slog.TimeKey:
				return slog.String("momento", a.Value.Time().UTC().Format("2006-01-02T15:04:05.000Z07:00"))
			case slog.LevelKey:
				nivel := "info"
				if a.Value.Any().(slog.Level) >= slog.LevelError {
					nivel = "error"
				}
				return slog.String("nivel", nivel)
			case slog.MessageKey:
				return slog.Attr{} // o E1 não tem mensagem: a linha é o pedido
			}
			return a
		},
	})
	return &Registro{logger: slog.New(h)}
}

func umaCasa(x float64) float64 { return math.Round(x*10) / 10 }

func textoOuNulo(s string) any {
	if s == "" {
		return nil
	}
	return s
}

// Pedido escreve a linha de um pedido terminado. 5xx sai com nivel "error", o resto com "info".
func (r *Registro) Pedido(correlacao, metodo, rota string, status int, duracao time.Duration, cache string, fonteS float64, temFonte bool) {
	nivel := slog.LevelInfo
	if status >= 500 {
		nivel = slog.LevelError
	}
	var fonteMs any
	if temFonte {
		fonteMs = umaCasa(fonteS * 1000)
	}
	r.logger.LogAttrs(context.Background(), nivel, "",
		slog.String("correlacao_id", correlacao),
		slog.String("metodo", metodo),
		slog.String("rota", rota),
		slog.Int("status", status),
		slog.Float64("duracao_ms", umaCasa(float64(duracao.Microseconds())/1000)),
		slog.Any("cache", textoOuNulo(cache)),
		slog.Any("fonte_ms", fonteMs),
	)
}

// Observador junta métricas e registro no fim de cada pedido. A assinatura é a do api.Observador.
func Observador(m *Metricas, reg *Registro) func(*http.Request, *Estado, int, time.Duration) {
	return func(r *http.Request, e *Estado, status int, duracao time.Duration) {
		rota, cache, tipoErro, fonteS, temFonte := e.Leitura()
		m.RegistrarPedido(rota, status, tipoErro, cache)
		reg.Pedido(e.Correlacao, r.Method, rota, status, duracao, cache, fonteS, temFonte)
	}
}

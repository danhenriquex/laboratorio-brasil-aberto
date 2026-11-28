// Package operacao tem o que é da operação do serviço: correlação, estado do pedido, saúde, métricas e
// registro (US5 do E1; research do E7, R10 e R12).
package operacao

import (
	"context"
	"crypto/rand"
	"fmt"
	"regexp"
	"sync"
)

// Cabecalho de correlação, devolvido em toda resposta.
const Cabecalho = "X-Correlation-Id"

var correlacaoValida = regexp.MustCompile(`^[A-Za-z0-9._-]{1,64}$`)

// CorrelacaoDe aplica a regra do R12 do E1: aceita de 1 a 64 caracteres em [A-Za-z0-9._-]; senão, gera um
// UUID v4.
func CorrelacaoDe(valor string) string {
	if correlacaoValida.MatchString(valor) {
		return valor
	}
	return uuidV4()
}

func uuidV4() string {
	var b [16]byte
	_, _ = rand.Read(b[:])
	b[6] = b[6]&0x0f | 0x40 // versão 4
	b[8] = b[8]&0x3f | 0x80 // variante RFC 4122
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:16])
}

// Estado guarda o que o registro e as métricas precisam saber de um pedido: correlação, modelo da rota,
// uso da cópia, tipo de erro e tempo gasto com o IBGE. Viaja no context.Context do pedido.
type Estado struct {
	Correlacao string

	mu       sync.Mutex
	rota     string
	cache    string
	tipoErro string
	fonteS   float64
	temFonte bool
}

func NovoEstado(cabecalho string) *Estado {
	return &Estado{Correlacao: CorrelacaoDe(cabecalho), rota: "nao-encontrado"}
}

func (e *Estado) DefinirRota(rota string) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.rota = rota
}

func (e *Estado) DefinirCache(resultado string) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.cache = resultado
}

func (e *Estado) DefinirTipoErro(tipo string) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.tipoErro = tipo
}

// SomarFonte acumula o tempo de uma consulta ao IBGE feita por este pedido.
func (e *Estado) SomarFonte(segundos float64) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.fonteS += segundos
	e.temFonte = true
}

// Leitura devolve uma cópia dos campos, para o registro e as métricas no fim do pedido.
func (e *Estado) Leitura() (rota, cache, tipoErro string, fonteS float64, temFonte bool) {
	e.mu.Lock()
	defer e.mu.Unlock()
	return e.rota, e.cache, e.tipoErro, e.fonteS, e.temFonte
}

type chaveEstado struct{}

func ComEstado(ctx context.Context, e *Estado) context.Context {
	return context.WithValue(ctx, chaveEstado{}, e)
}

// EstadoDe devolve o estado do pedido. Fora de um pedido (em testes de unidade, por exemplo), devolve um
// estado descartável, para quem anota não precisar checar nil.
func EstadoDe(ctx context.Context) *Estado {
	if e, ok := ctx.Value(chaveEstado{}).(*Estado); ok {
		return e
	}
	return NovoEstado("")
}

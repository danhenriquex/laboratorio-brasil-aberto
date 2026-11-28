// Package cache guarda a cópia de cada recurso do IBGE com validade, faz uma consulta só por chave e serve a
// cópia vencida quando a fonte falha (R5 do E1; research do E7, R7). Em memória do processo (Constituição
// X: sem Redis enquanto houver um processo).
//
// Estados de uma entrada (data-model do E1): ausente → válida → vencida. "Não encontrado" e erros nunca
// entram na cópia.
//
// Consulta única (T050 do E1): pedidos simultâneos pelo mesmo recurso aguardam a mesma consulta e recebem
// o mesmo resultado, inclusive o erro. Ninguém espera em fila por mais de um prazo, e a fonte com problema
// recebe uma consulta só. O singleflight faz exatamente isso: "If a duplicate comes in, the duplicate caller
// waits for the original to complete and receives the same results".
package cache

import (
	"context"
	"errors"
	"sync"
	"time"

	"golang.org/x/sync/singleflight"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/erros"
)

// Entrada é o que o serviço recebe: os dados, a procedência e o uso da cópia (acerto, falta, desatualizado).
type Entrada struct {
	Dados         any
	URLFonte      string
	ColetadoEm    time.Time
	Desatualizado bool
	Resultado     string
}

// Buscar consulta a fonte e devolve os dados normalizados e a URL consultada.
type Buscar func(ctx context.Context) (any, string, error)

type guardada struct {
	dados      any
	urlFonte   string
	coletadoEm time.Time
	expiraEm   time.Duration // no relógio monotônico
}

type Cache struct {
	agora      func() time.Time
	monotonico func() time.Duration
	validade   time.Duration

	mu        sync.Mutex
	guardadas map[string]guardada
	grupo     singleflight.Group
}

func Novo(agora func() time.Time, monotonico func() time.Duration, validade time.Duration) *Cache {
	return &Cache{agora: agora, monotonico: monotonico, validade: validade, guardadas: map[string]guardada{}}
}

func (c *Cache) guardada(chave string) (guardada, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	g, ok := c.guardadas[chave]
	return g, ok
}

func (c *Cache) valida(chave string) (guardada, bool) {
	g, ok := c.guardada(chave)
	return g, ok && c.monotonico() < g.expiraEm
}

// Obter devolve a cópia válida ou consulta a fonte. Cada pedido espera a consulta no próprio contexto: um
// pedido que desiste recebe context.Canceled, mas a consulta continua para os outros (o shield do E1).
func (c *Cache) Obter(ctx context.Context, chave string, buscar Buscar) (Entrada, error) {
	if g, ok := c.valida(chave); ok {
		return Entrada{Dados: g.dados, URLFonte: g.urlFonte, ColetadoEm: g.coletadoEm, Resultado: "acerto"}, nil
	}

	// Só o pedido cuja função o singleflight executa inicia a consulta; para os outros, é um acerto.
	// A escrita em iniciou acontece antes do envio no canal, que acontece antes da leitura aqui.
	iniciou := false
	resultado := c.grupo.DoChan(chave, func() (any, error) {
		iniciou = true
		// Uma consulta que terminou entre a checagem acima e este ponto já deixou a cópia válida.
		if g, ok := c.valida(chave); ok {
			return Entrada{Dados: g.dados, URLFonte: g.urlFonte, ColetadoEm: g.coletadoEm, Resultado: "acerto"}, nil
		}
		// A consulta não morre com o pedido que a iniciou; o prazo dela é o da fonte.
		consulta := context.WithoutCancel(ctx)
		coletadoEm := c.agora()
		dados, url, err := buscar(consulta)
		if err != nil {
			return nil, err
		}
		c.mu.Lock()
		c.guardadas[chave] = guardada{dados, url, coletadoEm, c.monotonico() + c.validade}
		c.mu.Unlock()
		return Entrada{Dados: dados, URLFonte: url, ColetadoEm: coletadoEm, Resultado: "falta"}, nil
	})

	select {
	case <-ctx.Done():
		return Entrada{}, ctx.Err()
	case r := <-resultado:
		if r.Err != nil {
			return c.vencidaOuErro(chave, r.Err)
		}
		entrada := r.Val.(Entrada)
		if !iniciou {
			entrada.Resultado = "acerto"
		}
		return entrada, nil
	}
}

// vencidaOuErro serve a cópia vencida quando a falha é da fonte; qualquer outro erro sobe.
func (c *Cache) vencidaOuErro(chave string, err error) (Entrada, error) {
	var e *erros.ErroDominio
	if !errors.As(err, &e) || !e.DeFonte() {
		return Entrada{}, err
	}
	g, ok := c.guardada(chave)
	if !ok {
		return Entrada{}, err
	}
	return Entrada{Dados: g.dados, URLFonte: g.urlFonte, ColetadoEm: g.coletadoEm, Desatualizado: true, Resultado: "desatualizado"}, nil
}

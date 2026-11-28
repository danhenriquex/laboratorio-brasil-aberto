package cache

import (
	"context"
	"errors"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/erros"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/testeapoio"
)

// Mesmos casos do test_cache.py do E1 e do CacheComValidadeTest.java do E4.

const validade = 24 * time.Hour

func novoCache() (*Cache, *testeapoio.Relogio) {
	r := testeapoio.NovoRelogio()
	return Novo(r.Agora, r.Monotonico, validade), r
}

// fonteContada devolve um Buscar que conta as chamadas e responde com dados fixos ou com um erro.
func fonteContada(dados any, err error) (Buscar, *atomic.Int32) {
	var n atomic.Int32
	return func(context.Context) (any, string, error) {
		n.Add(1)
		if err != nil {
			return nil, "", err
		}
		return dados, "https://ibge/estados", nil
	}, &n
}

func TestAcertoDentroDaValidade(t *testing.T) {
	c, r := novoCache()
	buscar, n := fonteContada("dados", nil)
	primeira, err := c.Obter(context.Background(), "estados", buscar)
	if err != nil || primeira.Resultado != "falta" || primeira.Dados != "dados" || primeira.URLFonte != "https://ibge/estados" {
		t.Fatalf("primeira = %+v, %v", primeira, err)
	}
	r.Avancar(validade - time.Second)
	segunda, err := c.Obter(context.Background(), "estados", buscar)
	if err != nil || segunda.Resultado != "acerto" || !segunda.ColetadoEm.Equal(primeira.ColetadoEm) || segunda.Desatualizado {
		t.Errorf("segunda = %+v, %v", segunda, err)
	}
	if n.Load() != 1 {
		t.Errorf("a fonte foi consultada %d vezes", n.Load())
	}
}

func TestFaltaDepoisDaValidade(t *testing.T) {
	c, r := novoCache()
	buscar, n := fonteContada("dados", nil)
	primeira, _ := c.Obter(context.Background(), "estados", buscar)
	r.Avancar(validade)
	segunda, err := c.Obter(context.Background(), "estados", buscar)
	if err != nil || segunda.Resultado != "falta" || !segunda.ColetadoEm.After(primeira.ColetadoEm) || n.Load() != 2 {
		t.Errorf("depois da validade: %+v, %v, %d consultas", segunda, err, n.Load())
	}
}

func TestCopiaVencidaQuandoAFonteFalha(t *testing.T) {
	c, r := novoCache()
	buscar, _ := fonteContada("dados", nil)
	primeira, _ := c.Obter(context.Background(), "estados", buscar)
	r.Avancar(validade + time.Hour)
	falhar, _ := fonteContada(nil, erros.FonteIndisponivel("o IBGE respondeu com status 503"))
	vencida, err := c.Obter(context.Background(), "estados", falhar)
	if err != nil || !vencida.Desatualizado || vencida.Resultado != "desatualizado" || vencida.Dados != "dados" ||
		!vencida.ColetadoEm.Equal(primeira.ColetadoEm) {
		t.Errorf("vencida = %+v, %v", vencida, err)
	}
}

func TestErroDeFonteSemCopiaENaoEncontradoNaoSaoGuardados(t *testing.T) {
	c, _ := novoCache()
	lenta, nLenta := fonteContada(nil, erros.FonteLenta("o IBGE não respondeu em 10 s"))
	if _, err := c.Obter(context.Background(), "municipios/1", lenta); err == nil || err.Error() != "o IBGE não respondeu em 10 s" {
		t.Errorf("sem cópia, o erro de fonte sobe: %v", err)
	}
	c.Obter(context.Background(), "municipios/1", lenta)
	if nLenta.Load() != 2 {
		t.Errorf("erro não é guardado: %d consultas", nLenta.Load())
	}
	inexistente, n := fonteContada(nil, erros.NaoEncontrado("não existe município com o código 9999999"))
	c.Obter(context.Background(), "municipios/9999999", inexistente)
	_, err := c.Obter(context.Background(), "municipios/9999999", inexistente)
	var e *erros.ErroDominio
	if !errors.As(err, &e) || e.Tipo != "nao-encontrado" || n.Load() != 2 {
		t.Errorf("\"não encontrado\" não é guardado: %v, %d consultas", err, n.Load())
	}
}

// NaoEncontrado não é erro de fonte: com uma cópia vencida, ele não vira resposta desatualizada.
func TestNaoEncontradoNaoUsaCopiaVencida(t *testing.T) {
	c, r := novoCache()
	buscar, _ := fonteContada("dados", nil)
	c.Obter(context.Background(), "chave", buscar)
	r.Avancar(validade + time.Hour)
	inexistente, _ := fonteContada(nil, erros.NaoEncontrado("sumiu"))
	if _, err := c.Obter(context.Background(), "chave", inexistente); err == nil {
		t.Error("não encontrado deveria subir, e não virar cópia vencida")
	}
}

// fonteTravada só responde quando o teste solta, para pôr vários pedidos esperando a mesma consulta.
func fonteTravada(err error) (Buscar, chan struct{}, *atomic.Int32, *atomic.Bool) {
	soltar := make(chan struct{})
	var n atomic.Int32
	var cancelada atomic.Bool
	return func(ctx context.Context) (any, string, error) {
		n.Add(1)
		<-soltar
		cancelada.Store(ctx.Err() != nil)
		if err != nil {
			return nil, "", err
		}
		return "dados", "https://ibge/estados", nil
	}, soltar, &n, &cancelada
}

// Consulta única (T050 do E1): pedidos simultâneos aguardam a mesma consulta e recebem o mesmo resultado,
// inclusive o mesmo erro.
func TestPedidosSimultaneosFazemUmaConsulta(t *testing.T) {
	for _, falha := range []error{nil, erros.FonteLenta("o IBGE não respondeu em 10 s")} {
		c, _ := novoCache()
		buscar, soltar, n, _ := fonteTravada(falha)
		var wg sync.WaitGroup
		entradas := make([]Entrada, 20)
		errs := make([]error, 20)
		for i := range 20 {
			wg.Add(1)
			go func() {
				defer wg.Done()
				entradas[i], errs[i] = c.Obter(context.Background(), "estados", buscar)
			}()
		}
		time.Sleep(50 * time.Millisecond)
		close(soltar)
		wg.Wait()
		if n.Load() != 1 {
			t.Errorf("falha=%v: %d consultas, esperado 1", falha, n.Load())
		}
		faltas := 0
		for i := range 20 {
			if falha == nil && (errs[i] != nil || entradas[i].Dados != "dados") {
				t.Errorf("pedido %d: %+v, %v", i, entradas[i], errs[i])
			}
			if falha != nil && errs[i] != falha {
				t.Errorf("pedido %d: erro %v, esperado o mesmo erro da consulta", i, errs[i])
			}
			if entradas[i].Resultado == "falta" {
				faltas++
			}
		}
		if falha == nil && faltas != 1 {
			t.Errorf("só quem iniciou a consulta conta como falta; os outros são acerto: %d faltas", faltas)
		}
	}
}

// Um pedido que desiste não cancela a consulta que os outros esperam (o shield do E1).
func TestPedidoQueDesisteNaoCancelaAConsulta(t *testing.T) {
	c, _ := novoCache()
	buscar, soltar, n, cancelada := fonteTravada(nil)
	ctxA, cancelarA := context.WithCancel(context.Background())
	resA := make(chan error, 1)
	go func() {
		_, err := c.Obter(ctxA, "estados", buscar)
		resA <- err
	}()
	time.Sleep(20 * time.Millisecond)
	resB := make(chan Entrada, 1)
	go func() {
		e, _ := c.Obter(context.Background(), "estados", buscar)
		resB <- e
	}()
	time.Sleep(20 * time.Millisecond)
	cancelarA()
	if err := <-resA; !errors.Is(err, context.Canceled) {
		t.Errorf("quem desistiu recebe context.Canceled: %v", err)
	}
	close(soltar)
	if e := <-resB; e.Dados != "dados" {
		t.Errorf("o outro pedido recebe o resultado: %+v", e)
	}
	if cancelada.Load() || n.Load() != 1 {
		t.Errorf("a consulta foi cancelada (%v) ou repetida (%d)", cancelada.Load(), n.Load())
	}
}

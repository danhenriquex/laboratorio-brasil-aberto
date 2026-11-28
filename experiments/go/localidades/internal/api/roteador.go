package api

import (
	"context"
	"errors"
	"net/http"
	"strings"
	"time"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/erros"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/operacao"
)

// statusClienteDesistiu marca, no registro e nas métricas, o pedido cujo cliente foi embora antes da resposta.
const statusClienteDesistiu = 499

// Observador recebe cada pedido terminado, para métricas e registro (US5).
type Observador func(r *http.Request, estado *operacao.Estado, status int, duracao time.Duration)

// HandlerComErro devolve o erro em vez de escrevê-lo; o roteador o converte em problem+json.
type HandlerComErro func(w http.ResponseWriter, r *http.Request) error

// Roteador é o handler de topo (research do E7, R3). Ele decide antes do ServeMux o que o contrato pede e o
// ServeMux faria de outro jeito: redirecionar caminhos com ".", ".." ou "//" (301/307) e responder 405 para
// método não suportado. No contrato, os dois casos são 404 nao-encontrado em problem+json.
type Roteador struct {
	mux      *http.ServeMux
	observar Observador
}

func NovoRoteador(observar Observador) *Roteador {
	return &Roteador{mux: http.NewServeMux(), observar: observar}
}

// Rota registra um handler que devolve erro, com padrão de método e curinga ("GET /v1/ufs/{uf}").
func (rt *Roteador) Rota(padrao string, h HandlerComErro) {
	rt.mux.HandleFunc(padrao, func(w http.ResponseWriter, r *http.Request) {
		err := h(w, r)
		switch {
		case err == nil:
		case errors.Is(err, context.Canceled) && r.Context().Err() != nil:
			// O cliente desistiu: ninguém lê a resposta, e não é erro do serviço. O 499 (convenção do nginx)
			// só aparece no registro e nas métricas.
			w.WriteHeader(statusClienteDesistiu)
		default:
			EscreverProblema(w, r, err)
		}
	})
}

// RotaHTTP registra um http.Handler comum (como /health e /metrics).
func (rt *Roteador) RotaHTTP(padrao string, h http.Handler) {
	rt.mux.Handle(padrao, h)
}

func (rt *Roteador) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	inicio := time.Now()
	estado := operacao.NovoEstado(r.Header.Get(operacao.Cabecalho))
	r = r.WithContext(operacao.ComEstado(r.Context(), estado))
	w.Header().Set(operacao.Cabecalho, estado.Correlacao)
	g := &gravador{ResponseWriter: w}

	defer func() {
		if p := recover(); p != nil {
			if p == http.ErrAbortHandler {
				panic(p)
			}
			if !g.escreveu {
				EscreverProblema(g, r, erros.ErroInterno())
			}
		}
		if rt.observar != nil {
			rt.observar(r, estado, g.statusFinal(), time.Since(inicio))
		}
	}()

	if caminhoIrregular(r.URL.EscapedPath()) || caminhoIrregular(r.URL.Path) {
		EscreverProblema(g, r, rotaInexistente(r))
		return
	}
	// Com padrão vazio, o ServeMux responderia "page not found" (404 em texto) ou "method not supported"
	// (405). Os dois viram o 404 do contrato, inclusive para TRACE, sem ecoar nada (T047 do E4).
	if _, padrao := rt.mux.Handler(r); padrao == "" {
		EscreverProblema(g, r, rotaInexistente(r))
		return
	} else {
		estado.DefinirRota(modeloDaRota(padrao))
	}
	// O ServeMux casa de novo para preencher r.PathValue; o caminho já está limpo e o método já confere.
	rt.mux.ServeHTTP(g, r)
}

func rotaInexistente(r *http.Request) error {
	return erros.NaoEncontrado("a rota %s não existe", r.URL.Path)
}

// caminhoIrregular reconhece o que o ServeMux redirecionaria (segmentos "." e "..", barras repetidas) e os
// parâmetros de caminho com ";", que o Tomcat descartava no E4 (T050). Pela RFC 3986, o ";" faz parte do
// segmento, e nenhuma rota do contrato o tem.
func caminhoIrregular(caminho string) bool {
	if strings.Contains(caminho, ";") || strings.Contains(caminho, "//") {
		return true
	}
	for _, segmento := range strings.Split(caminho, "/") {
		if segmento == "." || segmento == ".." {
			return true
		}
	}
	return false
}

// modeloDaRota tira o método do padrão: "GET /v1/municipios/{codigo}" → "/v1/municipios/{codigo}".
func modeloDaRota(padrao string) string {
	if i := strings.IndexAny(padrao, " \t"); i >= 0 {
		return strings.TrimSpace(padrao[i:])
	}
	return padrao
}

// gravador guarda o status, para o registro e as métricas, e se a resposta já começou a ser escrita.
type gravador struct {
	http.ResponseWriter
	status   int
	escreveu bool
}

func (g *gravador) WriteHeader(status int) {
	if !g.escreveu {
		g.status = status
		g.escreveu = true
	}
	g.ResponseWriter.WriteHeader(status)
}

func (g *gravador) Write(b []byte) (int, error) {
	if !g.escreveu {
		g.WriteHeader(http.StatusOK)
	}
	return g.ResponseWriter.Write(b)
}

func (g *gravador) Unwrap() http.ResponseWriter { return g.ResponseWriter }

func (g *gravador) statusFinal() int {
	if g.status == 0 {
		return http.StatusOK
	}
	return g.status
}

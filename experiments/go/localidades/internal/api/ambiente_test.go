package api

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/fonte"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/operacao"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/servico"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/testeapoio"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/transporte"
)

// ambiente monta o serviço inteiro (cliente, serviço e roteador) contra o IBGE simulado, como o app de
// teste do E1 e o @SpringBootTest do E4.
type ambiente struct {
	t       *testing.T
	ibge    *testeapoio.IBGE
	relogio *testeapoio.Relogio
	handler http.Handler
	srv     *httptest.Server
}

func novoAmbiente(t *testing.T) *ambiente {
	t.Helper()
	return novoAmbienteComPrazo(t, time.Second)
}

func novoAmbienteComPrazo(t *testing.T, prazo time.Duration) *ambiente {
	t.Helper()
	ibge := testeapoio.NovoIBGE(t)
	relogio := testeapoio.NovoRelogio()
	cliente := fonte.NovoCliente(ibge.URL(), prazo, nil)
	s := servico.Novo(cliente, servico.Opcoes{
		Agora:      relogio.Agora,
		Monotonico: relogio.Monotonico,
		Validade:   24 * time.Hour,
		ItensMax:   500,
	})
	rt := NovoRoteador(nil)
	rt.RotaHTTP("GET /health", http.HandlerFunc(operacao.Saude))
	RegistrarV1(rt, s)
	return &ambiente{t: t, ibge: ibge, relogio: relogio, handler: rt}
}

func (a *ambiente) get(alvo string, cabecalhos ...string) *httptest.ResponseRecorder {
	a.t.Helper()
	return pedir(a.handler, "GET", alvo, cabecalhos...)
}

// cru manda o pedido escrito à mão a um servidor de verdade, para caminho e query chegarem como escritos.
func (a *ambiente) cru(alvo string, cabecalhos ...string) testeapoio.RespostaCrua {
	a.t.Helper()
	if a.srv == nil {
		// Com o mesmo Ouvinte do main, que saneia a linha do pedido antes do net/http (lição da T044 do E4).
		a.srv = httptest.NewUnstartedServer(a.handler)
		a.srv.Listener = transporte.Ouvinte(a.srv.Listener)
		a.srv.Start()
		a.t.Cleanup(a.srv.Close)
	}
	return testeapoio.PedidoCru(a.t, a.srv, "GET", alvo, cabecalhos...)
}

func (a *ambiente) estados() { a.ibge.ResponderFixture(a.t, "/estados", "estados.json") }
func (a *ambiente) rj() {
	a.ibge.ResponderFixture(a.t, "/estados/33/municipios", "municipios-uf-33.json")
}
func (a *ambiente) sp() {
	a.ibge.ResponderFixture(a.t, "/estados/35/municipios", "municipios-uf-35.json")
}

// corpoJSON decodifica a resposta num mapa genérico, como o r.json() do E1.
func corpoJSON(t *testing.T, corpo []byte) map[string]any {
	t.Helper()
	var m map[string]any
	if err := json.Unmarshal(corpo, &m); err != nil {
		t.Fatalf("corpo não é JSON: %s", corpo)
	}
	return m
}

// conferirMeta é o assert_meta do E1.
func conferirMeta(t *testing.T, corpo map[string]any, urlFonte string, desatualizado bool) {
	t.Helper()
	meta, _ := corpo["meta"].(map[string]any)
	if meta["fonte"] != "IBGE — API de localidades" || meta["url_fonte"] != urlFonte ||
		meta["url_documentacao"] != "https://servicodados.ibge.gov.br/api/docs/localidades" || meta["desatualizado"] != desatualizado {
		t.Errorf("meta = %v", meta)
	}
	if c, _ := meta["coletado_em"].(string); len(c) != len("2026-11-26T12:00:00.123Z") || c[len(c)-1] != 'Z' {
		t.Errorf("coletado_em fora do formato: %v", meta["coletado_em"])
	}
}

func nomesDe(t *testing.T, dados any) []string {
	t.Helper()
	lista, _ := dados.([]any)
	nomes := make([]string, 0, len(lista))
	for _, item := range lista {
		nomes = append(nomes, item.(map[string]any)["nome"].(string))
	}
	return nomes
}

// testeapoioResposta é uma resposta 200 do IBGE simulado com o corpo dado.
func testeapoioResposta(corpo string) testeapoio.Resposta {
	return testeapoio.Resposta{Corpo: []byte(corpo)}
}

// municipio serve em /municipios/<codigo> o item de uma lista de municípios das fixtures, como o IBGE
// falso da suíte faz.
func (a *ambiente) municipio(fixtureLista, codigo string) {
	a.t.Helper()
	var lista []map[string]any
	if err := json.Unmarshal(testeapoio.Fixture(a.t, fixtureLista), &lista); err != nil {
		a.t.Fatal(err)
	}
	for _, m := range lista {
		if id, _ := m["id"].(float64); fmt.Sprintf("%.0f", id) == codigo {
			corpo, _ := json.Marshal(m)
			a.ibge.Responder("/municipios/"+codigo, testeapoio.Resposta{Corpo: corpo})
			return
		}
	}
	a.t.Fatalf("município %s não está em %s", codigo, fixtureLista)
}

package api

import (
	"net/url"
	"slices"
	"strings"
	"testing"
)

// Mesmos casos do test_api_busca.py do E1 e do ApiBuscaTest.java do E4 (US4), mais a lição da T046.

func buscar(a *ambiente, uf, termo string, extra ...string) map[string]any {
	a.t.Helper()
	alvo := "/v1/ufs/" + uf + "/municipios?nome=" + url.QueryEscape(termo)
	for _, e := range extra {
		alvo += "&" + e
	}
	w := a.get(alvo)
	if w.Code != 200 {
		a.t.Fatalf("%s: status %d %s", alvo, w.Code, w.Body)
	}
	return corpoJSON(a.t, w.Body.Bytes())
}

func TestBuscaSemAcentoESemCaixa(t *testing.T) {
	a := novoAmbiente(t)
	a.rj()
	for _, termo := range []string{"niteroi", "NITERÓI", "  Niterói  "} {
		corpo := buscar(a, "RJ", termo)
		dados := corpo["dados"].([]any)
		if len(dados) != 1 || dados[0].(map[string]any)["codigo"] != "3303302" || dados[0].(map[string]any)["nome"] != "Niterói" {
			t.Errorf("%q: %v", termo, dados)
		}
	}
}

func TestBuscaComVariosResultadosEmOrdemEPaginados(t *testing.T) {
	a := novoAmbiente(t)
	a.sp()
	tudo := buscar(a, "SP", "são", "itens=500")
	nomes := nomesDe(t, tudo["dados"])
	total := tudo["paginacao"].(map[string]any)["total"].(float64)
	if int(total) != len(nomes) || len(nomes) <= 10 || !slices.Contains(nomes, "São Paulo") || !slices.Contains(nomes, "São José dos Campos") {
		t.Fatalf("total %v, %d nomes", total, len(nomes))
	}
	pagina := buscar(a, "SP", "SAO", "itens=10", "pagina=2")
	if !slices.Equal(nomesDe(t, pagina["dados"]), nomes[10:20]) {
		t.Errorf("a página 2 não é a continuação da lista ordenada")
	}
}

func TestBuscaSemResultado(t *testing.T) {
	a := novoAmbiente(t)
	a.rj()
	corpo := buscar(a, "RJ", "xyzw")
	pag := corpo["paginacao"].(map[string]any)
	if len(corpo["dados"].([]any)) != 0 || pag["total"] != 0.0 || pag["paginas"] != 0.0 || pag["pagina"] != 1.0 || pag["itens"] != 100.0 {
		t.Errorf("sem resultado: %v", corpo)
	}
	if !strings.Contains(a.get("/v1/ufs/RJ/municipios?nome=xyzw").Body.String(), `"dados":[]`) {
		t.Error("lista vazia sai como [], e não como null")
	}
}

func TestBuscaInvalidaE400SemConsultar(t *testing.T) {
	a := novoAmbiente(t)
	casos := map[string]string{
		"a":                     "pelo menos 2",
		"  a  ":                 "pelo menos 2",
		"":                      "pelo menos 2",
		strings.Repeat("x", 61): "no máximo 60",
	}
	for termo, trecho := range casos {
		w := a.get("/v1/ufs/RJ/municipios?nome=" + url.QueryEscape(termo))
		p := conferirProblema(t, w.Code, w.Header(), w.Body.Bytes(), 400, "entrada-invalida")
		if !strings.Contains(p["detail"].(string), trecho) {
			t.Errorf("%q: detail %v", termo, p["detail"])
		}
	}
	if a.ibge.Total() != 0 {
		t.Errorf("busca inválida não consulta o IBGE: %d pedidos", a.ibge.Total())
	}
}

func TestDuasBuscasNaMesmaUFFazemUmaConsulta(t *testing.T) {
	a := novoAmbiente(t)
	a.rj()
	buscar(a, "RJ", "niteroi")
	buscar(a, "rj", "são")
	a.get("/v1/ufs/33/municipios")
	if a.ibge.Pedidos("/estados/33/municipios") != 1 {
		t.Errorf("%d consultas, esperado 1", a.ibge.Pedidos("/estados/33/municipios"))
	}
}

// T046 do E4: nome com codificação inválida, enviado cru, é 400 entrada-invalida, nunca 500.
func TestNomeMalCodificadoE400(t *testing.T) {
	a := novoAmbiente(t)
	a.rj()
	for _, consulta := range []string{"nome=%ZZ", "nome=s%E3o", "nome=%"} {
		r := a.cru("/v1/ufs/RJ/municipios?"+consulta, "X-Correlation-Id: nome-1")
		conferirProblema(t, r.StatusCode, r.Header, r.Corpo, 400, "entrada-invalida")
	}
	if a.ibge.Total() != 0 {
		t.Errorf("nome mal codificado não consulta o IBGE: %d pedidos", a.ibge.Total())
	}
}

package api

import (
	"strings"
	"testing"
)

// Mesmos casos do test_api_ufs.py do E1 e do ApiUfsTest.java do E4 (US1), mais as lições do E4.

func TestListaAs27UFsOrdenadas(t *testing.T) {
	a := novoAmbiente(t)
	a.estados()
	w := a.get("/v1/ufs")
	if w.Code != 200 || w.Header().Get("Content-Type") != "application/json" {
		t.Fatalf("status %d, Content-Type %q", w.Code, w.Header().Get("Content-Type"))
	}
	corpo := corpoJSON(t, w.Body.Bytes())
	if _, tem := corpo["paginacao"]; tem {
		t.Error("/v1/ufs não é paginada")
	}
	nomes := nomesDe(t, corpo["dados"])
	if len(nomes) != 27 || nomes[0] != "Acre" || nomes[26] != "Tocantins" {
		t.Errorf("%d UFs, primeira %q", len(nomes), nomes[0])
	}
	rj := corpo["dados"].([]any)[18].(map[string]any)
	if rj["sigla"] != "RJ" || rj["codigo"] != "33" || rj["regiao"].(map[string]any)["sigla"] != "SE" {
		t.Errorf("RJ = %v", rj)
	}
	conferirMeta(t, corpo, a.ibge.URL()+"/estados", false)
}

func TestUFPorSiglaOuCodigo(t *testing.T) {
	a := novoAmbiente(t)
	a.estados()
	for _, alvo := range []string{"/v1/ufs/rj", "/v1/ufs/33", "/v1/ufs/%20RJ%20"} {
		w := a.get(alvo)
		if w.Code != 200 {
			t.Fatalf("%s: status %d %s", alvo, w.Code, w.Body)
		}
		corpo := corpoJSON(t, w.Body.Bytes())
		dados := corpo["dados"].(map[string]any)
		if dados["nome"] != "Rio de Janeiro" || dados["codigo"] != "33" {
			t.Errorf("%s: %v", alvo, dados)
		}
		if _, tem := corpo["paginacao"]; tem {
			t.Errorf("%s: um recurso único não leva paginacao", alvo)
		}
	}
}

func TestUFInexistenteOuMalFormadaSemConsultarOIBGE(t *testing.T) {
	a := novoAmbiente(t)
	casos := []struct {
		alvo   string
		status int
		tipo   string
	}{
		{"/v1/ufs/XX", 404, "nao-encontrado"},
		{"/v1/ufs/99", 404, "nao-encontrado"},
		{"/v1/ufs/R1", 400, "entrada-invalida"},
		{"/v1/ufs/XX/municipios", 404, "nao-encontrado"},
		{"/v1/ufs/R1/municipios", 400, "entrada-invalida"},
	}
	for _, c := range casos {
		w := a.get(c.alvo)
		conferirProblema(t, w.Code, w.Header(), w.Body.Bytes(), c.status, c.tipo)
	}
	if a.ibge.Total() != 0 {
		t.Errorf("o IBGE foi consultado %d vezes", a.ibge.Total())
	}
}

func TestMunicipiosDoRJ(t *testing.T) {
	a := novoAmbiente(t)
	a.rj()
	w := a.get("/v1/ufs/RJ/municipios")
	if w.Code != 200 {
		t.Fatalf("status %d %s", w.Code, w.Body)
	}
	corpo := corpoJSON(t, w.Body.Bytes())
	nomes := nomesDe(t, corpo["dados"])
	if len(nomes) != 92 || nomes[0] != "Angra dos Reis" {
		t.Errorf("%d municípios, primeiro %q", len(nomes), nomes[0])
	}
	pag := corpo["paginacao"].(map[string]any)
	if pag["pagina"] != 1.0 || pag["itens"] != 100.0 || pag["total"] != 92.0 || pag["paginas"] != 1.0 {
		t.Errorf("paginacao = %v", pag)
	}
	conferirMeta(t, corpo, a.ibge.URL()+"/estados/33/municipios", false)
	if !strings.HasPrefix(w.Body.String(), `{"dados":`) || !strings.Contains(w.Body.String(), `],"paginacao":{`) {
		t.Errorf("campos fora da ordem dados, paginacao, meta: %.80s", w.Body.String())
	}
}

func TestPaginacao(t *testing.T) {
	a := novoAmbiente(t)
	a.rj()
	corpo := corpoJSON(t, a.get("/v1/ufs/RJ/municipios?itens=10&pagina=10").Body.Bytes())
	if n := len(corpo["dados"].([]any)); n != 2 {
		t.Errorf("página 10 de 10 itens: %d itens", n)
	}
	corpo = corpoJSON(t, a.get("/v1/ufs/RJ/municipios?itens=10&pagina=11").Body.Bytes())
	if dados := corpo["dados"].([]any); len(dados) != 0 || corpo["paginacao"].(map[string]any)["total"] != 92.0 {
		t.Errorf("além do fim: %v", corpo["paginacao"])
	}
}

func TestPaginacaoInvalidaE400ComOLimite(t *testing.T) {
	a := novoAmbiente(t)
	a.rj()
	casos := map[string]string{
		"itens=0":   "itens precisa estar entre 1 e 500, recebi 0",
		"itens=501": "itens precisa estar entre 1 e 500, recebi 501",
		"pagina=0":  "pagina precisa ser maior ou igual a 1, recebi 0",
		"itens=1.5": "itens precisa ser um número inteiro, recebi '1.5'",
		"pagina=x":  "pagina precisa ser um número inteiro, recebi 'x'",
	}
	for consulta, detalhe := range casos {
		w := a.get("/v1/ufs/RJ/municipios?" + consulta)
		p := conferirProblema(t, w.Code, w.Header(), w.Body.Bytes(), 400, "entrada-invalida")
		if p["detail"] != detalhe {
			t.Errorf("%s: detail %v", consulta, p["detail"])
		}
	}
	if a.ibge.Total() != 0 {
		t.Errorf("entrada inválida não consulta o IBGE: %d pedidos", a.ibge.Total())
	}
}

// T045 do E4: o contrato não limita pagina, e parâmetro repetido vale o último, como no E1.
func TestPaginaEnormeEParametroRepetido(t *testing.T) {
	a := novoAmbiente(t)
	a.rj()
	corpo := corpoJSON(t, a.get("/v1/ufs/RJ/municipios?pagina=99999999999").Body.Bytes())
	pag := corpo["paginacao"].(map[string]any)
	if len(corpo["dados"].([]any)) != 0 || pag["pagina"] != 99999999999.0 || pag["total"] != 92.0 {
		t.Errorf("pagina=99999999999: %v", pag)
	}
	w := a.get("/v1/ufs/RJ/municipios?pagina=" + strings.Repeat("9", 30))
	if w.Code != 200 || len(corpoJSON(t, w.Body.Bytes())["dados"].([]any)) != 0 {
		t.Errorf("pagina com 30 dígitos: %d %s", w.Code, w.Body)
	}
	corpo = corpoJSON(t, a.get("/v1/ufs/RJ/municipios?itens=10&itens=20").Body.Bytes())
	if corpo["paginacao"].(map[string]any)["itens"] != 20.0 || len(corpo["dados"].([]any)) != 20 {
		t.Errorf("itens repetido: %v", corpo["paginacao"])
	}
}

// T046 do E4: query mal codificada é erro do pedido (400), nunca 500.
func TestQueryMalCodificadaE400(t *testing.T) {
	a := novoAmbiente(t)
	a.rj()
	for _, consulta := range []string{"itens=%ZZ", "pagina=%E3", "itens=%"} {
		r := a.cru("/v1/ufs/RJ/municipios?"+consulta, "X-Correlation-Id: query-1")
		p := conferirProblema(t, r.StatusCode, r.Header, r.Corpo, 400, "entrada-invalida")
		if !strings.Contains(p["detail"].(string), "codificação inválida") {
			t.Errorf("%s: detail %v", consulta, p["detail"])
		}
	}
	if a.ibge.Total() != 0 {
		t.Errorf("query mal codificada não consulta o IBGE: %d pedidos", a.ibge.Total())
	}
}

// T048 do E4: o Accept não muda o formato.
func TestAcceptNaoMudaOFormatoDaLista(t *testing.T) {
	a := novoAmbiente(t)
	a.estados()
	for _, aceita := range []string{"application/xml", "text/html", "application/problem+json"} {
		w := a.get("/v1/ufs", "Accept", aceita)
		if w.Code != 200 || w.Header().Get("Content-Type") != "application/json" {
			t.Errorf("Accept %s: %d %q", aceita, w.Code, w.Header().Get("Content-Type"))
		}
	}
}

// T050 do E4: com ";" no caminho, a rota não casa e o IBGE não é consultado.
func TestParametroDeCaminhoNaoCasaComARota(t *testing.T) {
	a := novoAmbiente(t)
	a.estados()
	a.rj()
	for _, alvo := range []string{"/v1/ufs;jsessionid=x", "/v1/ufs/RJ;x=1/municipios", "/v1/ufs/RJ/municipios;x"} {
		r := a.cru(alvo, "X-Correlation-Id: pv-1")
		conferirProblema(t, r.StatusCode, r.Header, r.Corpo, 404, "nao-encontrado")
	}
	if a.ibge.Total() != 0 {
		t.Errorf("o IBGE foi consultado %d vezes", a.ibge.Total())
	}
}

func TestJSONSemEscapeHTML(t *testing.T) {
	a := novoAmbiente(t)
	a.ibge.Responder("/estados/33/municipios", testeapoioResposta(`[{"id": 3300100, "nome": "A <&> B"}]`))
	w := a.get("/v1/ufs/RJ/municipios")
	if !strings.Contains(w.Body.String(), `"nome":"A <&> B"`) {
		t.Errorf("o JSON escapou <, & ou >: %s", w.Body.String())
	}
}

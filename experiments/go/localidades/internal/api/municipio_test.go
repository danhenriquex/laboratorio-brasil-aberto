package api

import (
	"strings"
	"testing"
)

// Mesmos casos do test_api_municipio.py do E1 e do ApiMunicipioTest.java do E4 (US2), mais a lição da T044.

func TestMunicipioRioDeJaneiro(t *testing.T) {
	a := novoAmbiente(t)
	a.municipio("municipios-uf-33.json", "3304557")
	w := a.get("/v1/municipios/3304557")
	if w.Code != 200 {
		t.Fatalf("status %d %s", w.Code, w.Body)
	}
	corpo := corpoJSON(t, w.Body.Bytes())
	d := corpo["dados"].(map[string]any)
	uf := d["uf"].(map[string]any)
	if d["codigo"] != "3304557" || d["nome"] != "Rio de Janeiro" || uf["sigla"] != "RJ" || uf["codigo"] != "33" ||
		d["regiao_imediata"].(map[string]any)["codigo"] != "330001" || d["regiao_intermediaria"].(map[string]any)["codigo"] != "3301" {
		t.Errorf("dados = %v", d)
	}
	if _, tem := corpo["paginacao"]; tem {
		t.Error("um município não leva paginacao")
	}
	conferirMeta(t, corpo, a.ibge.URL()+"/municipios/3304557", false)
}

func TestMunicipioInexistenteE404ComODetalheDoE1(t *testing.T) {
	a := novoAmbiente(t)
	a.ibge.Responder("/municipios/9999999", testeapoioResposta("[]"))
	w := a.get("/v1/municipios/9999999")
	p := conferirProblema(t, w.Code, w.Header(), w.Body.Bytes(), 404, "nao-encontrado")
	if p["detail"] != "não existe município com o código 9999999" {
		t.Errorf("detail %v", p["detail"])
	}
}

func TestCodigoMalFormadoE400SemConsultar(t *testing.T) {
	a := novoAmbiente(t)
	for _, codigo := range []string{"12ab", "123456", "12345678", "330455%EF%BC%97"} {
		w := a.get("/v1/municipios/" + codigo)
		conferirProblema(t, w.Code, w.Header(), w.Body.Bytes(), 400, "entrada-invalida")
	}
	if a.ibge.Total() != 0 {
		t.Errorf("o IBGE foi consultado %d vezes", a.ibge.Total())
	}
}

func TestNomeComApostrofoSemEscape(t *testing.T) {
	a := novoAmbiente(t)
	a.municipio("municipios-uf-35.json", "3545803")
	w := a.get("/v1/municipios/3545803")
	if !strings.Contains(w.Body.String(), `"nome":"Santa Bárbara d'Oeste"`) {
		t.Errorf("nome com apóstrofo: %s", w.Body.String())
	}
}

func TestMunicipioSemMicrorregiaoEBrasilia(t *testing.T) {
	a := novoAmbiente(t)
	a.ibge.ResponderFixture(t, "/municipios/5101837", "municipio-5101837.json")
	a.municipio("municipios-uf-53.json", "5300108")
	for codigo, sigla := range map[string]string{"5101837": "MT", "5300108": "DF"} {
		w := a.get("/v1/municipios/" + codigo)
		if w.Code != 200 || corpoJSON(t, w.Body.Bytes())["dados"].(map[string]any)["uf"].(map[string]any)["sigla"] != sigla {
			t.Errorf("%s: %d %s", codigo, w.Code, w.Body)
		}
	}
}

// T044 do E4: caminho mal codificado sai em problem+json com correlação, nunca em HTML nem texto puro.
// Em Go, o próprio net/http recusaria o %ZZ antes do handler; o Ouvinte saneia a linha do pedido.
func TestCaminhoMalCodificadoEProblemaComCorrelacao(t *testing.T) {
	a := novoAmbiente(t)
	casos := []struct {
		alvo   string
		status int
		tipo   string
	}{
		{"/v1/municipios/%ZZ", 400, "entrada-invalida"},
		{"/v1/municipios/%", 400, "entrada-invalida"},
		{"/v1/municipios/%E3", 400, "entrada-invalida"},
		{"/v1/ufs/R%ZZ/municipios", 400, "entrada-invalida"},
		{"/v1/municipios/%2F", 404, "nao-encontrado"},
	}
	for _, c := range casos {
		r := a.cru(c.alvo, "X-Correlation-Id: mal-codificado")
		p := conferirProblema(t, r.StatusCode, r.Header, r.Corpo, c.status, c.tipo)
		if p["correlacao_id"] != "mal-codificado" {
			t.Errorf("%s: correlação %v", c.alvo, p["correlacao_id"])
		}
	}
	if a.ibge.Total() != 0 {
		t.Errorf("o IBGE foi consultado %d vezes", a.ibge.Total())
	}
}

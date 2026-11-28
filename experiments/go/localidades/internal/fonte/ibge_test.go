package fonte

import (
	"context"
	"encoding/json"
	"errors"
	"strings"
	"testing"
	"time"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/erros"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/testeapoio"
)

func tipoDe(err error) string {
	var e *erros.ErroDominio
	if errors.As(err, &e) {
		return e.Tipo
	}
	return ""
}

func novoCliente(t *testing.T, ibge *testeapoio.IBGE, prazo time.Duration) (*Cliente, *[]string) {
	t.Helper()
	medidos := &[]string{}
	return NovoCliente(ibge.URL(), prazo, func(_ context.Context, recurso string, _ float64) {
		*medidos = append(*medidos, recurso)
	}), medidos
}

func TestClassificacaoDasFalhas(t *testing.T) {
	ibge := testeapoio.NovoIBGE(t)
	casos := []struct {
		nome     string
		resposta testeapoio.Resposta
		tipo     string
	}{
		{"503", testeapoio.Resposta{Status: 503, Corpo: []byte("fora")}, "fonte-indisponivel"},
		{"429", testeapoio.Resposta{Status: 429, Corpo: []byte("calma")}, "fonte-indisponivel"},
		{"404", testeapoio.Resposta{Status: 404, Corpo: []byte("[]")}, "resposta-inesperada-da-fonte"},
		{"301 não é seguido", testeapoio.Resposta{Status: 301, Corpo: nil}, "resposta-inesperada-da-fonte"},
		{"HTML com 200", testeapoio.Resposta{Corpo: testeapoio.Fixture(t, "erro.html"), Tipo: "text/html"}, "resposta-inesperada-da-fonte"},
		{"JSON sem campo obrigatório", testeapoio.Resposta{Corpo: testeapoio.Fixture(t, "estados-sem-regiao.json")}, "resposta-inesperada-da-fonte"},
		{"lista vazia de UFs", testeapoio.Resposta{Corpo: []byte("[]")}, "resposta-inesperada-da-fonte"},
	}
	for _, c := range casos {
		ibge.Responder("/estados", c.resposta)
		cliente, _ := novoCliente(t, ibge, time.Second)
		_, _, err := cliente.Estados(context.Background())
		if tipoDe(err) != c.tipo {
			t.Errorf("%s: erro %v, esperado %s", c.nome, err, c.tipo)
		}
		if err != nil && strings.Contains(err.Error(), "Página de erro") {
			t.Errorf("%s: a mensagem não pode carregar o corpo do IBGE: %v", c.nome, err)
		}
	}
}

func TestConexaoRecusadaEFonteIndisponivel(t *testing.T) {
	ibge := testeapoio.NovoIBGE(t)
	url := ibge.URL()
	ibge.Servidor.Close()
	cliente := NovoCliente(url, time.Second, nil)
	_, _, err := cliente.Estados(context.Background())
	if tipoDe(err) != "fonte-indisponivel" || err.Error() != "não foi possível conectar ao IBGE" {
		t.Errorf("erro %v, esperado fonte-indisponivel", err)
	}
}

func TestPrazoTotalEFonteLenta(t *testing.T) {
	ibge := testeapoio.NovoIBGE(t)
	ibge.Responder("/estados", testeapoio.Resposta{Corpo: testeapoio.Fixture(t, "estados.json"), Atraso: 300 * time.Millisecond})
	cliente, medidos := novoCliente(t, ibge, 50*time.Millisecond)
	inicio := time.Now()
	_, _, err := cliente.Estados(context.Background())
	decorrido := time.Since(inicio)
	if tipoDe(err) != "fonte-lenta" || err.Error() != "o IBGE não respondeu em 0.05 s" {
		t.Errorf("erro %v, esperado fonte-lenta com o prazo no detalhe", err)
	}
	if decorrido >= 300*time.Millisecond {
		t.Errorf("o prazo de 50 ms não foi respeitado: %v", decorrido)
	}
	if len(*medidos) != 1 || (*medidos)[0] != "estados" {
		t.Errorf("a duração precisa ser medida também na falha: %v", *medidos)
	}
}

func TestNormalizacaoDasUFs(t *testing.T) {
	ibge := testeapoio.NovoIBGE(t)
	ibge.ResponderFixture(t, "/estados", "estados.json")
	cliente, medidos := novoCliente(t, ibge, time.Second)
	ufs, url, err := cliente.Estados(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if len(ufs) != 27 || url != ibge.URL()+"/estados" {
		t.Fatalf("%d UFs, url %q", len(ufs), url)
	}
	ro := ufs[0]
	if ro.Codigo != "11" || ro.Sigla != "RO" || ro.Nome != "Rondônia" || ro.Regiao.Codigo != "1" || ro.Regiao.Sigla != "N" {
		t.Errorf("primeira UF = %+v", ro)
	}
	if ibge.Pedidos("/estados") != 1 {
		t.Errorf("esperava exatamente 1 pedido, foram %d", ibge.Pedidos("/estados"))
	}
	if ibge.UserAgent() != UserAgent {
		t.Errorf("User-Agent = %q", ibge.UserAgent())
	}
	if len(*medidos) != 1 {
		t.Errorf("medidas: %v", *medidos)
	}
}

func TestNormalizacaoDosMunicipiosDaUF(t *testing.T) {
	ibge := testeapoio.NovoIBGE(t)
	ibge.ResponderFixture(t, "/estados/33/municipios", "municipios-uf-33.json")
	cliente, _ := novoCliente(t, ibge, time.Second)
	municipios, _, err := cliente.MunicipiosDaUF(context.Background(), "33")
	if err != nil {
		t.Fatal(err)
	}
	if len(municipios) != 92 || municipios[0].Codigo != "3300100" || municipios[0].Nome != "Angra dos Reis" {
		t.Errorf("%d municípios, primeiro %+v", len(municipios), municipios[0])
	}
}

func TestMunicipioObjetoOuListaDeUmESemMicrorregiao(t *testing.T) {
	ibge := testeapoio.NovoIBGE(t)
	objeto := testeapoio.Fixture(t, "municipio-5101837.json")
	lista := append(append([]byte("["), objeto...), ']')
	for nome, corpo := range map[string][]byte{"objeto": objeto, "lista de 1": lista} {
		ibge.Responder("/municipios/5101837", testeapoio.Resposta{Corpo: corpo})
		cliente, _ := novoCliente(t, ibge, time.Second)
		m, _, err := cliente.Municipio(context.Background(), "5101837")
		if err != nil {
			t.Fatalf("%s: %v", nome, err)
		}
		if m.Nome != "Boa Esperança do Norte" || m.UF.Sigla != "MT" || m.RegiaoImediata.Codigo != "510008" || m.RegiaoIntermediaria.Codigo != "5103" {
			t.Errorf("%s: %+v", nome, m)
		}
	}
}

func TestMunicipioInexistenteENaoEncontrado(t *testing.T) {
	ibge := testeapoio.NovoIBGE(t)
	ibge.Responder("/municipios/9999999", testeapoio.Resposta{Corpo: []byte("[]")})
	cliente, _ := novoCliente(t, ibge, time.Second)
	_, _, err := cliente.Municipio(context.Background(), "9999999")
	if tipoDe(err) != "nao-encontrado" || err.Error() != "não existe município com o código 9999999" {
		t.Errorf("erro %v", err)
	}
}

func TestMunicipioSemRegiaoImediataEInesperado(t *testing.T) {
	ibge := testeapoio.NovoIBGE(t)
	ibge.ResponderFixture(t, "/municipios/1100015", "municipio-sem-regiao-imediata.json")
	cliente, _ := novoCliente(t, ibge, time.Second)
	_, _, err := cliente.Municipio(context.Background(), "1100015")
	if tipoDe(err) != "resposta-inesperada-da-fonte" {
		t.Errorf("erro %v", err)
	}
}

// Formato exato de códigos e siglas (T048 e T049 do E1): completar com zeros ou aceitar sigla fora do
// padrão inventaria um dado que o IBGE não publicou.
func TestFormatoExatoDeCodigosESiglas(t *testing.T) {
	ibge := testeapoio.NovoIBGE(t)
	cliente, _ := novoCliente(t, ibge, time.Second)

	var estados []map[string]any
	if err := json.Unmarshal(testeapoio.Fixture(t, "estados.json"), &estados); err != nil {
		t.Fatal(err)
	}
	alterarEstados := func(mudar func(uf map[string]any)) []byte {
		copia := make([]map[string]any, len(estados))
		for i, uf := range estados {
			nova := map[string]any{}
			for k, v := range uf {
				nova[k] = v
			}
			regiao := map[string]any{}
			for k, v := range uf["regiao"].(map[string]any) {
				regiao[k] = v
			}
			nova["regiao"] = regiao
			copia[i] = nova
		}
		mudar(copia[0])
		corpo, _ := json.Marshal(copia)
		return corpo
	}
	casosUF := map[string]func(map[string]any){
		"UF com id 1":            func(uf map[string]any) { uf["id"] = 1 },
		"sigla de UF minúscula":  func(uf map[string]any) { uf["sigla"] = "ro" },
		"sigla de UF com espaço": func(uf map[string]any) { uf["sigla"] = "R O" },
		"sigla de região longa":  func(uf map[string]any) { uf["regiao"].(map[string]any)["sigla"] = "Norte" },
		"id booleano":            func(uf map[string]any) { uf["id"] = true },
	}
	for nome, mudar := range casosUF {
		ibge.Responder("/estados", testeapoio.Resposta{Corpo: alterarEstados(mudar)})
		if _, _, err := cliente.Estados(context.Background()); tipoDe(err) != "resposta-inesperada-da-fonte" {
			t.Errorf("%s: erro %v", nome, err)
		}
	}

	ibge.Responder("/estados/33/municipios", testeapoio.Resposta{Corpo: []byte(`[{"id": 33001, "nome": "Curto"}]`)})
	if _, _, err := cliente.MunicipiosDaUF(context.Background(), "33"); tipoDe(err) != "resposta-inesperada-da-fonte" {
		t.Errorf("id de 5 dígitos na lista: erro %v", err)
	}

	var municipio map[string]any
	if err := json.Unmarshal(testeapoio.Fixture(t, "municipio-5101837.json"), &municipio); err != nil {
		t.Fatal(err)
	}
	municipio["regiao-imediata"].(map[string]any)["id"] = 51000
	corpo, _ := json.Marshal(municipio)
	ibge.Responder("/municipios/5101837", testeapoio.Resposta{Corpo: corpo})
	if _, _, err := cliente.Municipio(context.Background(), "5101837"); tipoDe(err) != "resposta-inesperada-da-fonte" {
		t.Errorf("região imediata com 5 dígitos: erro %v", err)
	}
}

func TestOutroMunicipioNaRespostaEInesperado(t *testing.T) {
	ibge := testeapoio.NovoIBGE(t)
	ibge.ResponderFixture(t, "/municipios/5101838", "municipio-5101837.json")
	cliente, _ := novoCliente(t, ibge, time.Second)
	if _, _, err := cliente.Municipio(context.Background(), "5101838"); tipoDe(err) != "resposta-inesperada-da-fonte" {
		t.Errorf("erro %v", err)
	}
}

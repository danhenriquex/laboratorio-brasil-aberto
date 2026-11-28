package transporte

import (
	"bufio"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestSanearLinhaDoPedido(t *testing.T) {
	casos := map[string]string{
		"GET /v1/municipios/%ZZ HTTP/1.1":             "GET /v1/municipios/%25ZZ HTTP/1.1",
		"GET /v1/ufs/R%ZZ/municipios HTTP/1.1":        "GET /v1/ufs/R%25ZZ/municipios HTTP/1.1",
		"GET /v1/municipios/% HTTP/1.1":               "GET /v1/municipios/%25 HTTP/1.1",
		"GET /v1/municipios/%4 HTTP/1.1":              "GET /v1/municipios/%254 HTTP/1.1",
		"GET /v1/ufs/%20RJ%20 HTTP/1.1":               "GET /v1/ufs/%20RJ%20 HTTP/1.1",
		"GET /v1/ufs/RJ/municipios?nome=%ZZ HTTP/1.1": "GET /v1/ufs/RJ/municipios?nome=%ZZ HTTP/1.1", // a query fica crua
		"GET /v1/ufs/%2F HTTP/1.1":                    "GET /v1/ufs/%2F HTTP/1.1",
		"lixo":                                        "lixo",
	}
	for entrada, esperado := range casos {
		if obtido := string(sanearLinha([]byte(entrada))); obtido != esperado {
			t.Errorf("sanearLinha(%q) = %q, esperado %q", entrada, obtido, esperado)
		}
	}
}

// eco devolve o caminho que chegou ao handler, para ver o que o net/http recebeu depois do saneamento.
func servidorEco(t *testing.T) *httptest.Server {
	t.Helper()
	srv := httptest.NewUnstartedServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		_, _ = io.Copy(io.Discard, r.Body)
		fmt.Fprintf(w, "%s %s?%s", r.Method, r.URL.Path, r.URL.RawQuery)
	}))
	srv.Listener = Ouvinte(srv.Listener)
	srv.Start()
	t.Cleanup(srv.Close)
	return srv
}

func TestPedidoMalCodificadoChegaAoHandler(t *testing.T) {
	srv := servidorEco(t)
	resp, err := http.Get(srv.URL + "/v1/ufs") // pedido normal continua normal
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()

	conexao, err := net.Dial("tcp", srv.Listener.Addr().String())
	if err != nil {
		t.Fatal(err)
	}
	defer conexao.Close()
	leitor := bufio.NewReader(conexao)

	// Três pedidos na mesma conexão (keep-alive): o saneamento vale para cada linha de pedido, e um corpo
	// no meio não é tratado como linha de pedido.
	pedidos := "GET /v1/municipios/%ZZ HTTP/1.1\r\nHost: x\r\n\r\n" +
		"POST /v1/x HTTP/1.1\r\nHost: x\r\nContent-Length: 7\r\n\r\na=%ZZ&b" +
		"GET /v1/ufs/R%ZZ/municipios?nome=%E3 HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n"
	if _, err := io.WriteString(conexao, pedidos); err != nil {
		t.Fatal(err)
	}
	esperados := []string{"GET /v1/municipios/%ZZ?", "POST /v1/x?", "GET /v1/ufs/R%ZZ/municipios?nome=%E3"}
	for _, esperado := range esperados {
		resp, err := http.ReadResponse(leitor, nil)
		if err != nil {
			t.Fatalf("esperava %q: %v", esperado, err)
		}
		corpo, _ := io.ReadAll(resp.Body)
		resp.Body.Close()
		if resp.StatusCode != 200 || string(corpo) != esperado {
			t.Errorf("status %d, corpo %q; esperado %q", resp.StatusCode, corpo, esperado)
		}
	}
}

func TestSemOuvinteONetHTTPRecusaSozinho(t *testing.T) {
	// Documenta o comportamento que o Ouvinte contorna: o net/http responde 400 em texto puro, sem passar
	// pelo handler e, portanto, sem correlação nem problem+json.
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t.Error("o handler não deveria ser chamado")
	}))
	defer srv.Close()
	conexao, err := net.Dial("tcp", srv.Listener.Addr().String())
	if err != nil {
		t.Fatal(err)
	}
	defer conexao.Close()
	_, _ = io.WriteString(conexao, "GET /v1/municipios/%ZZ HTTP/1.1\r\nHost: x\r\n\r\n")
	resp, err := http.ReadResponse(bufio.NewReader(conexao), nil)
	if err != nil {
		t.Fatal(err)
	}
	if resp.StatusCode != 400 || !strings.HasPrefix(resp.Header.Get("Content-Type"), "text/plain") {
		t.Errorf("o net/http mudou de comportamento: %d %q", resp.StatusCode, resp.Header.Get("Content-Type"))
	}
}

package testeapoio

import (
	"bufio"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

// RespostaCrua é a resposta de um pedido escrito à mão, com o corpo inteiro e os bytes brutos.
type RespostaCrua struct {
	*http.Response
	Corpo []byte
	Bruto string
}

// PedidoCru escreve o pedido HTTP direto no socket de um httptest.Server. Assim o caminho e a query chegam
// exatamente como escritos: um cliente HTTP comum limparia "//", "." e "..", e recusaria um "%" inválido.
func PedidoCru(t testing.TB, servidor *httptest.Server, metodo, alvo string, cabecalhos ...string) RespostaCrua {
	t.Helper()
	conexao, err := net.Dial("tcp", strings.TrimPrefix(servidor.URL, "http://"))
	if err != nil {
		t.Fatal(err)
	}
	defer conexao.Close()
	pedido := metodo + " " + alvo + " HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n"
	for _, c := range cabecalhos {
		pedido += c + "\r\n"
	}
	if _, err := io.WriteString(conexao, pedido+"\r\n"); err != nil {
		t.Fatal(err)
	}
	bruto, err := io.ReadAll(conexao)
	if err != nil {
		t.Fatal(err)
	}
	resposta, err := http.ReadResponse(bufio.NewReader(strings.NewReader(string(bruto))), nil)
	if err != nil {
		t.Fatalf("resposta ilegível para %s %s: %v\n%s", metodo, alvo, err, bruto)
	}
	corpo, _ := io.ReadAll(resposta.Body)
	resposta.Body.Close()
	return RespostaCrua{Response: resposta, Corpo: corpo, Bruto: string(bruto)}
}

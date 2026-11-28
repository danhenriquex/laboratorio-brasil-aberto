// Package transporte saneia a linha de cada pedido antes do net/http (lição da T044 do E4).
//
// O net/http recusa sozinho um caminho com escape inválido (como /v1/municipios/%ZZ): responde 400 em
// texto puro, antes de qualquer handler, e portanto sem problem+json nem X-Correlation-Id. A biblioteca
// padrão não tem gancho para isso. O Ouvinte troca, só no caminho da linha do pedido, cada "%" que não
// inicia um escape válido por "%25". Assim o pedido chega ao handler com o texto literal ("%ZZ"), que a
// validação do domínio recusa como entrada inválida, como no E1. A query fica crua: a leitura dela já
// recusa a codificação inválida (research R4).
package transporte

import (
	"bufio"
	"bytes"
	"errors"
	"io"
	"net"
	"strconv"
)

// limiteCabecalho acompanha o MaxHeaderBytes padrão do net/http (1 MB) com folga. Acima disso, os bytes
// passam sem saneamento, e o próprio net/http recusa o pedido.
const limiteCabecalho = 1<<20 + 4096

// Ouvinte embrulha um net.Listener para sanear a linha de cada pedido das conexões aceitas.
func Ouvinte(l net.Listener) net.Listener { return ouvinte{l} }

type ouvinte struct{ net.Listener }

func (o ouvinte) Accept() (net.Conn, error) {
	c, err := o.Listener.Accept()
	if err != nil {
		return nil, err
	}
	return &conexao{Conn: c, leitor: bufio.NewReader(c)}, nil
}

// conexao lê cada bloco de cabeçalho inteiro, saneia a primeira linha e entrega os bytes ao net/http.
// Um corpo nunca é alterado: com Content-Length, os bytes do corpo passam sem mexer e o saneamento volta
// no pedido seguinte; com Transfer-Encoding (sem tamanho conhecido), o resto da conexão passa sem mexer.
// As rotas do serviço são todas GET, sem corpo.
type conexao struct {
	net.Conn
	leitor  *bufio.Reader
	pronto  []byte // bytes já saneados, à espera de quem lê
	bloco   []byte // bloco de cabeçalho ainda incompleto (sobrevive a um prazo de leitura esgotado)
	corpo   int64  // bytes de corpo que ainda passam sem mexer
	repasse bool   // o resto da conexão passa sem mexer
	fim     error
}

func (c *conexao) Read(p []byte) (int, error) {
	for len(c.pronto) == 0 {
		if c.fim != nil {
			return 0, c.fim
		}
		if c.corpo > 0 {
			n, err := c.leitor.Read(p[:min(int64(len(p)), c.corpo)])
			c.corpo -= int64(n)
			return n, err
		}
		if c.repasse {
			if len(c.bloco) > 0 {
				c.pronto, c.bloco = c.bloco, nil
				break
			}
			return c.leitor.Read(p)
		}
		linha, err := c.leitor.ReadSlice('\n')
		c.bloco = append(c.bloco, linha...)
		switch {
		case errors.Is(err, bufio.ErrBufferFull):
			if len(c.bloco) > limiteCabecalho {
				c.repasse = true
			}
			continue
		case err != nil:
			if errors.Is(err, io.EOF) && len(c.bloco) > 0 {
				c.pronto, c.bloco, c.fim = c.bloco, nil, err
				break
			}
			return 0, err // por exemplo, prazo de leitura: o bloco parcial fica guardado
		case len(bytes.TrimRight(linha, "\r\n")) == 0:
			c.terminarBloco()
		}
	}
	n := copy(p, c.pronto)
	c.pronto = c.pronto[n:]
	return n, nil
}

// terminarBloco é chamado na linha em branco que fecha um bloco de cabeçalho.
func (c *conexao) terminarBloco() {
	bloco := c.bloco
	c.bloco = nil
	fimDaLinha := bytes.IndexByte(bloco, '\n')
	if fimDaLinha == len(bloco)-1 {
		// Linha em branco solta antes do pedido (a RFC 9112 permite): passa como veio.
		c.pronto = bloco
		return
	}
	c.pronto = append(sanearLinha(bloco[:fimDaLinha+1]), bloco[fimDaLinha+1:]...)
	c.corpo, c.repasse = tamanhoDoCorpo(bloco[fimDaLinha+1:])
}

// sanearLinha troca, só no caminho de "MÉTODO ALVO VERSÃO", cada "%" que não inicia um escape válido.
func sanearLinha(linha []byte) []byte {
	i := bytes.IndexByte(linha, ' ')
	if i < 0 {
		return linha
	}
	j := bytes.IndexByte(linha[i+1:], ' ')
	if j < 0 {
		return linha
	}
	alvo := linha[i+1 : i+1+j]
	caminho, query := alvo, []byte(nil)
	if k := bytes.IndexByte(alvo, '?'); k >= 0 {
		caminho, query = alvo[:k], alvo[k:]
	}
	if !escapeInvalido(caminho) {
		return linha
	}
	var saida bytes.Buffer
	saida.Write(linha[:i+1])
	for k := 0; k < len(caminho); k++ {
		if caminho[k] == '%' && !(k+2 < len(caminho) && hexa(caminho[k+1]) && hexa(caminho[k+2])) {
			saida.WriteString("%25")
			continue
		}
		saida.WriteByte(caminho[k])
	}
	saida.Write(query)
	saida.Write(linha[i+1+j:])
	return saida.Bytes()
}

func escapeInvalido(caminho []byte) bool {
	for k := 0; k < len(caminho); k++ {
		if caminho[k] == '%' && !(k+2 < len(caminho) && hexa(caminho[k+1]) && hexa(caminho[k+2])) {
			return true
		}
	}
	return false
}

func hexa(b byte) bool {
	return '0' <= b && b <= '9' || 'a' <= b && b <= 'f' || 'A' <= b && b <= 'F'
}

// tamanhoDoCorpo lê o Content-Length dos cabeçalhos. Com Transfer-Encoding, ou com um Content-Length que
// não dá para ler, o tamanho é desconhecido, e o resto da conexão passa sem mexer.
func tamanhoDoCorpo(cabecalhos []byte) (tamanho int64, desconhecido bool) {
	for _, linha := range bytes.Split(cabecalhos, []byte("\n")) {
		nome, valor, ok := bytes.Cut(linha, []byte(":"))
		if !ok {
			continue
		}
		nome = bytes.TrimSpace(nome)
		valor = bytes.TrimSpace(valor)
		switch {
		case bytes.EqualFold(nome, []byte("Transfer-Encoding")):
			return 0, true
		case bytes.EqualFold(nome, []byte("Content-Length")):
			n, err := strconv.ParseInt(string(valor), 10, 64)
			if err != nil || n < 0 {
				return 0, true
			}
			tamanho = n
		}
	}
	return tamanho, false
}

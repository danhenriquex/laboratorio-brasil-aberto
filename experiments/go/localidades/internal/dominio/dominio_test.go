package dominio

import (
	"errors"
	"slices"
	"strings"
	"testing"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/erros"
)

// tipoDe devolve o tipo do ErroDominio, ou "" se o erro for nil ou de outro tipo.
func tipoDe(err error) string {
	var e *erros.ErroDominio
	if errors.As(err, &e) {
		return e.Tipo
	}
	return ""
}

func TestDobrar(t *testing.T) {
	casos := []struct{ entrada, esperado string }{
		{"Niterói", "niteroi"},
		{"SÃO", "sao"},
		{"São João d'Aliança", "sao joao d'alianca"},
		{"Açu", "acu"},
		{"", ""},
	}
	for _, c := range casos {
		if obtido := Dobrar(c.entrada); obtido != c.esperado {
			t.Errorf("Dobrar(%q) = %q, esperado %q", c.entrada, obtido, c.esperado)
		}
	}
}

func TestOrdenarPorNomeDobradoEDesempatePeloCodigo(t *testing.T) {
	itens := []MunicipioResumido{
		{Codigo: "3", Nome: "Ébano"},
		{Codigo: "2", Nome: "abacate"},
		{Codigo: "9", Nome: "Abacate"},
		{Codigo: "1", Nome: "Zé"},
	}
	ordenados := Ordenar(itens)
	var codigos []string
	for _, m := range ordenados {
		codigos = append(codigos, m.Codigo)
	}
	if esperado := []string{"2", "9", "3", "1"}; !slices.Equal(codigos, esperado) {
		t.Errorf("ordem = %v, esperado %v", codigos, esperado)
	}
	if itens[0].Codigo != "3" {
		t.Error("Ordenar não pode mexer na lista original")
	}
}

func TestFiltrarPorNome(t *testing.T) {
	itens := []MunicipioResumido{
		{Codigo: "1", Nome: "Niterói"},
		{Codigo: "2", Nome: "São Gonçalo"},
		{Codigo: "3", Nome: "Rio de Janeiro"},
	}
	casos := []struct {
		termo    string
		esperado []string
	}{
		{"niteroi", []string{"1"}},
		{"  NITERÓI ", []string{"1"}},
		{"sao", []string{"2"}},
		{"o", []string{"1", "2", "3"}},
		{"xyz", nil},
	}
	for _, c := range casos {
		var codigos []string
		for _, m := range FiltrarPorNome(itens, c.termo) {
			codigos = append(codigos, m.Codigo)
		}
		if !slices.Equal(codigos, c.esperado) {
			t.Errorf("FiltrarPorNome(%q) = %v, esperado %v", c.termo, codigos, c.esperado)
		}
	}
}

func TestPaginar(t *testing.T) {
	numeros := make([]int, 92)
	for i := range numeros {
		numeros[i] = i
	}
	casos := []struct {
		nome           string
		colecao        []int
		pagina         int64
		itens          int
		quantos        int
		primeiro       int
		total, paginas int
	}{
		{"primeira página", numeros, 1, 100, 92, 0, 92, 1},
		{"última página parcial", numeros, 10, 10, 2, 90, 92, 10},
		{"além do fim", numeros, 11, 10, 0, -1, 92, 10},
		{"muito além do fim, sem estourar", numeros, 1 << 62, 500, 0, -1, 92, 1},
		{"coleção vazia", nil, 1, 10, 0, -1, 0, 0},
	}
	for _, c := range casos {
		p := Paginar(c.colecao, c.pagina, c.itens)
		if len(p.Itens) != c.quantos || p.Paginacao.Total != c.total || p.Paginacao.Paginas != c.paginas {
			t.Errorf("%s: %d itens, total %d, páginas %d; esperado %d, %d, %d",
				c.nome, len(p.Itens), p.Paginacao.Total, p.Paginacao.Paginas, c.quantos, c.total, c.paginas)
		}
		if c.quantos > 0 && p.Itens[0] != c.primeiro {
			t.Errorf("%s: primeiro item %d, esperado %d", c.nome, p.Itens[0], c.primeiro)
		}
		if p.Paginacao.Pagina != c.pagina || p.Paginacao.Itens != c.itens {
			t.Errorf("%s: paginação %+v não repete o pedido", c.nome, p.Paginacao)
		}
		if p.Itens == nil {
			t.Errorf("%s: lista nil sairia como null no JSON", c.nome)
		}
	}
}

func TestResolverUF(t *testing.T) {
	casos := []struct {
		entrada, codigo, tipo string
	}{
		{" rj ", "33", ""},
		{"RJ", "33", ""},
		{"33", "33", ""},
		{"df", "53", ""},
		{"XX", "", "nao-encontrado"},
		{"99", "", "nao-encontrado"},
		{"R1", "", "entrada-invalida"},
		{"123", "", "entrada-invalida"},
		{"", "", "entrada-invalida"},
		{"３３", "", "entrada-invalida"}, // dígitos de largura total não são ASCII
	}
	for _, c := range casos {
		codigo, err := ResolverUF(c.entrada)
		if codigo != c.codigo || tipoDe(err) != c.tipo {
			t.Errorf("ResolverUF(%q) = (%q, %v), esperado (%q, %s)", c.entrada, codigo, err, c.codigo, c.tipo)
		}
	}
	_, err := ResolverUF("R1")
	if !strings.Contains(err.Error(), "recebi 'R1'") {
		t.Errorf("detalhe sem o valor recebido: %v", err)
	}
	_, err = ResolverUF("XX")
	if err.Error() != "não existe UF 'XX'" {
		t.Errorf("detalhe diferente do E1: %v", err)
	}
}

func TestValidarCodigoMunicipio(t *testing.T) {
	for _, valido := range []string{"3304557", "5300108"} {
		if _, err := ValidarCodigoMunicipio(valido); err != nil {
			t.Errorf("%q deveria valer: %v", valido, err)
		}
	}
	for _, invalido := range []string{"12ab", "123456", "12345678", "330455７", "", " 3304557"} {
		_, err := ValidarCodigoMunicipio(invalido)
		if tipoDe(err) != "entrada-invalida" {
			t.Errorf("%q deveria dar entrada-invalida, deu %v", invalido, err)
		}
	}
	_, err := ValidarCodigoMunicipio("12ab")
	if err.Error() != "código de município inválido: precisa ter exatamente 7 dígitos, recebi '12ab'" {
		t.Errorf("detalhe diferente do E1: %v", err)
	}
}

func TestValidarPaginacao(t *testing.T) {
	casos := []struct {
		pagina int64
		itens  int
		tipo   string
		trecho string
	}{
		{1, 100, "", ""},
		{1 << 62, 500, "", ""},
		{0, 100, "entrada-invalida", "pagina precisa ser maior ou igual a 1, recebi 0"},
		{1, 0, "entrada-invalida", "itens precisa estar entre 1 e 500, recebi 0"},
		{1, 501, "entrada-invalida", "itens precisa estar entre 1 e 500, recebi 501"},
	}
	for _, c := range casos {
		err := ValidarPaginacao(c.pagina, c.itens, 500)
		if tipoDe(err) != c.tipo || (c.trecho != "" && err.Error() != c.trecho) {
			t.Errorf("ValidarPaginacao(%d, %d) = %v, esperado %q", c.pagina, c.itens, err, c.trecho)
		}
	}
}

func TestValidarNome(t *testing.T) {
	if nome, err := ValidarNome("  são  "); err != nil || nome != "são" {
		t.Errorf("ValidarNome aparado = (%q, %v)", nome, err)
	}
	casos := []struct{ entrada, trecho string }{
		{"a", "pelo menos 2"},
		{"  a  ", "pelo menos 2"},
		{"", "pelo menos 2"},
		{strings.Repeat("x", 61), "no máximo 60"},
	}
	for _, c := range casos {
		_, err := ValidarNome(c.entrada)
		if tipoDe(err) != "entrada-invalida" || !strings.Contains(err.Error(), c.trecho) {
			t.Errorf("ValidarNome(%q) = %v, esperado %q", c.entrada, err, c.trecho)
		}
	}
	if _, err := ValidarNome(strings.Repeat("ã", 60)); err != nil {
		t.Errorf("60 caracteres (não bytes) deveriam valer: %v", err)
	}
}

func TestReprComoNoPython(t *testing.T) {
	casos := map[string]string{
		"R1":          "'R1'",
		"d'Oeste":     `"d'Oeste"`,
		`a\b`:         `'a\\b'`,
		"linha\nnova": `'linha\nnova'`,
	}
	for entrada, esperado := range casos {
		if obtido := Repr(entrada); obtido != esperado {
			t.Errorf("Repr(%q) = %s, esperado %s", entrada, obtido, esperado)
		}
	}
}

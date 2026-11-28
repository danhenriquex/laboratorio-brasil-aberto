// Package dominio tem as entidades e as regras do serviço (data-model do E1 e do E7). Não importa net/http.
package dominio

import (
	"cmp"
	"regexp"
	"slices"
	"strconv"
	"strings"
	"unicode"
	"unicode/utf8"

	"golang.org/x/text/cases"
	"golang.org/x/text/runes"
	"golang.org/x/text/transform"
	"golang.org/x/text/unicode/norm"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/erros"
)

// UFsOficiais tem o código e a sigla das 27 UFs, usados só para validar e resolver a entrada (R1 do E1).
// Nomes e regiões vêm sempre do IBGE.
var UFsOficiais = map[string]string{
	"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
	"21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA",
	"31": "MG", "32": "ES", "33": "RJ", "35": "SP",
	"41": "PR", "42": "SC", "43": "RS",
	"50": "MS", "51": "MT", "52": "GO", "53": "DF",
}

var codigoPorSigla = func() map[string]string {
	m := make(map[string]string, len(UFsOficiais))
	for codigo, sigla := range UFsOficiais {
		m[sigla] = codigo
	}
	return m
}()

// No RE2 do Go, \d e [A-Za-z] já são só ASCII: dígitos e letras de outros alfabetos não passam.
var (
	reSigla           = regexp.MustCompile(`^[A-Za-z]{2}$`)
	reCodigoUF        = regexp.MustCompile(`^[0-9]{2}$`)
	reCodigoMunicipio = regexp.MustCompile(`^[0-9]{7}$`)
)

const (
	NomeMin = 2
	NomeMax = 60
)

type Regiao struct {
	Codigo string `json:"codigo"`
	Sigla  string `json:"sigla"`
	Nome   string `json:"nome"`
}

type UF struct {
	Codigo string `json:"codigo"`
	Sigla  string `json:"sigla"`
	Nome   string `json:"nome"`
	Regiao Regiao `json:"regiao"`
}

type UFResumida struct {
	Codigo string `json:"codigo"`
	Sigla  string `json:"sigla"`
	Nome   string `json:"nome"`
}

type RegiaoImediata struct {
	Codigo string `json:"codigo"`
	Nome   string `json:"nome"`
}

type RegiaoIntermediaria struct {
	Codigo string `json:"codigo"`
	Nome   string `json:"nome"`
}

type MunicipioResumido struct {
	Codigo string `json:"codigo"`
	Nome   string `json:"nome"`
}

type Municipio struct {
	Codigo              string              `json:"codigo"`
	Nome                string              `json:"nome"`
	UF                  UFResumida          `json:"uf"`
	RegiaoImediata      RegiaoImediata      `json:"regiao_imediata"`
	RegiaoIntermediaria RegiaoIntermediaria `json:"regiao_intermediaria"`
}

// Paginacao vai no envelope das listas. Pagina é int64 porque pagina=99999999999 estoura 32 bits (T045 do E4).
type Paginacao struct {
	Pagina  int64 `json:"pagina"`
	Itens   int   `json:"itens"`
	Total   int   `json:"total"`
	Paginas int   `json:"paginas"`
}

type Pagina[T any] struct {
	Itens     []T
	Paginacao Paginacao
}

// Item é o que pode ser ordenado por nome: UFs e municípios.
type Item interface {
	nomeEcodigo() (string, string)
}

func (u UF) nomeEcodigo() (string, string)                { return u.Nome, u.Codigo }
func (m MunicipioResumido) nomeEcodigo() (string, string) { return m.Nome, m.Codigo }

// Dobrar aplica a regra do R8 do E1: NFKD, sem marcas diacríticas (categoria Mn) e casefold.
// O transform do x/text guarda estado, então a cadeia é criada a cada chamada.
func Dobrar(texto string) string {
	cadeia := transform.Chain(norm.NFKD, runes.Remove(runes.In(unicode.Mn)), cases.Fold())
	dobrado, _, err := transform.String(cadeia, texto)
	if err != nil {
		return strings.ToLower(texto)
	}
	return dobrado
}

// Ordenar devolve uma cópia ordenada por (nome dobrado, código), a mesma chave do E1 e do E4.
func Ordenar[T Item](itens []T) []T {
	type comChave struct {
		item         T
		nome, codigo string
	}
	chaves := make([]comChave, len(itens))
	for i, item := range itens {
		nome, codigo := item.nomeEcodigo()
		chaves[i] = comChave{item, Dobrar(nome), codigo}
	}
	slices.SortStableFunc(chaves, func(a, b comChave) int {
		return cmp.Or(strings.Compare(a.nome, b.nome), strings.Compare(a.codigo, b.codigo))
	})
	ordenados := make([]T, len(itens))
	for i, c := range chaves {
		ordenados[i] = c.item
	}
	return ordenados
}

// FiltrarPorNome mantém os municípios cujo nome dobrado contém o termo dobrado.
func FiltrarPorNome(itens []MunicipioResumido, nome string) []MunicipioResumido {
	alvo := Dobrar(strings.TrimSpace(nome))
	var filtrados []MunicipioResumido
	for _, item := range itens {
		if strings.Contains(Dobrar(item.Nome), alvo) {
			filtrados = append(filtrados, item)
		}
	}
	return filtrados
}

// Paginar fatia uma coleção já filtrada e ordenada. Página além do fim devolve lista vazia com o total
// correto, sem estourar a conta mesmo com páginas enormes.
func Paginar[T any](colecao []T, pagina int64, itens int) Pagina[T] {
	total := len(colecao)
	paginas := 0
	if total > 0 {
		paginas = (total + itens - 1) / itens
	}
	fatia := []T{}
	if pagina >= 1 && pagina <= int64(paginas) {
		inicio := int(pagina-1) * itens
		fim := min(inicio+itens, total)
		fatia = append(fatia, colecao[inicio:fim]...)
	}
	return Pagina[T]{
		Itens:     fatia,
		Paginacao: Paginacao{Pagina: pagina, Itens: itens, Total: total, Paginas: paginas},
	}
}

// ResolverUF aceita a sigla (sem diferenciar maiúsculas) ou o código de 2 dígitos e devolve o código.
func ResolverUF(param string) (string, error) {
	valor := strings.TrimSpace(param)
	var codigo string
	switch {
	case reSigla.MatchString(valor):
		codigo = codigoPorSigla[strings.ToUpper(valor)]
	case reCodigoUF.MatchString(valor):
		if _, ok := UFsOficiais[valor]; ok {
			codigo = valor
		}
	default:
		return "", erros.EntradaInvalida(
			"UF inválida: use a sigla de 2 letras (ex.: RJ) ou o código de 2 dígitos (ex.: 33), recebi %s", Repr(param))
	}
	if codigo == "" {
		return "", erros.NaoEncontrado("não existe UF %s", Repr(valor))
	}
	return codigo, nil
}

func ValidarCodigoMunicipio(codigo string) (string, error) {
	if !reCodigoMunicipio.MatchString(codigo) {
		return "", erros.EntradaInvalida(
			"código de município inválido: precisa ter exatamente 7 dígitos, recebi %s", Repr(codigo))
	}
	return codigo, nil
}

func ValidarPaginacao(pagina int64, itens, itensMax int) error {
	if pagina < 1 {
		return erros.EntradaInvalida("pagina precisa ser maior ou igual a 1, recebi %d", pagina)
	}
	if itens < 1 || itens > itensMax {
		return erros.EntradaInvalida("itens precisa estar entre 1 e %d, recebi %d", itensMax, itens)
	}
	return nil
}

// ValidarNome conta caracteres (runas), não bytes, como o len() do Python.
func ValidarNome(nome string) (string, error) {
	valor := strings.TrimSpace(nome)
	n := utf8.RuneCountInString(valor)
	if n < NomeMin {
		return "", erros.EntradaInvalida("nome precisa ter pelo menos %d caracteres, sem contar espaços nas pontas", NomeMin)
	}
	if n > NomeMax {
		return "", erros.EntradaInvalida("nome pode ter no máximo %d caracteres", NomeMax)
	}
	return valor, nil
}

// Repr imita o repr() do Python que o E1 usa nas mensagens ('R1', "d'Oeste"), para os detalhes saírem iguais.
func Repr(s string) string {
	aspas := byte('\'')
	if strings.ContainsRune(s, '\'') && !strings.ContainsRune(s, '"') {
		aspas = '"'
	}
	var b strings.Builder
	b.WriteByte(aspas)
	for _, r := range s {
		switch {
		case r == '\\':
			b.WriteString(`\\`)
		case r == rune(aspas):
			b.WriteByte('\\')
			b.WriteRune(r)
		case r == '\n':
			b.WriteString(`\n`)
		case r == '\r':
			b.WriteString(`\r`)
		case r == '\t':
			b.WriteString(`\t`)
		case !unicode.IsPrint(r):
			b.WriteString(strconv.QuoteRuneToASCII(r)[1 : len(strconv.QuoteRuneToASCII(r))-1])
		default:
			b.WriteRune(r)
		}
	}
	b.WriteByte(aspas)
	return b.String()
}

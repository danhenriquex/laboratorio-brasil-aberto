package api

import (
	"errors"
	"math"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"unicode/utf8"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/dominio"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/erros"
)

// consulta são os parâmetros da query, lidos como o research do E7 (R4) decidiu. O URL.Query() do Go
// descartaria em silêncio os pares mal codificados, e o Get devolveria o primeiro valor de um parâmetro
// repetido; aqui a codificação inválida é recusada e vale o último valor, como no E1.
type consulta url.Values

func lerConsulta(r *http.Request) (consulta, error) {
	valores, err := url.ParseQuery(r.URL.RawQuery)
	if err != nil {
		return nil, malCodificada()
	}
	for chave, lista := range valores {
		if !utf8.ValidString(chave) {
			return nil, malCodificada()
		}
		for _, v := range lista {
			if !utf8.ValidString(v) {
				return nil, malCodificada()
			}
		}
	}
	return consulta(valores), nil
}

// malCodificada é a lição da T046 do E4: lá, ?nome=%ZZ virava 500.
func malCodificada() error {
	return erros.EntradaInvalida("os parâmetros da consulta têm codificação inválida")
}

// ultimo devolve o último valor de um parâmetro e se ele veio.
func (c consulta) ultimo(nome string) (string, bool) {
	lista := c[nome]
	if len(lista) == 0 {
		return "", false
	}
	return lista[len(lista)-1], true
}

// inteiro lê um parâmetro inteiro como o int() do Python: aceita espaços nas pontas e sinal. Vazio ou
// ausente usa o padrão. Só dígitos, mas grande demais para int64, vale como o maior valor: para pagina, é
// uma página além do fim, e não um erro (T045 do E4). A validação de faixa fica com o domínio, para o
// detalhe citar o limite configurado.
func (c consulta) inteiro(nome string, padrao int64) (int64, error) {
	bruto, ok := c.ultimo(nome)
	valor := strings.TrimSpace(bruto)
	if !ok || valor == "" {
		return padrao, nil
	}
	n, err := strconv.ParseInt(valor, 10, 64)
	if errors.Is(err, strconv.ErrRange) {
		if strings.HasPrefix(valor, "-") {
			return math.MinInt64, nil
		}
		return math.MaxInt64, nil
	}
	if err != nil {
		return 0, erros.EntradaInvalida("%s precisa ser um número inteiro, recebi %s", nome, dominio.Repr(bruto))
	}
	return n, nil
}

// Package config lê as variáveis LOCALIDADES_*, comuns ao E1, ao E4 e ao E7, com os mesmos padrões
// (R14 do E1) e as regras de validação do E4 depois da T049 (research do E7, R11).
package config

import (
	"errors"
	"fmt"
	"math"
	"strconv"
	"strings"
	"time"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/dominio"
)

const IBGEURLPadrao = "https://servicodados.ibge.gov.br/api/v1/localidades"

// Prazo e validade ficam entre 1 ms e 10⁹ s: abaixo disso o valor arredonda para zero, acima não cabe no
// relógio monotônico em nanossegundos, e o infinito deixaria a consulta ao IBGE sem prazo (T049 do E4).
const (
	segundosMin = 0.001
	segundosMax = 1e9
)

type Configuracao struct {
	IBGEURL    string
	PrazoFonte time.Duration
	Validade   time.Duration
	ItensMax   int
	Host       string
	Porta      int
}

// Carregar lê a configuração por uma função como os.Getenv. Um valor inválido impede a partida: o erro
// cita a variável e o valor recebido, e o main acrescenta "configuração inválida:", como no E1.
func Carregar(getenv func(string) string) (Configuracao, error) {
	bruto := func(nome string) string { return strings.TrimSpace(getenv(nome)) }
	texto := func(nome, padrao string) string {
		if v := bruto(nome); v != "" {
			return v
		}
		return padrao
	}

	c := Configuracao{Host: texto("LOCALIDADES_HOST", "127.0.0.1")}

	c.IBGEURL = strings.TrimRight(texto("LOCALIDADES_IBGE_URL", IBGEURLPadrao), "/")
	if !strings.HasPrefix(c.IBGEURL, "http://") && !strings.HasPrefix(c.IBGEURL, "https://") {
		return c, fmt.Errorf("LOCALIDADES_IBGE_URL precisa começar com http:// ou https://, recebi %s", dominio.Repr(c.IBGEURL))
	}

	var err error
	if c.Porta, err = inteiro("LOCALIDADES_PORTA", bruto("LOCALIDADES_PORTA"), 8000, 65535); err != nil {
		return c, err
	}
	if c.ItensMax, err = inteiro("LOCALIDADES_ITENS_MAX", bruto("LOCALIDADES_ITENS_MAX"), 500, math.MaxInt32); err != nil {
		return c, err
	}
	if c.PrazoFonte, err = segundos("LOCALIDADES_PRAZO_FONTE_S", bruto("LOCALIDADES_PRAZO_FONTE_S"), 10); err != nil {
		return c, err
	}
	if c.Validade, err = segundos("LOCALIDADES_VALIDADE_S", bruto("LOCALIDADES_VALIDADE_S"), 86400); err != nil {
		return c, err
	}
	return c, nil
}

func inteiro(nome, valor string, padrao, maximo int) (int, error) {
	if valor == "" {
		return padrao, nil
	}
	n, err := strconv.Atoi(valor)
	if err != nil && !errors.Is(err, strconv.ErrRange) {
		return 0, fmt.Errorf("%s precisa ser um número inteiro, recebi %s", nome, dominio.Repr(valor))
	}
	if err == nil && n <= 0 {
		return 0, fmt.Errorf("%s precisa ser maior que zero, recebi %s", nome, dominio.Repr(valor))
	}
	if err != nil || n > maximo {
		if maximo == 65535 {
			return 0, fmt.Errorf("%s precisa estar entre 1 e 65535, recebi %s", nome, dominio.Repr(valor))
		}
		return 0, fmt.Errorf("%s precisa ser de no máximo %d, recebi %s", nome, maximo, dominio.Repr(valor))
	}
	return n, nil
}

// segundos aceita o que o ParseFloat aceita, mas recusa NaN e infinito, que ele também aceita
// ("NaN", "Inf", "infinity" e números como 1e400, que estouram para infinito).
func segundos(nome, valor string, padrao float64) (time.Duration, error) {
	if valor == "" {
		return time.Duration(padrao * float64(time.Second)), nil
	}
	s, err := strconv.ParseFloat(valor, 64)
	if err != nil && !errors.Is(err, strconv.ErrRange) {
		return 0, fmt.Errorf("%s precisa ser um número, recebi %s", nome, dominio.Repr(valor))
	}
	recebi := dominio.Repr(valor)
	switch {
	case math.IsNaN(s) || math.IsInf(s, 0):
		return 0, fmt.Errorf("%s precisa ser um número finito, recebi %s", nome, recebi)
	case s <= 0:
		return 0, fmt.Errorf("%s precisa ser maior que zero, recebi %s", nome, recebi)
	case s < segundosMin:
		return 0, fmt.Errorf("%s precisa ser de pelo menos 0.001 (1 ms), recebi %s", nome, recebi)
	case s > segundosMax:
		return 0, fmt.Errorf("%s precisa ser de no máximo 1000000000 (10⁹ s), recebi %s", nome, recebi)
	}
	return time.Duration(math.Round(s * float64(time.Second))), nil
}

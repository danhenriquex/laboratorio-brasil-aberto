package config

import (
	"strings"
	"testing"
	"time"
)

func ambiente(valores map[string]string) func(string) string {
	return func(nome string) string { return valores[nome] }
}

func TestPadroesDoE1(t *testing.T) {
	c, err := Carregar(ambiente(nil))
	if err != nil {
		t.Fatal(err)
	}
	esperado := Configuracao{
		IBGEURL:    "https://servicodados.ibge.gov.br/api/v1/localidades",
		PrazoFonte: 10 * time.Second,
		Validade:   86400 * time.Second,
		ItensMax:   500,
		Host:       "127.0.0.1",
		Porta:      8000,
	}
	if c != esperado {
		t.Errorf("padrões = %+v, esperado %+v", c, esperado)
	}
}

func TestLeituraDasVariaveisLocalidades(t *testing.T) {
	c, err := Carregar(ambiente(map[string]string{
		"LOCALIDADES_IBGE_URL":      "http://127.0.0.1:8099/api/v1/localidades/",
		"LOCALIDADES_PRAZO_FONTE_S": "1.5",
		"LOCALIDADES_VALIDADE_S":    " 2 ",
		"LOCALIDADES_ITENS_MAX":     "50",
		"LOCALIDADES_PORTA":         "8090",
		"LOCALIDADES_HOST":          "0.0.0.0",
	}))
	if err != nil {
		t.Fatal(err)
	}
	if c.IBGEURL != "http://127.0.0.1:8099/api/v1/localidades" {
		t.Errorf("URL sem barra final: %q", c.IBGEURL)
	}
	if c.PrazoFonte != 1500*time.Millisecond || c.Validade != 2*time.Second || c.ItensMax != 50 || c.Porta != 8090 || c.Host != "0.0.0.0" {
		t.Errorf("leitura = %+v", c)
	}
}

func TestVariavelVaziaUsaOPadrao(t *testing.T) {
	c, err := Carregar(ambiente(map[string]string{"LOCALIDADES_PRAZO_FONTE_S": "  ", "LOCALIDADES_HOST": ""}))
	if err != nil || c.PrazoFonte != 10*time.Second || c.Host != "127.0.0.1" {
		t.Errorf("vazio deveria usar o padrão: %+v, %v", c, err)
	}
}

// Valores inválidos impedem a partida, com mensagem que cita a variável e o valor recebido (R14 do E1;
// T049 do E4: número finito entre 0,001 e 10⁹ para prazo e validade).
func TestValoresInvalidosImpedemAPartida(t *testing.T) {
	casos := []struct{ variavel, valor, trecho string }{
		{"LOCALIDADES_PRAZO_FONTE_S", "abc", "precisa ser um número"},
		{"LOCALIDADES_PRAZO_FONTE_S", "0", "maior que zero"},
		{"LOCALIDADES_PRAZO_FONTE_S", "-1", "maior que zero"},
		{"LOCALIDADES_PRAZO_FONTE_S", "NaN", "finito"},
		{"LOCALIDADES_PRAZO_FONTE_S", "Inf", "finito"},
		{"LOCALIDADES_PRAZO_FONTE_S", "infinity", "finito"},
		{"LOCALIDADES_PRAZO_FONTE_S", "0.0001", "pelo menos 0.001"},
		{"LOCALIDADES_VALIDADE_S", "x", "precisa ser um número"},
		{"LOCALIDADES_VALIDADE_S", "1e300", "no máximo 1000000000"},
		{"LOCALIDADES_VALIDADE_S", "1e400", "finito"},
		{"LOCALIDADES_VALIDADE_S", "Infinity", "finito"},
		{"LOCALIDADES_VALIDADE_S", "0.0001", "pelo menos 0.001"},
		{"LOCALIDADES_ITENS_MAX", "0", "maior que zero"},
		{"LOCALIDADES_ITENS_MAX", "1.5", "precisa ser um número inteiro"},
		{"LOCALIDADES_IBGE_URL", "ftp://ibge", "precisa começar com http:// ou https://"},
		{"LOCALIDADES_PORTA", "abc", "precisa ser um número inteiro"},
		{"LOCALIDADES_PORTA", "99999", "entre 1 e 65535"},
	}
	for _, c := range casos {
		_, err := Carregar(ambiente(map[string]string{c.variavel: c.valor}))
		if err == nil {
			t.Errorf("%s=%s deveria impedir a partida", c.variavel, c.valor)
			continue
		}
		msg := err.Error()
		if !strings.HasPrefix(msg, c.variavel+" ") || !strings.Contains(msg, c.trecho) || !strings.Contains(msg, "recebi '") {
			t.Errorf("%s=%s: mensagem %q não cita a variável, %q e o valor recebido", c.variavel, c.valor, msg, c.trecho)
		}
	}
}

func TestLimitesAceitos(t *testing.T) {
	c, err := Carregar(ambiente(map[string]string{
		"LOCALIDADES_PRAZO_FONTE_S": "0.001",
		"LOCALIDADES_VALIDADE_S":    "1000000000",
	}))
	if err != nil {
		t.Fatal(err)
	}
	if c.PrazoFonte != time.Millisecond || c.Validade != 1_000_000_000*time.Second {
		t.Errorf("limites = %v e %v", c.PrazoFonte, c.Validade)
	}
}

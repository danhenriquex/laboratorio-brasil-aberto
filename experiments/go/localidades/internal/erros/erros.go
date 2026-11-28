// Package erros define os erros de domínio e seus tipos de problema (RFC 9457), com os mesmos tipos,
// títulos e status do E1 (research do E1, R11; data-model do E7).
package erros

import "fmt"

// PrefixoURN é o início do "type" de todo problema.
const PrefixoURN = "urn:brasil-aberto:problema:"

// ErroDominio é um erro que o serviço sabe classificar. Go não tem exceções: o erro é um valor devolvido,
// e o adaptador HTTP o converte em application/problem+json.
type ErroDominio struct {
	Tipo    string
	Titulo  string
	Status  int
	Detalhe string
}

func (e *ErroDominio) Error() string { return e.Detalhe }

// URN é o "type" do problema.
func (e *ErroDominio) URN() string { return PrefixoURN + e.Tipo }

// DeFonte diz se o erro veio do IBGE (o equivalente ao ERROS_DE_FONTE do E1).
func (e *ErroDominio) DeFonte() bool {
	switch e.Tipo {
	case "fonte-indisponivel", "fonte-lenta", "resposta-inesperada-da-fonte":
		return true
	}
	return false
}

func novo(tipo, titulo string, status int, formato string, args ...any) *ErroDominio {
	return &ErroDominio{Tipo: tipo, Titulo: titulo, Status: status, Detalhe: fmt.Sprintf(formato, args...)}
}

func EntradaInvalida(formato string, args ...any) *ErroDominio {
	return novo("entrada-invalida", "Entrada inválida", 400, formato, args...)
}

func NaoEncontrado(formato string, args ...any) *ErroDominio {
	return novo("nao-encontrado", "Não encontrado", 404, formato, args...)
}

func FonteIndisponivel(formato string, args ...any) *ErroDominio {
	return novo("fonte-indisponivel", "Fonte indisponível", 502, formato, args...)
}

func FonteLenta(formato string, args ...any) *ErroDominio {
	return novo("fonte-lenta", "Fonte lenta", 504, formato, args...)
}

func RespostaInesperadaDaFonte(formato string, args ...any) *ErroDominio {
	return novo("resposta-inesperada-da-fonte", "Resposta inesperada da fonte", 502, formato, args...)
}

// ErroInterno tem sempre o mesmo detalhe genérico, sem rastro de execução (FR-013 do E1).
func ErroInterno() *ErroDominio {
	return novo("erro-interno", "Erro interno do serviço", 500, "erro interno do serviço")
}

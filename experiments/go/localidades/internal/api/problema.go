// Package api é o adaptador HTTP: handler de topo, rotas v1, envelope e problem+json. O contrato é o
// openapi.yaml escrito à mão em contracts/localidades/; nada aqui gera OpenAPI (R3 do E1).
package api

import (
	"bytes"
	"encoding/json"
	"errors"
	"net/http"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/erros"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/operacao"
)

// problema tem os campos na ordem do E1: type, title, status, detail, correlacao_id.
type problema struct {
	Type         string `json:"type"`
	Title        string `json:"title"`
	Status       int    `json:"status"`
	Detail       string `json:"detail"`
	CorrelacaoID string `json:"correlacao_id"`
}

// codificar escreve JSON sem escapar <, > e & (o padrão do Go os troca por sequências unicode escapadas), e
// sem a quebra de linha final que o Encoder acrescenta.
func codificar(v any) []byte {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	if err := enc.Encode(v); err != nil {
		return []byte(`{}`)
	}
	return bytes.TrimRight(buf.Bytes(), "\n")
}

// EscreverJSON responde sempre em application/json, ignorando o Accept (T048 do E4).
func EscreverJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_, _ = w.Write(codificar(v))
}

// EscreverProblema converte um erro em application/problem+json. Um erro que não é de domínio vira 500
// erro-interno, com detalhe genérico e sem rastro de execução.
func EscreverProblema(w http.ResponseWriter, r *http.Request, err error) {
	var e *erros.ErroDominio
	if !errors.As(err, &e) {
		e = erros.ErroInterno()
	}
	estado := operacao.EstadoDe(r.Context())
	estado.DefinirTipoErro(e.Tipo)
	w.Header().Set("Content-Type", "application/problem+json")
	w.WriteHeader(e.Status)
	_, _ = w.Write(codificar(problema{
		Type:         e.URN(),
		Title:        e.Titulo,
		Status:       e.Status,
		Detail:       e.Detalhe,
		CorrelacaoID: estado.Correlacao,
	}))
}

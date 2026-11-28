package api

import (
	"math"
	"net/http"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/dominio"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/operacao"
	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/servico"
)

// Resposta é o envelope do contrato, com os campos na ordem do E1: dados, paginacao (só nas listas
// paginadas) e meta.
type Resposta struct {
	Dados     any                `json:"dados"`
	Paginacao *dominio.Paginacao `json:"paginacao,omitempty"`
	Meta      servico.Meta       `json:"meta"`
}

// responder escreve o envelope e anota o uso da cópia guardada para as métricas e o registro.
func responder(w http.ResponseWriter, r *http.Request, res servico.Resultado) error {
	operacao.EstadoDe(r.Context()).DefinirCache(res.Cache)
	EscreverJSON(w, http.StatusOK, Resposta{Dados: res.Dados, Paginacao: res.Paginacao, Meta: res.Meta})
	return nil
}

// RegistrarV1 registra as rotas v1 do contrato no roteador.
func RegistrarV1(rt *Roteador, s *servico.Servico) {
	rt.Rota("GET /v1/ufs", func(w http.ResponseWriter, r *http.Request) error {
		res, err := s.ListarUFs(r.Context())
		if err != nil {
			return err
		}
		return responder(w, r, res)
	})

	rt.Rota("GET /v1/ufs/{uf}", func(w http.ResponseWriter, r *http.Request) error {
		res, err := s.ObterUF(r.Context(), r.PathValue("uf"))
		if err != nil {
			return err
		}
		return responder(w, r, res)
	})

	rt.Rota("GET /v1/ufs/{uf}/municipios", func(w http.ResponseWriter, r *http.Request) error {
		q, err := lerConsulta(r)
		if err != nil {
			return err
		}
		pagina, err := q.inteiro("pagina", 1)
		if err != nil {
			return err
		}
		itens, err := q.inteiro("itens", 100)
		if err != nil {
			return err
		}
		var nome *string
		if v, ok := q.ultimo("nome"); ok {
			nome = &v
		}
		res, err := s.ListarMunicipios(r.Context(), r.PathValue("uf"), pagina, limitarInt(itens), nome)
		if err != nil {
			return err
		}
		return responder(w, r, res)
	})
}

// limitarInt converte para int sem estourar, mantendo o valor fora da faixa para a validação do domínio.
func limitarInt(n int64) int {
	switch {
	case n > math.MaxInt32:
		return math.MaxInt32
	case n < math.MinInt32:
		return math.MinInt32
	}
	return int(n)
}

package api

import (
	"net/http"

	"github.com/danhenriquex/laboratorio-brasil-aberto/experiments/go/localidades/internal/servico"
)

// registrarMunicipios registra GET /v1/municipios/{codigo} (US2).
func registrarMunicipios(rt *Roteador, s *servico.Servico) {
	rt.Rota("GET /v1/municipios/{codigo}", func(w http.ResponseWriter, r *http.Request) error {
		res, err := s.ObterMunicipio(r.Context(), r.PathValue("codigo"))
		if err != nil {
			return err
		}
		return responder(w, r, res)
	})
}

package io.github.danhenriquex.brasilaberto.localidades.api;

import io.github.danhenriquex.brasilaberto.localidades.dominio.Municipio;
import io.github.danhenriquex.brasilaberto.localidades.servico.ServicoLocalidades;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

/** GET /v1/municipios/{codigo} (US2). */
@RestController
public class MunicipiosController {

    private final ServicoLocalidades servico;

    public MunicipiosController(ServicoLocalidades servico) {
        this.servico = servico;
    }

    @GetMapping("/v1/municipios/{codigo}")
    public Resposta<Municipio> obterMunicipio(@PathVariable String codigo, HttpServletRequest pedido) {
        return Resposta.de(servico.obterMunicipio(codigo), pedido);
    }
}

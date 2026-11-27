package io.github.danhenriquex.brasilaberto.localidades.api;

import com.fasterxml.jackson.annotation.JsonInclude;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Meta;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Paginacao;
import io.github.danhenriquex.brasilaberto.localidades.servico.Resultado;
import jakarta.servlet.http.HttpServletRequest;

/** Envelope do contrato: {dados, meta}, e {dados, paginacao, meta} nas listas paginadas. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record Resposta<T>(T dados, Paginacao paginacao, Meta meta) {

    public static final String ATRIBUTO_CACHE = "cache";

    /** Monta o envelope e anota no pedido o uso da cópia guardada, para as métricas e o registro. */
    public static <T> Resposta<T> de(Resultado<T> resultado, HttpServletRequest pedido) {
        pedido.setAttribute(ATRIBUTO_CACHE, resultado.cache());
        return new Resposta<>(resultado.dados(), resultado.paginacao(), resultado.meta());
    }
}

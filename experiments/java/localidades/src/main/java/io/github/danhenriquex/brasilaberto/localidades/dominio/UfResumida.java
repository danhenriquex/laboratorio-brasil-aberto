package io.github.danhenriquex.brasilaberto.localidades.dominio;

/** Entidade exposta (data-model do E1). Códigos são sempre texto de tamanho fixo (R7 do E1). */
public record UfResumida(String codigo, String sigla, String nome) {}

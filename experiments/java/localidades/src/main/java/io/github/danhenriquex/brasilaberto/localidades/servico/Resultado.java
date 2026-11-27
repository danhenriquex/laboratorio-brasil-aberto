package io.github.danhenriquex.brasilaberto.localidades.servico;

import io.github.danhenriquex.brasilaberto.localidades.dominio.Meta;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Paginacao;

/** O que um caso de uso devolve ao adaptador HTTP. paginacao é nula fora das listas paginadas. */
public record Resultado<T>(T dados, Paginacao paginacao, Meta meta, String cache) {}

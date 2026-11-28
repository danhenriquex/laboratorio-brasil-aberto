package io.github.danhenriquex.brasilaberto.localidades.servico;

import io.github.danhenriquex.brasilaberto.localidades.dominio.Meta;

/** Um recurso do IBGE já normalizado, com a procedência e o uso da cópia guardada (acerto, falta, desatualizado). */
public record Obtido<T>(T dados, Meta meta, String cache) {}

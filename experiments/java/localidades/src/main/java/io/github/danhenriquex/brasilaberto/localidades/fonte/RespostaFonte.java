package io.github.danhenriquex.brasilaberto.localidades.fonte;

/** Dado já normalizado e a URL do IBGE consultada para obtê-lo. */
public record RespostaFonte<T>(T dados, String urlFonte) {}

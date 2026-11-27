package io.github.danhenriquex.brasilaberto.localidades.dominio;

import java.util.Map;
import java.util.stream.Collectors;

/** Código e sigla das 27 UFs, usados só para validar e resolver a entrada (R1 do E1). Nomes vêm do IBGE. */
public final class UfsOficiais {

    public static final Map<String, String> CODIGO_PARA_SIGLA = Map.ofEntries(
            Map.entry("11", "RO"), Map.entry("12", "AC"), Map.entry("13", "AM"), Map.entry("14", "RR"),
            Map.entry("15", "PA"), Map.entry("16", "AP"), Map.entry("17", "TO"), Map.entry("21", "MA"),
            Map.entry("22", "PI"), Map.entry("23", "CE"), Map.entry("24", "RN"), Map.entry("25", "PB"),
            Map.entry("26", "PE"), Map.entry("27", "AL"), Map.entry("28", "SE"), Map.entry("29", "BA"),
            Map.entry("31", "MG"), Map.entry("32", "ES"), Map.entry("33", "RJ"), Map.entry("35", "SP"),
            Map.entry("41", "PR"), Map.entry("42", "SC"), Map.entry("43", "RS"), Map.entry("50", "MS"),
            Map.entry("51", "MT"), Map.entry("52", "GO"), Map.entry("53", "DF"));

    public static final Map<String, String> SIGLA_PARA_CODIGO = CODIGO_PARA_SIGLA.entrySet().stream()
            .collect(Collectors.toUnmodifiableMap(Map.Entry::getValue, Map.Entry::getKey));

    private UfsOficiais() {}
}

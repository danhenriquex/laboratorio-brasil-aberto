package io.github.danhenriquex.brasilaberto.localidades.dominio;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;

/** Procedência (Constituição II). coletado_em: ISO 8601 em UTC, sempre com milissegundos e Z. */
public record Meta(String fonte, String urlFonte, String urlDocumentacao, String coletadoEm, boolean desatualizado) {

    public static final String FONTE = "IBGE — API de localidades";
    public static final String URL_DOCUMENTACAO = "https://servicodados.ibge.gov.br/api/docs/localidades";

    // Instant.toString() omite os milissegundos quando são zero; o contrato exige \.\d{3}Z.
    private static final DateTimeFormatter FORMATO =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").withZone(ZoneOffset.UTC);

    public static Meta de(String urlFonte, Instant coletadoEm, boolean desatualizado) {
        return new Meta(FONTE, urlFonte, URL_DOCUMENTACAO, FORMATO.format(coletadoEm), desatualizado);
    }
}

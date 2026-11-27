package io.github.danhenriquex.brasilaberto.localidades.api;

import static org.assertj.core.api.Assertions.assertThat;

import java.nio.charset.StandardCharsets;
import java.util.regex.Pattern;
import org.springframework.test.web.servlet.MvcResult;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Asserções comuns dos testes de API, equivalentes ao assert_problema e assert_meta do E1. */
final class Apoio {

    static final JsonMapper JSON = JsonMapper.builder().build();
    static final Pattern COLETADO_EM = Pattern.compile("^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}Z$");

    private Apoio() {}

    static JsonNode json(MvcResult r) throws Exception {
        return JSON.readTree(r.getResponse().getContentAsString(StandardCharsets.UTF_8));
    }

    static JsonNode assertProblema(MvcResult r, int status, String tipo) throws Exception {
        assertThat(r.getResponse().getStatus()).as(r.getResponse().getContentAsString()).isEqualTo(status);
        assertThat(r.getResponse().getContentType()).startsWith("application/problem+json");
        JsonNode corpo = json(r);
        assertThat(corpo.get("type").asString()).isEqualTo("urn:brasil-aberto:problema:" + tipo);
        assertThat(corpo.get("status").asInt()).isEqualTo(status);
        assertThat(corpo.get("detail").asString()).isNotBlank();
        assertThat(corpo.get("correlacao_id").asString()).isEqualTo(r.getResponse().getHeader("X-Correlation-Id"));
        return corpo;
    }

    static void assertMeta(JsonNode meta, String urlFonte, boolean desatualizado) {
        assertThat(meta.get("fonte").asString()).isEqualTo("IBGE — API de localidades");
        assertThat(meta.get("url_fonte").asString()).isEqualTo(urlFonte);
        assertThat(meta.get("url_documentacao").asString()).isEqualTo("https://servicodados.ibge.gov.br/api/docs/localidades");
        assertThat(meta.get("coletado_em").asString()).matches(COLETADO_EM);
        assertThat(meta.get("desatualizado").asBoolean()).isEqualTo(desatualizado);
    }
}

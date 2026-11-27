package io.github.danhenriquex.brasilaberto.localidades.api;

import static io.github.danhenriquex.brasilaberto.localidades.api.Apoio.assertMeta;
import static io.github.danhenriquex.brasilaberto.localidades.api.Apoio.assertProblema;
import static io.github.danhenriquex.brasilaberto.localidades.api.Apoio.json;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import io.github.danhenriquex.brasilaberto.localidades.apoio.Fixtures;
import java.net.URI;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ArrayNode;

/** Mesmos casos do test_api_municipio.py do E1 (US2). */
class ApiMunicipioTest extends BaseApiTest {

    private static String itemDaUf(String uf, long codigo) {
        ArrayNode lista = (ArrayNode) Apoio.JSON.readTree(Fixtures.texto("municipios-uf-" + uf + ".json"));
        for (JsonNode item : lista) {
            if (item.get("id").asLong() == codigo) {
                return item.toString();
            }
        }
        throw new IllegalArgumentException("sem " + codigo);
    }

    @Test
    void municipioExistente() throws Exception {
        IBGE.responderJson("/municipios/3304557", itemDaUf("33", 3304557));
        var r = mvc.perform(get("/v1/municipios/3304557")).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        JsonNode corpo = json(r);
        assertThat(corpo.propertyNames()).containsExactlyInAnyOrder("dados", "meta");
        assertThat(corpo.get("dados").toString()).isEqualTo(
                "{\"codigo\":\"3304557\",\"nome\":\"Rio de Janeiro\","
                        + "\"uf\":{\"codigo\":\"33\",\"sigla\":\"RJ\",\"nome\":\"Rio de Janeiro\"},"
                        + "\"regiao_imediata\":{\"codigo\":\"330001\",\"nome\":\"Rio de Janeiro\"},"
                        + "\"regiao_intermediaria\":{\"codigo\":\"3301\",\"nome\":\"Rio de Janeiro\"}}");
        assertMeta(corpo.get("meta"), IBGE.url() + "/municipios/3304557", false);
        assertThat(IBGE.pedidos("/municipios/3304557")).isEqualTo(1);
    }

    @Test
    void codigoInexistenteE404() throws Exception {
        IBGE.responderJson("/municipios/9999999", "[]");
        assertProblema(mvc.perform(get("/v1/municipios/9999999")).andReturn(), 404, "nao-encontrado");
    }

    @ParameterizedTest
    @ValueSource(strings = {"12ab", "123456", "12345678", "330455%EF%BC%97"})
    void codigoMalFormadoE400SemConsultar(String codigo) throws Exception {
        assertProblema(mvc.perform(get(URI.create("/v1/municipios/" + codigo))).andReturn(), 400, "entrada-invalida");
        assertThat(IBGE.pedidosTotais()).isZero();
    }

    @Test
    void nomeComApostrofoSaiComoOIbgePublica() throws Exception {
        IBGE.responderJson("/municipios/3545803", itemDaUf("35", 3545803));
        var corpo = json(mvc.perform(get("/v1/municipios/3545803")).andReturn());
        assertThat(corpo.get("dados").get("nome").asString()).isEqualTo("Santa Bárbara d'Oeste");
    }

    @Test
    void municipioSemMicrorregiao() throws Exception {
        IBGE.responderFixture("/municipios/5101837", "municipio-5101837.json");
        var r = mvc.perform(get("/v1/municipios/5101837")).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(json(r).get("dados").get("uf").get("sigla").asString()).isEqualTo("MT");
    }

    @Test
    void municipioSemRegiaoImediataE502() throws Exception {
        IBGE.responderFixture("/municipios/3304557", "municipio-sem-regiao-imediata.json");
        assertProblema(mvc.perform(get("/v1/municipios/3304557")).andReturn(), 502, "resposta-inesperada-da-fonte");
    }
}

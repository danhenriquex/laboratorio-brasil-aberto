package io.github.danhenriquex.brasilaberto.localidades.api;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static io.github.danhenriquex.brasilaberto.localidades.api.Apoio.assertProblema;
import static io.github.danhenriquex.brasilaberto.localidades.api.Apoio.json;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import com.github.tomakehurst.wiremock.http.Fault;
import io.github.danhenriquex.brasilaberto.localidades.apoio.Fixtures;
import io.github.danhenriquex.brasilaberto.localidades.apoio.RelogioFalso;
import java.time.Duration;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.test.context.TestPropertySource;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ArrayNode;

/** Mesmos casos do test_api_falhas.py do E1 (US3), com relógio falso e prazo curto. */
@TestPropertySource(properties = "localidades.prazo-fonte-s=0.3")
@Import(ApiFalhasTest.Relogio.class)
class ApiFalhasTest extends BaseApiTest {

    @TestConfiguration
    static class Relogio {
        @Bean
        @Primary
        RelogioFalso relogioFalso() {
            return new RelogioFalso();
        }
    }

    @Autowired
    RelogioFalso relogio;

    private static final String ROTA = "/municipios/3304557";
    private static final String URL = "/v1/municipios/3304557";

    private static String rio() {
        ArrayNode lista = (ArrayNode) Apoio.JSON.readTree(Fixtures.texto("municipios-uf-33.json"));
        for (JsonNode item : lista) {
            if (item.get("id").asLong() == 3304557) return item.toString();
        }
        throw new IllegalStateException();
    }

    private void assertSemDetalhesInternos(JsonNode corpo) {
        assertThat(corpo.toString()).doesNotContain("<html", "Exception", "127.0.0.1", "Página de erro", "at java.");
    }

    @Test
    void fonteForaSemCopiaE502() throws Exception {
        IBGE.responder(ROTA, aResponse().withFault(Fault.CONNECTION_RESET_BY_PEER));
        assertSemDetalhesInternos(assertProblema(mvc.perform(get(URL)).andReturn(), 502, "fonte-indisponivel"));
        IBGE.responder(ROTA, aResponse().withStatus(503).withBody("Traceback interno do IBGE"));
        var corpo = assertProblema(mvc.perform(get(URL)).andReturn(), 502, "fonte-indisponivel");
        assertThat(corpo.toString()).doesNotContain("Traceback");
    }

    @Test
    void fonteLentaSemCopiaE504() throws Exception {
        IBGE.responder(ROTA, aResponse().withStatus(200).withBody(rio()).withFixedDelay(1500));
        long inicio = System.nanoTime();
        assertSemDetalhesInternos(assertProblema(mvc.perform(get(URL)).andReturn(), 504, "fonte-lenta"));
        assertThat((System.nanoTime() - inicio) / 1_000_000).isLessThan(1000);
    }

    @Test
    void htmlComStatus200SemCopiaE502() throws Exception {
        IBGE.responder(ROTA, aResponse().withStatus(200).withHeader("Content-Type", "text/html").withBody(Fixtures.texto("erro.html")));
        assertSemDetalhesInternos(assertProblema(mvc.perform(get(URL)).andReturn(), 502, "resposta-inesperada-da-fonte"));
    }

    @Test
    void copiaValidaEvitaNovaConsulta() throws Exception {
        IBGE.responderJson(ROTA, rio());
        var primeira = json(mvc.perform(get(URL)).andReturn());
        relogio.avancar(Duration.ofHours(1));
        var segunda = json(mvc.perform(get(URL)).andReturn());
        assertThat(IBGE.pedidos(ROTA)).isEqualTo(1);
        assertThat(segunda.get("meta").get("coletado_em")).isEqualTo(primeira.get("meta").get("coletado_em"));
        assertThat(segunda.get("meta").get("desatualizado").asBoolean()).isFalse();
    }

    @Test
    void copiaVencidaServidaQuandoAFonteFalha() throws Exception {
        IBGE.responderJson(ROTA, rio());
        var primeira = json(mvc.perform(get(URL)).andReturn());
        relogio.avancar(Duration.ofSeconds(86400 + 1));
        IBGE.responder(ROTA, aResponse().withFault(Fault.CONNECTION_RESET_BY_PEER));
        var r = mvc.perform(get(URL)).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        var corpo = json(r);
        assertThat(corpo.get("meta").get("desatualizado").asBoolean()).isTrue();
        assertThat(corpo.get("meta").get("coletado_em")).isEqualTo(primeira.get("meta").get("coletado_em"));
        assertThat(corpo.get("dados")).isEqualTo(primeira.get("dados"));
    }

    @Test
    void copiaVencidaRenovadaQuandoAFonteResponde() throws Exception {
        IBGE.responderJson(ROTA, rio());
        var primeira = json(mvc.perform(get(URL)).andReturn());
        relogio.avancar(Duration.ofSeconds(86400 + 1));
        var segunda = json(mvc.perform(get(URL)).andReturn());
        assertThat(IBGE.pedidos(ROTA)).isEqualTo(2);
        assertThat(segunda.get("meta").get("desatualizado").asBoolean()).isFalse();
        assertThat(segunda.get("meta").get("coletado_em").asString()).isGreaterThan(primeira.get("meta").get("coletado_em").asString());
    }

    @Test
    void falhaNumPedidoNaoAfetaOSeguinte() throws Exception {
        IBGE.responder(ROTA, aResponse().withStatus(200).withBody(rio()).withFixedDelay(1500));
        IBGE.responderFixture("/estados/53/municipios", "municipios-uf-53.json");
        assertThat(mvc.perform(get(URL)).andReturn().getResponse().getStatus()).isEqualTo(504);
        assertThat(mvc.perform(get("/v1/ufs/DF/municipios")).andReturn().getResponse().getStatus()).isEqualTo(200);
    }

    @Test
    void listasTambemUsamACopia() throws Exception {
        IBGE.responderFixture("/estados/33/municipios", "municipios-uf-33.json");
        mvc.perform(get("/v1/ufs/RJ/municipios"));
        mvc.perform(get("/v1/ufs/rj/municipios").param("pagina", "2").param("itens", "10"));
        mvc.perform(get("/v1/ufs/33/municipios"));
        assertThat(IBGE.pedidos("/estados/33/municipios")).isEqualTo(1);
    }
}

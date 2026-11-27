package io.github.danhenriquex.brasilaberto.localidades.api;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;

import io.github.danhenriquex.brasilaberto.localidades.LocalidadesApplication;
import io.github.danhenriquex.brasilaberto.localidades.operacao.FiltroCorrelacao;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.micrometer.metrics.test.autoconfigure.AutoConfigureMetrics;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.context.WebApplicationContext;

/** Mesmos casos do test_api_base.py do E1. */
@AutoConfigureMetrics
@SpringBootTest(classes = {LocalidadesApplication.class, ApiBaseTest.Falha.class})
class ApiBaseTest {

    @RestController
    static class Falha {
        @GetMapping("/v1/_falha_de_teste")
        String falhar() {
            throw new IllegalStateException("segredo interno /etc/passwd");
        }
    }

    @Autowired
    WebApplicationContext contexto;

    @Autowired
    FiltroCorrelacao filtro;

    MockMvc mvc;

    @BeforeEach
    void montar() {
        mvc = MockMvcBuilders.webAppContextSetup(contexto).addFilters(filtro).build();
    }

    @Test
    void health() throws Exception {
        MvcResult r = mvc.perform(get("/health")).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(r.getResponse().getContentAsString()).isEqualTo("{\"status\":\"ok\"}");
    }

    @ParameterizedTest
    @ValueSource(strings = {"/v2/ufs", "/ufs", "/nada", "/v1"})
    void rotaInexistenteEProblema404(String caminho) throws Exception {
        MvcResult r = mvc.perform(get(caminho)).andReturn();
        Apoio.assertProblema(r, 404, "nao-encontrado");
    }

    @Test
    void metodoNaoSuportadoTambemE404() throws Exception {
        Apoio.assertProblema(mvc.perform(post("/health")).andReturn(), 404, "nao-encontrado");
    }

    @Test
    void correlacaoValidaVoltaIgual() throws Exception {
        MvcResult r = mvc.perform(get("/health").header("X-Correlation-Id", "teste-123_a.b")).andReturn();
        assertThat(r.getResponse().getHeader("X-Correlation-Id")).isEqualTo("teste-123_a.b");
    }

    @ParameterizedTest
    @ValueSource(strings = {"com espaço", "acentuação"})
    void correlacaoInvalidaETrocada(String valor) throws Exception {
        MvcResult r = mvc.perform(get("/health").header("X-Correlation-Id", valor)).andReturn();
        assertThat(UUID.fromString(r.getResponse().getHeader("X-Correlation-Id")).version()).isEqualTo(4);
        MvcResult longo = mvc.perform(get("/health").header("X-Correlation-Id", "x".repeat(65))).andReturn();
        assertThat(UUID.fromString(longo.getResponse().getHeader("X-Correlation-Id")).version()).isEqualTo(4);
    }

    @Test
    void erroInesperadoVira500SemDetalhesInternos() throws Exception {
        MvcResult r = mvc.perform(get("/v1/_falha_de_teste")).andReturn();
        var corpo = Apoio.assertProblema(r, 500, "erro-interno");
        String texto = r.getResponse().getContentAsString();
        assertThat(texto).doesNotContain("segredo", "IllegalState", "at io.github", "Exception");
        assertThat(corpo.get("detail").asString()).isEqualTo("erro interno do serviço");
    }
}

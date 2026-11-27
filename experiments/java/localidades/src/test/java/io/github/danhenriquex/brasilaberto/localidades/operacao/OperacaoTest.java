package io.github.danhenriquex.brasilaberto.localidades.operacao;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.github.tomakehurst.wiremock.http.Fault;
import io.github.danhenriquex.brasilaberto.localidades.apoio.Fixtures;
import io.github.danhenriquex.brasilaberto.localidades.apoio.IbgeSimulado;
import io.github.danhenriquex.brasilaberto.localidades.apoio.RelogioFalso;
import java.time.Duration;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.micrometer.metrics.test.autoconfigure.AutoConfigureMetrics;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Primary;
import org.springframework.test.annotation.DirtiesContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Mesmos casos do test_api_operacao.py do E1 (US5). Contexto novo por teste: as métricas acumulam. */
@AutoConfigureMetrics
@SpringBootTest(properties = "localidades.prazo-fonte-s=0.25")
@Import(OperacaoTest.Relogio.class)
@DirtiesContext(classMode = DirtiesContext.ClassMode.AFTER_EACH_TEST_METHOD)
class OperacaoTest {

    static final IbgeSimulado IBGE = new IbgeSimulado();
    static final JsonMapper JSON = JsonMapper.builder().build();

    @DynamicPropertySource
    static void ibge(DynamicPropertyRegistry registro) {
        registro.add("localidades.ibge-url", IBGE::url);
    }

    @TestConfiguration
    static class Relogio {
        @Bean
        @Primary
        RelogioFalso relogioFalso() {
            return new RelogioFalso();
        }
    }

    @Autowired WebApplicationContext contexto;
    @Autowired FiltroCorrelacao filtro;
    @Autowired RelogioFalso relogio;

    MockMvc mvc;
    ListAppender<ILoggingEvent> linhas;
    Logger logger;

    @BeforeEach
    void montar() {
        IBGE.servidor().resetAll();
        mvc = MockMvcBuilders.webAppContextSetup(contexto).addFilters(filtro).build();
        logger = (Logger) LoggerFactory.getLogger(RegistroPedidos.LOGGER);
        linhas = new ListAppender<>();
        linhas.start();
        logger.addAppender(linhas);
    }

    @AfterEach
    void desmontar() {
        logger.detachAppender(linhas);
    }

    private static String rio() {
        for (JsonNode item : JSON.readTree(Fixtures.texto("municipios-uf-33.json"))) {
            if (item.get("id").asLong() == 3304557) return item.toString();
        }
        throw new IllegalStateException();
    }

    @Test
    void healthNaoDependeDoIbge() throws Exception {
        IBGE.servidor().stubFor(com.github.tomakehurst.wiremock.client.WireMock.any(com.github.tomakehurst.wiremock.client.WireMock.anyUrl())
                .willReturn(aResponse().withFault(Fault.CONNECTION_RESET_BY_PEER)));
        assertThat(mvc.perform(get("/health")).andReturn().getResponse().getStatus()).isEqualTo(200);
        assertThat(IBGE.pedidosTotais()).isZero();
    }

    @Test
    void metricasComOsNomesDoContrato() throws Exception {
        IBGE.responderJson("/municipios/3304557", rio());
        IBGE.responder("/municipios/3303302", aResponse().withStatus(200).withBody("[]").withFixedDelay(1000));
        mvc.perform(get("/v1/municipios/3304557")); // falta
        mvc.perform(get("/v1/municipios/3304557")); // acerto
        relogio.avancar(Duration.ofSeconds(86400 + 1));
        IBGE.responder("/municipios/3304557", aResponse().withFault(Fault.CONNECTION_RESET_BY_PEER));
        mvc.perform(get("/v1/municipios/3304557")); // desatualizado
        mvc.perform(get("/v1/municipios/3303302")); // fonte-lenta
        mvc.perform(get("/v1/municipios/12ab")); // entrada-invalida

        var r = mvc.perform(get("/metrics")).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(r.getResponse().getContentType()).startsWith("text/plain");
        String texto = r.getResponse().getContentAsString();
        assertThat(texto).contains(
                "localidades_pedidos_total{rota=\"/v1/municipios/{codigo}\",status=\"200\"} 3.0",
                "localidades_pedidos_total{rota=\"/v1/municipios/{codigo}\",status=\"504\"} 1.0",
                "localidades_erros_total{tipo=\"fonte-lenta\"} 1.0",
                "localidades_erros_total{tipo=\"entrada-invalida\"} 1.0",
                "localidades_cache_total{resultado=\"falta\"} 1.0",
                "localidades_cache_total{resultado=\"acerto\"} 1.0",
                "localidades_cache_total{resultado=\"desatualizado\"} 1.0",
                "localidades_fonte_duracao_segundos_count{recurso=\"municipio\"} 3");
        // nenhum nome ganhou sufixo de unidade do Micrometer (R8)
        assertThat(texto).doesNotContain("localidades_fonte_duracao_segundos_seconds", "localidades_fonte_duracao_seconds");
    }

    @Test
    void rotaInexistenteNaoMultiplicaSeries() throws Exception {
        for (int i = 0; i < 3; i++) {
            mvc.perform(get("/nada/" + i));
        }
        String texto = mvc.perform(get("/metrics")).andReturn().getResponse().getContentAsString();
        assertThat(texto).contains("localidades_pedidos_total{rota=\"nao-encontrado\",status=\"404\"} 3.0");
        assertThat(texto).doesNotContain("/nada/");
    }

    @Test
    void registroJsonPorPedido() throws Exception {
        IBGE.responderJson("/municipios/3304557", rio());
        mvc.perform(get("/v1/municipios/3304557").header("X-Correlation-Id", "pedido-1"));
        mvc.perform(get("/v1/municipios/3304557").header("X-Correlation-Id", "pedido-2"));
        Map<String, JsonNode> registros = new HashMap<>();
        for (ILoggingEvent evento : List.copyOf(linhas.list)) {
            JsonNode linha = JSON.readTree(evento.getFormattedMessage());
            registros.put(linha.get("correlacao_id").asString(), linha);
        }
        JsonNode primeiro = registros.get("pedido-1");
        JsonNode segundo = registros.get("pedido-2");
        assertThat(primeiro.propertyNames()).containsExactlyInAnyOrder(
                "momento", "nivel", "correlacao_id", "metodo", "rota", "status", "duracao_ms", "cache", "fonte_ms");
        assertThat(primeiro.get("metodo").asString()).isEqualTo("GET");
        assertThat(primeiro.get("rota").asString()).isEqualTo("/v1/municipios/{codigo}");
        assertThat(primeiro.get("status").asInt()).isEqualTo(200);
        assertThat(primeiro.get("nivel").asString()).isEqualTo("info");
        assertThat(primeiro.get("cache").asString()).isEqualTo("falta");
        assertThat(segundo.get("cache").asString()).isEqualTo("acerto");
        assertThat(primeiro.get("fonte_ms").isNumber()).isTrue();
        assertThat(segundo.get("fonte_ms").isNull()).isTrue();
        assertThat(primeiro.get("momento").asString()).endsWith("Z");
        assertThat(registros.values().toString()).doesNotContain("127.0.0.1", "localhost");
    }
}

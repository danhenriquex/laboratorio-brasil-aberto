package io.github.danhenriquex.brasilaberto.localidades.api;

import io.github.danhenriquex.brasilaberto.localidades.apoio.IbgeSimulado;
import io.github.danhenriquex.brasilaberto.localidades.cache.CacheComValidade;
import io.github.danhenriquex.brasilaberto.localidades.operacao.FiltroCorrelacao;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.micrometer.metrics.test.autoconfigure.AutoConfigureMetrics;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import org.springframework.web.context.WebApplicationContext;

/**
 * Base dos testes de integração: serviço inteiro (MockMvc) com o IBGE simulado pelo WireMock. O Tomcat também
 * sobe, numa porta livre, para os casos que só ele reproduz (Apoio.pedidoCru).
 */
@AutoConfigureMetrics
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
abstract class BaseApiTest {

    static final IbgeSimulado IBGE = new IbgeSimulado();

    @DynamicPropertySource
    static void apontarParaOIbgeSimulado(DynamicPropertyRegistry registro) {
        registro.add("localidades.ibge-url", IBGE::url);
    }

    @AfterAll
    static void descer() {
        // o mesmo servidor serve a todas as classes; o JVM o encerra no fim
    }

    @Autowired
    WebApplicationContext contexto;

    @Autowired
    FiltroCorrelacao filtro;

    @Autowired
    CacheComValidade cache;

    @LocalServerPort
    int porta;

    MockMvc mvc;

    @BeforeEach
    void montar() {
        IBGE.servidor().resetAll();
        cache.limpar(); // o contexto do Spring é reaproveitado entre os testes
        mvc = MockMvcBuilders.webAppContextSetup(contexto).addFilters(filtro).build();
    }
}

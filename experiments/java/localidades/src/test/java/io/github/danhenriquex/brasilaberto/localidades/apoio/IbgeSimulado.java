package io.github.danhenriquex.brasilaberto.localidades.apoio;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static com.github.tomakehurst.wiremock.client.WireMock.get;
import static com.github.tomakehurst.wiremock.client.WireMock.urlPathEqualTo;
import static com.github.tomakehurst.wiremock.core.WireMockConfiguration.options;

import com.github.tomakehurst.wiremock.WireMockServer;
import com.github.tomakehurst.wiremock.client.ResponseDefinitionBuilder;

/** IBGE simulado com WireMock em 127.0.0.1, porta aleatória (equivalente ao respx do E1). */
public final class IbgeSimulado implements AutoCloseable {

    public static final String PREFIXO = "/api/v1/localidades";

    private final WireMockServer servidor;

    public IbgeSimulado() {
        servidor = new WireMockServer(options().dynamicPort().bindAddress("127.0.0.1"));
        servidor.start();
    }

    public String url() {
        return "http://127.0.0.1:" + servidor.port() + PREFIXO;
    }

    public WireMockServer servidor() {
        return servidor;
    }

    public void responder(String caminho, ResponseDefinitionBuilder resposta) {
        servidor.stubFor(get(urlPathEqualTo(PREFIXO + caminho)).willReturn(resposta));
    }

    public void responderJson(String caminho, String corpo) {
        responder(caminho, aResponse().withStatus(200).withHeader("Content-Type", "application/json; charset=utf-8").withBody(corpo));
    }

    public void responderFixture(String caminho, String fixture) {
        responderJson(caminho, Fixtures.texto(fixture));
    }

    public int pedidos(String caminho) {
        return servidor.findAll(com.github.tomakehurst.wiremock.client.WireMock.getRequestedFor(urlPathEqualTo(PREFIXO + caminho))).size();
    }

    public int pedidosTotais() {
        return servidor.getAllServeEvents().size();
    }

    @Override
    public void close() {
        servidor.stop();
    }
}

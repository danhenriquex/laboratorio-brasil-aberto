package io.github.danhenriquex.brasilaberto.localidades.api;

import static io.github.danhenriquex.brasilaberto.localidades.api.Apoio.assertMeta;
import static io.github.danhenriquex.brasilaberto.localidades.api.Apoio.assertProblema;
import static io.github.danhenriquex.brasilaberto.localidades.api.Apoio.json;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import io.github.danhenriquex.brasilaberto.localidades.apoio.Fixtures;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Dobra;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.node.ArrayNode;

/** Mesmos casos do test_api_ufs.py do E1 (US1). */
class ApiUfsTest extends BaseApiTest {

    private void estados() {
        IBGE.responderFixture("/estados", "estados.json");
    }

    private void rj() {
        IBGE.responderFixture("/estados/33/municipios", "municipios-uf-33.json");
    }

    private static List<String> nomes(JsonNode dados) {
        List<String> nomes = new ArrayList<>();
        dados.forEach(d -> nomes.add(d.get("nome").asString()));
        return nomes;
    }

    @Test
    void listaAs27UfsOrdenadas() throws Exception {
        estados();
        var r = mvc.perform(get("/v1/ufs")).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(r.getResponse().getContentType()).startsWith("application/json");
        JsonNode corpo = json(r);
        assertThat(corpo.propertyNames()).containsExactlyInAnyOrder("dados", "meta");
        JsonNode ufs = corpo.get("dados");
        assertThat(ufs).hasSize(27);
        assertThat(ufs.get(0).get("sigla").asString()).isEqualTo("AC");
        var dobrados = nomes(ufs).stream().map(Dobra::dobrar).toList();
        assertThat(dobrados).isSorted();
        JsonNode rj = null;
        for (JsonNode u : ufs) if (u.get("sigla").asString().equals("RJ")) rj = u;
        assertThat(rj.toString()).isEqualTo("{\"codigo\":\"33\",\"sigla\":\"RJ\",\"nome\":\"Rio de Janeiro\",\"regiao\":{\"codigo\":\"3\",\"sigla\":\"SE\",\"nome\":\"Sudeste\"}}");
        assertMeta(corpo.get("meta"), IBGE.url() + "/estados", false);
        assertThat(IBGE.pedidos("/estados")).isEqualTo(1);
    }

    @ParameterizedTest
    @ValueSource(strings = {"rj", "RJ", "33", "%20RJ%20"})
    void obterUf(String param) throws Exception {
        estados();
        // URI pronta: get(String) trata o texto como template e codificaria o "%" de novo
        var r = mvc.perform(get(java.net.URI.create("/v1/ufs/" + param))).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(json(r).get("dados").get("sigla").asString()).isEqualTo("RJ");
        assertMeta(json(r).get("meta"), IBGE.url() + "/estados", false);
    }

    @ParameterizedTest
    @ValueSource(strings = {"XX", "99"})
    void ufInexistenteE404SemConsultar(String param) throws Exception {
        assertProblema(mvc.perform(get("/v1/ufs/" + param)).andReturn(), 404, "nao-encontrado");
        assertThat(IBGE.pedidosTotais()).isZero();
    }

    @ParameterizedTest
    @ValueSource(strings = {"R1", "123", "R"})
    void ufMalFormadaE400SemConsultar(String param) throws Exception {
        assertProblema(mvc.perform(get("/v1/ufs/" + param)).andReturn(), 400, "entrada-invalida");
        assertThat(IBGE.pedidosTotais()).isZero();
    }

    @Test
    void ufDaTabelaAusenteNoIbgeEInesperada() throws Exception {
        ArrayNode estados = (ArrayNode) Apoio.JSON.readTree(Fixtures.texto("estados.json"));
        ArrayNode semRj = Apoio.JSON.createArrayNode();
        estados.forEach(u -> { if (!u.get("sigla").asString().equals("RJ")) semRj.add(u); });
        IBGE.responderJson("/estados", semRj.toString());
        assertProblema(mvc.perform(get("/v1/ufs/RJ")).andReturn(), 502, "resposta-inesperada-da-fonte");
    }

    @Test
    void municipiosDoRj() throws Exception {
        rj();
        var r = mvc.perform(get("/v1/ufs/RJ/municipios")).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        JsonNode corpo = json(r);
        assertThat(corpo.propertyNames()).containsExactlyInAnyOrder("dados", "paginacao", "meta");
        assertThat(corpo.get("paginacao").toString()).isEqualTo("{\"pagina\":1,\"itens\":100,\"total\":92,\"paginas\":1}");
        JsonNode dados = corpo.get("dados");
        assertThat(dados).hasSize(92);
        dados.forEach(m -> assertThat(m.propertyNames()).containsExactlyInAnyOrder("codigo", "nome"));
        assertThat(dados.get(0).toString()).isEqualTo("{\"codigo\":\"3300100\",\"nome\":\"Angra dos Reis\"}");
        assertThat(dados.toString()).contains("{\"codigo\":\"3303302\",\"nome\":\"Niterói\"}");
        assertThat(nomes(dados).stream().map(Dobra::dobrar).toList()).isSorted();
        assertMeta(corpo.get("meta"), IBGE.url() + "/estados/33/municipios", false);
        assertThat(IBGE.pedidos("/estados/33/municipios")).isEqualTo(1);
        assertThat(IBGE.pedidos("/estados")).isZero(); // uma consulta por pedido (FR-017)
    }

    @Test
    void paginacao() throws Exception {
        rj();
        var corpo = json(mvc.perform(get("/v1/ufs/rj/municipios").param("itens", "10").param("pagina", "10")).andReturn());
        assertThat(corpo.get("paginacao").toString()).isEqualTo("{\"pagina\":10,\"itens\":10,\"total\":92,\"paginas\":10}");
        assertThat(corpo.get("dados")).hasSize(2);
    }

    @Test
    void paginaAlemDoFim() throws Exception {
        rj();
        var r = mvc.perform(get("/v1/ufs/33/municipios").param("pagina", "20")).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(json(r).get("dados")).isEmpty();
        assertThat(json(r).get("paginacao").get("total").asInt()).isEqualTo(92);
    }

    @ParameterizedTest
    @CsvSource({"itens,0,500", "itens,501,500", "pagina,0,pagina", "itens,dez,itens"})
    void paginacaoInvalidaE400SemConsultar(String parametro, String valor, String trecho) throws Exception {
        var corpo = assertProblema(mvc.perform(get("/v1/ufs/RJ/municipios").param(parametro, valor)).andReturn(), 400, "entrada-invalida");
        assertThat(corpo.get("detail").asString()).contains(trecho);
        assertThat(IBGE.pedidosTotais()).isZero();
    }

    @Test
    void listaVaziaParaUfExistenteEInesperada() throws Exception {
        IBGE.responderJson("/estados/33/municipios", "[]");
        assertProblema(mvc.perform(get("/v1/ufs/RJ/municipios")).andReturn(), 502, "resposta-inesperada-da-fonte");
    }

    @Test
    void dfTemUmMunicipio() throws Exception {
        IBGE.responderFixture("/estados/53/municipios", "municipios-uf-53.json");
        var corpo = json(mvc.perform(get("/v1/ufs/DF/municipios")).andReturn());
        assertThat(corpo.get("dados").toString()).isEqualTo("[{\"codigo\":\"5300108\",\"nome\":\"Brasília\"}]");
        assertThat(corpo.get("paginacao").get("paginas").asInt()).isEqualTo(1);
    }

    // --- Convergência do E4 (T045): leitura de pagina e itens como no E1 ---

    @Test
    void paginaMuitoGrandeEPaginaAlemDoFim() throws Exception {
        rj();
        var r = mvc.perform(get("/v1/ufs/RJ/municipios").param("pagina", "99999999999")).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(json(r).get("dados")).isEmpty();
        assertThat(json(r).get("paginacao").toString()).isEqualTo("{\"pagina\":99999999999,\"itens\":100,\"total\":92,\"paginas\":1}");
    }

    @Test
    void parametroRepetidoValeOUltimo() throws Exception {
        rj();
        var r = mvc.perform(get("/v1/ufs/RJ/municipios").param("itens", "10", "20")).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(json(r).get("paginacao").get("itens").asInt()).isEqualTo(20);
        assertThat(json(r).get("dados")).hasSize(20);
    }

    @Test
    void itensMuitoGrandeContinuaForaDoLimite() throws Exception {
        var corpo = assertProblema(mvc.perform(get("/v1/ufs/RJ/municipios").param("itens", "99999999999")).andReturn(), 400, "entrada-invalida");
        assertThat(corpo.get("detail").asString()).contains("500");
    }

    /** T048: com qualquer Accept, a lista sai em application/json, como no E1. */
    @ParameterizedTest
    @ValueSource(strings = {"application/xml", "text/html", "text/plain", "application/problem+json"})
    void acceptNaoMudaOFormato(String aceita) throws Exception {
        estados();
        var r = mvc.perform(get("/v1/ufs").header("Accept", aceita)).andReturn();
        assertThat(r.getResponse().getStatus()).as(r.getResponse().getContentAsString()).isEqualTo(200);
        assertThat(r.getResponse().getContentType()).startsWith("application/json");
        assertThat(json(r).get("dados")).hasSize(27);
    }

    /** T050: "/v1/ufs;jsessionid=x" e "/v1/ufs/RJ;x=1/municipios" não devolvem dados nem consultam o IBGE. */
    @ParameterizedTest
    @ValueSource(strings = {"/v1/ufs;jsessionid=x", "/v1/ufs/RJ;x=1/municipios", "/v1/ufs/RJ/municipios;x"})
    void parametroDeCaminhoNaoCasaComARota(String caminho) throws Exception {
        IBGE.servidor().resetAll();
        var r = Apoio.pedidoCru(porta, "GET", caminho, "X-Correlation-Id: pv-456");
        assertThat(r.status()).as(r.corpo()).isEqualTo(404);
        assertThat(r.cabecalho("Content-Type")).startsWith("application/problem+json");
        assertThat(r.json().get("correlacao_id").asString()).isEqualTo("pv-456");
        assertThat(IBGE.pedidosTotais()).isZero();
    }
}

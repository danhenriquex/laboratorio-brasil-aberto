package io.github.danhenriquex.brasilaberto.localidades.fonte;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static com.github.tomakehurst.wiremock.client.WireMock.getRequestedFor;
import static com.github.tomakehurst.wiremock.client.WireMock.urlPathEqualTo;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.danhenriquex.brasilaberto.localidades.apoio.Fixtures;
import io.github.danhenriquex.brasilaberto.localidades.apoio.IbgeSimulado;
import io.github.danhenriquex.brasilaberto.localidades.config.Configuracao;
import io.github.danhenriquex.brasilaberto.localidades.dominio.MunicipioResumido;
import io.github.danhenriquex.brasilaberto.localidades.erros.FonteIndisponivel;
import io.github.danhenriquex.brasilaberto.localidades.erros.FonteLenta;
import io.github.danhenriquex.brasilaberto.localidades.erros.NaoEncontrado;
import io.github.danhenriquex.brasilaberto.localidades.erros.RespostaInesperadaDaFonte;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

/** Mesmos casos do test_fonte_ibge.py do E1, incluindo T048 e T049. */
class ClienteIbgeTest {

    private static final JsonMapper JSON = JsonMapper.builder().build();

    private IbgeSimulado ibge;
    private final List<String> medidas = new ArrayList<>();

    @BeforeEach
    void subir() {
        ibge = new IbgeSimulado();
    }

    @AfterEach
    void descer() {
        ibge.close();
    }

    private ClienteIbge cliente(double prazo) {
        return new ClienteIbge(new Configuracao(ibge.url(), prazo, 86400, 500), (recurso, s) -> medidas.add(recurso));
    }

    private ClienteIbge cliente() {
        return cliente(10);
    }

    private static ObjectNode itemDaUf(String uf, long codigo) {
        ArrayNode lista = (ArrayNode) JSON.readTree(Fixtures.texto("municipios-uf-" + uf + ".json"));
        for (var item : lista) {
            if (item.get("id").asLong() == codigo) {
                return (ObjectNode) item.deepCopy();
            }
        }
        throw new IllegalArgumentException("sem " + codigo);
    }

    // --- normalização ---

    @Test
    void estadosNormalizados() {
        ibge.responderFixture("/estados", "estados.json");
        var r = cliente().obterEstados();
        assertThat(r.dados()).hasSize(27);
        var rj = r.dados().stream().filter(u -> u.sigla().equals("RJ")).findFirst().orElseThrow();
        assertThat(rj.codigo()).isEqualTo("33");
        assertThat(rj.nome()).isEqualTo("Rio de Janeiro");
        assertThat(rj.regiao().codigo()).isEqualTo("3");
        assertThat(rj.regiao().sigla()).isEqualTo("SE");
        assertThat(r.urlFonte()).isEqualTo(ibge.url() + "/estados");
        assertThat(ibge.pedidos("/estados")).isEqualTo(1);
        ibge.servidor().verify(getRequestedFor(urlPathEqualTo(IbgeSimulado.PREFIXO + "/estados"))
                .withHeader("User-Agent", com.github.tomakehurst.wiremock.client.WireMock.equalTo(ClienteIbge.USER_AGENT)));
        assertThat(medidas).containsExactly("estados");
    }

    @Test
    void municipiosDaUf() {
        ibge.responderFixture("/estados/33/municipios", "municipios-uf-33.json");
        var r = cliente().obterMunicipiosDaUf("33");
        assertThat(r.dados()).hasSize(92).contains(new MunicipioResumido("3303302", "Niterói"));
        assertThat(r.urlFonte()).isEqualTo(ibge.url() + "/estados/33/municipios");
    }

    @Test
    void municipiosDaUfVaziaEInesperada() {
        ibge.responderJson("/estados/33/municipios", "[]");
        assertThatThrownBy(() -> cliente().obterMunicipiosDaUf("33")).isInstanceOf(RespostaInesperadaDaFonte.class);
    }

    @Test
    void municipioObjetoOuListaDeUm() {
        var item = itemDaUf("33", 3304557);
        for (String corpo : List.of(item.toString(), "[" + item + "]")) {
            ibge.servidor().resetAll();
            ibge.responderJson("/municipios/3304557", corpo);
            var r = cliente().obterMunicipio("3304557");
            assertThat(r.dados().codigo()).isEqualTo("3304557");
            assertThat(r.dados().nome()).isEqualTo("Rio de Janeiro");
            assertThat(r.dados().uf().sigla()).isEqualTo("RJ");
            assertThat(r.dados().uf().codigo()).isEqualTo("33");
            assertThat(r.dados().regiaoImediata().codigo()).isEqualTo("330001");
            assertThat(r.dados().regiaoIntermediaria().codigo()).isEqualTo("3301");
        }
    }

    @Test
    void municipioVazioENaoEncontrado() {
        ibge.responderJson("/municipios/9999999", "[]");
        assertThatThrownBy(() -> cliente().obterMunicipio("9999999")).isInstanceOf(NaoEncontrado.class);
    }

    @Test
    void municipioSemMicrorregiaoEAceito() {
        ibge.responderFixture("/municipios/5101837", "municipio-5101837.json");
        assertThat(cliente().obterMunicipio("5101837").dados().uf().sigla()).isEqualTo("MT");
    }

    @Test
    void listaComDoisMunicipiosEInesperada() {
        var item = itemDaUf("33", 3304557);
        ibge.responderJson("/municipios/3304557", "[" + item + "," + item + "]");
        assertThatThrownBy(() -> cliente().obterMunicipio("3304557")).isInstanceOf(RespostaInesperadaDaFonte.class);
    }

    @Test
    void municipioSemRegiaoImediataEInesperado() {
        ibge.responderFixture("/municipios/3304557", "municipio-sem-regiao-imediata.json");
        assertThatThrownBy(() -> cliente().obterMunicipio("3304557")).isInstanceOf(RespostaInesperadaDaFonte.class);
    }

    // --- classificação (R6 do E1) ---

    @Test
    void conexaoRecusadaEIndisponivel() {
        String url = ibge.url();
        ibge.close();
        var c = new ClienteIbge(new Configuracao(url, 2, 86400, 500), (r, s) -> {});
        assertThatThrownBy(c::obterEstados).isInstanceOf(FonteIndisponivel.class);
        ibge = new IbgeSimulado();
    }

    @Test
    void status503e429SaoIndisponibilidade() {
        for (int status : new int[] {503, 429}) {
            ibge.servidor().resetAll();
            ibge.responder("/estados", aResponse().withStatus(status));
            assertThatThrownBy(() -> cliente().obterEstados()).isInstanceOf(FonteIndisponivel.class);
            assertThat(ibge.pedidos("/estados")).isEqualTo(1);
        }
    }

    @Test
    void prazoTotalEsgotadoEFonteLenta() {
        ibge.responder("/estados", aResponse().withStatus(200).withBody("[]").withFixedDelay(600));
        long inicio = System.nanoTime();
        assertThatThrownBy(() -> cliente(0.1).obterEstados()).isInstanceOf(FonteLenta.class);
        assertThat((System.nanoTime() - inicio) / 1_000_000).isLessThan(500);
    }

    @Test
    void status404EInesperado() {
        ibge.responder("/estados", aResponse().withStatus(404));
        assertThatThrownBy(() -> cliente().obterEstados()).isInstanceOf(RespostaInesperadaDaFonte.class);
    }

    @Test
    void htmlComStatus200EInesperadoSemRepassarOCorpo() {
        ibge.responder("/estados", aResponse().withStatus(200).withHeader("Content-Type", "text/html").withBody(Fixtures.texto("erro.html")));
        assertThatThrownBy(() -> cliente().obterEstados())
                .isInstanceOf(RespostaInesperadaDaFonte.class)
                .satisfies(e -> assertThat(e.getMessage()).doesNotContainIgnoringCase("<html"));
    }

    @Test
    void jsonSemCampoObrigatorioEInesperado() {
        ibge.responderFixture("/estados", "estados-sem-regiao.json");
        assertThatThrownBy(() -> cliente().obterEstados()).isInstanceOf(RespostaInesperadaDaFonte.class);
        ibge.responderJson("/estados", "{\"nao\": \"e lista\"}");
        assertThatThrownBy(() -> cliente().obterEstados()).isInstanceOf(RespostaInesperadaDaFonte.class);
    }

    // --- formato exato (T048 e T049 do E1) ---

    @Test
    void municipioDaListaComIdCurtoEInesperado() {
        ibge.responderJson("/estados/33/municipios", "[{\"id\": 33045, \"nome\": \"Curto\"}]");
        assertThatThrownBy(() -> cliente().obterMunicipiosDaUf("33")).isInstanceOf(RespostaInesperadaDaFonte.class).hasMessageContaining("7 dígitos");
    }

    @Test
    void ufComIdDeUmDigitoEInesperada() {
        ArrayNode estados = (ArrayNode) JSON.readTree(Fixtures.texto("estados.json"));
        ((ObjectNode) estados.get(0)).put("id", 1);
        ibge.responderJson("/estados", estados.toString());
        assertThatThrownBy(() -> cliente().obterEstados()).isInstanceOf(RespostaInesperadaDaFonte.class).hasMessageContaining("2 dígitos");
    }

    @Test
    void regiaoImediataComIdCurtoEInesperada() {
        var item = itemDaUf("33", 3304557);
        ((ObjectNode) item.get("regiao-imediata")).put("id", 33001);
        ibge.responderJson("/municipios/3304557", item.toString());
        assertThatThrownBy(() -> cliente().obterMunicipio("3304557")).isInstanceOf(RespostaInesperadaDaFonte.class).hasMessageContaining("6 dígitos");
    }

    @Test
    void siglasForaDoFormatoSaoInesperadas() {
        ArrayNode estados = (ArrayNode) JSON.readTree(Fixtures.texto("estados.json"));
        ((ObjectNode) estados.get(0)).put("sigla", "ro");
        ibge.responderJson("/estados", estados.toString());
        assertThatThrownBy(() -> cliente().obterEstados()).isInstanceOf(RespostaInesperadaDaFonte.class).hasMessageContaining("sigla");

        estados = (ArrayNode) JSON.readTree(Fixtures.texto("estados.json"));
        ((ObjectNode) estados.get(0).get("regiao")).put("sigla", "Norte");
        ibge.responderJson("/estados", estados.toString());
        assertThatThrownBy(() -> cliente().obterEstados()).isInstanceOf(RespostaInesperadaDaFonte.class).hasMessageContaining("sigla");

        var item = itemDaUf("33", 3304557);
        ((ObjectNode) item.get("regiao-imediata").get("regiao-intermediaria").get("UF")).put("sigla", "R J");
        ibge.responderJson("/municipios/3304557", item.toString());
        assertThatThrownBy(() -> cliente().obterMunicipio("3304557")).isInstanceOf(RespostaInesperadaDaFonte.class).hasMessageContaining("sigla");
    }
}

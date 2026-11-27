package io.github.danhenriquex.brasilaberto.localidades.api;

import static io.github.danhenriquex.brasilaberto.localidades.api.Apoio.assertProblema;
import static io.github.danhenriquex.brasilaberto.localidades.api.Apoio.json;
import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;

import io.github.danhenriquex.brasilaberto.localidades.apoio.Fixtures;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Dobra;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;
import tools.jackson.databind.JsonNode;

/** Mesmos casos do test_api_busca.py do E1 (US4). */
class ApiBuscaTest extends BaseApiTest {

    @BeforeEach
    void rj() {
        IBGE.responderFixture("/estados/33/municipios", "municipios-uf-33.json");
    }

    private static List<String> nomes(JsonNode dados) {
        List<String> nomes = new ArrayList<>();
        dados.forEach(d -> nomes.add(d.get("nome").asString()));
        return nomes;
    }

    @ParameterizedTest
    @ValueSource(strings = {"niteroi", "NITERÓI", "  Niterói  "})
    void buscaSemAcentoESemCaixa(String termo) throws Exception {
        var r = mvc.perform(get("/v1/ufs/RJ/municipios").param("nome", termo)).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        var corpo = json(r);
        assertThat(corpo.get("dados").toString()).isEqualTo("[{\"codigo\":\"3303302\",\"nome\":\"Niterói\"}]");
        assertThat(corpo.get("paginacao").toString()).isEqualTo("{\"pagina\":1,\"itens\":100,\"total\":1,\"paginas\":1}");
    }

    @Test
    void buscaComVariosResultados() throws Exception {
        List<String> esperados = new ArrayList<>();
        Apoio.JSON.readTree(Fixtures.texto("municipios-uf-33.json")).forEach(m -> {
            if (Dobra.dobrar(m.get("nome").asString()).contains("sao")) esperados.add(m.get("nome").asString() + "|" + m.get("id").asString());
        });
        esperados.sort(Comparator.comparing((String s) -> Dobra.dobrar(s.split("\\|")[0])).thenComparing(s -> s.split("\\|")[1]));
        List<String> nomesEsperados = esperados.stream().map(s -> s.split("\\|")[0]).toList();

        var corpo = json(mvc.perform(get("/v1/ufs/RJ/municipios").param("nome", "são").param("itens", "5")).andReturn());
        assertThat(corpo.get("paginacao").get("total").asInt()).isEqualTo(nomesEsperados.size()).isGreaterThan(5);
        assertThat(nomes(corpo.get("dados"))).isEqualTo(nomesEsperados.subList(0, 5));
        var pagina2 = json(mvc.perform(get("/v1/ufs/RJ/municipios").param("nome", "são").param("itens", "5").param("pagina", "2")).andReturn());
        assertThat(nomes(pagina2.get("dados"))).isEqualTo(nomesEsperados.subList(5, Math.min(10, nomesEsperados.size())));
    }

    @Test
    void buscaSemResultado() throws Exception {
        var r = mvc.perform(get("/v1/ufs/RJ/municipios").param("nome", "xyzw")).andReturn();
        assertThat(r.getResponse().getStatus()).isEqualTo(200);
        assertThat(json(r).get("dados")).isEmpty();
        assertThat(json(r).get("paginacao").toString()).isEqualTo("{\"pagina\":1,\"itens\":100,\"total\":0,\"paginas\":0}");
    }

    @ParameterizedTest
    @CsvSource(delimiter = '|', value = {"a|2", "'  a  '|2", "''|2"})
    void buscaInvalidaE400SemConsultar(String termo, String trecho) throws Exception {
        IBGE.servidor().resetAll();
        var corpo = assertProblema(mvc.perform(get("/v1/ufs/RJ/municipios").param("nome", termo)).andReturn(), 400, "entrada-invalida");
        assertThat(corpo.get("detail").asString()).contains(trecho);
        assertThat(IBGE.pedidosTotais()).isZero();
    }

    @Test
    void buscaLongaDemaisE400() throws Exception {
        var corpo = assertProblema(mvc.perform(get("/v1/ufs/RJ/municipios").param("nome", "x".repeat(61))).andReturn(), 400, "entrada-invalida");
        assertThat(corpo.get("detail").asString()).contains("60");
    }

    @Test
    void duasBuscasUmaConsulta() throws Exception {
        mvc.perform(get("/v1/ufs/RJ/municipios").param("nome", "niteroi"));
        mvc.perform(get("/v1/ufs/RJ/municipios").param("nome", "são"));
        assertThat(IBGE.pedidos("/estados/33/municipios")).isEqualTo(1);
    }
}

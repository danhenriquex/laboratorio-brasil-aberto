package io.github.danhenriquex.brasilaberto.localidades.dominio;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.danhenriquex.brasilaberto.localidades.erros.EntradaInvalida;
import io.github.danhenriquex.brasilaberto.localidades.erros.NaoEncontrado;
import java.util.List;
import java.util.stream.IntStream;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

/** Mesmos casos do test_dominio.py do E1. */
class DominioTest {

    private static MunicipioResumido m(String codigo, String nome) {
        return new MunicipioResumido(codigo, nome);
    }

    @ParameterizedTest
    @CsvSource(delimiter = '|', value = {"Niterói|niteroi", "SÃO|sao", "Santa Bárbara d'Oeste|santa barbara d'oeste", "Açu|acu"})
    void dobrar(String entrada, String esperado) {
        assertThat(Dobra.dobrar(entrada)).isEqualTo(esperado);
    }

    @Test
    void ufsOficiais() {
        assertThat(UfsOficiais.CODIGO_PARA_SIGLA).hasSize(27).containsEntry("33", "RJ").containsEntry("53", "DF");
        assertThat(UfsOficiais.CODIGO_PARA_SIGLA.values()).doesNotHaveDuplicates();
    }

    @Test
    void ordenarIgnoraAcentoECaixaEDesempataPeloCodigo() {
        var itens = List.of(m("3300001", "Óbidos"), m("3300003", "abc"), m("3300002", "Abc"), m("3300004", "Niterói"));
        assertThat(Dobra.ordenar(itens)).extracting(MunicipioResumido::codigo)
                .containsExactly("3300002", "3300003", "3300004", "3300001");
    }

    @Test
    void filtrarPorNome() {
        var itens = List.of(m("1", "São Gonçalo"), m("2", "Niterói"), m("3", "Paraíso"));
        assertThat(Dobra.filtrarPorNome(itens, "  SAO ")).extracting(MunicipioResumido::codigo).containsExactly("1");
        assertThat(Dobra.filtrarPorNome(itens, "ni")).extracting(MunicipioResumido::codigo).containsExactly("2");
        assertThat(Dobra.filtrarPorNome(itens, "zzz")).isEmpty();
    }

    @Test
    void paginar() {
        var itens = IntStream.range(0, 7).mapToObj(i -> m(String.valueOf(i), "n" + i)).toList();
        var p = Pagina.paginar(itens, 2, 3);
        assertThat(p.itens()).extracting(MunicipioResumido::codigo).containsExactly("3", "4", "5");
        assertThat(p.paginacao()).isEqualTo(new Paginacao(2, 3, 7, 3));
        assertThat(Pagina.paginar(itens, 3, 3).itens()).extracting(MunicipioResumido::codigo).containsExactly("6");
        var alem = Pagina.paginar(itens, 10, 3);
        assertThat(alem.itens()).isEmpty();
        assertThat(alem.paginacao()).isEqualTo(new Paginacao(10, 3, 7, 3));
        assertThat(Pagina.paginar(List.<MunicipioResumido>of(), 1, 100).paginacao()).isEqualTo(new Paginacao(1, 100, 0, 0));
    }

    @ParameterizedTest
    @CsvSource({"' rj ',33", "RJ,33", "33,33", "df,53", "' 35',35"})
    void resolverUf(String entrada, String codigo) {
        assertThat(Validacao.resolverUf(entrada)).isEqualTo(codigo);
    }

    @ParameterizedTest
    @ValueSource(strings = {"XX", "99", "zz", "10"})
    void ufInexistente(String entrada) {
        assertThatThrownBy(() -> Validacao.resolverUf(entrada)).isInstanceOf(NaoEncontrado.class);
    }

    @ParameterizedTest
    @ValueSource(strings = {"R1", "123", "", "   ", "R", "RJX", "3"})
    void ufMalFormada(String entrada) {
        assertThatThrownBy(() -> Validacao.resolverUf(entrada)).isInstanceOf(EntradaInvalida.class);
    }

    @ParameterizedTest
    @ValueSource(strings = {"3304557", "5300108"})
    void codigoMunicipioValido(String codigo) {
        assertThat(Validacao.validarCodigoMunicipio(codigo)).isEqualTo(codigo);
    }

    @ParameterizedTest
    @ValueSource(strings = {"12ab", "123456", "12345678", "", "330455７"})
    void codigoMunicipioInvalido(String codigo) {
        assertThatThrownBy(() -> Validacao.validarCodigoMunicipio(codigo)).isInstanceOf(EntradaInvalida.class);
    }

    @Test
    void validarPaginacao() {
        Validacao.validarPaginacao(1, 1, 500);
        Validacao.validarPaginacao(3, 500, 500);
        assertThatThrownBy(() -> Validacao.validarPaginacao(1, 501, 500)).isInstanceOf(EntradaInvalida.class).hasMessageContaining("500");
        assertThatThrownBy(() -> Validacao.validarPaginacao(1, 0, 500)).isInstanceOf(EntradaInvalida.class).hasMessageContaining("500");
        assertThatThrownBy(() -> Validacao.validarPaginacao(0, 10, 500)).isInstanceOf(EntradaInvalida.class).hasMessageContaining("pagina");
    }

    @Test
    void validarNome() {
        assertThat(Validacao.validarNome("  niteroi ")).isEqualTo("niteroi");
        assertThat(Validacao.validarNome("sã")).isEqualTo("sã");
        assertThatThrownBy(() -> Validacao.validarNome(" a ")).isInstanceOf(EntradaInvalida.class).hasMessageContaining("2");
        assertThatThrownBy(() -> Validacao.validarNome("x".repeat(61))).isInstanceOf(EntradaInvalida.class).hasMessageContaining("60");
    }
}

package io.github.danhenriquex.brasilaberto.localidades.servico;

import io.github.danhenriquex.brasilaberto.localidades.cache.CacheComValidade;
import io.github.danhenriquex.brasilaberto.localidades.config.Configuracao;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Dobra;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Meta;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Municipio;
import io.github.danhenriquex.brasilaberto.localidades.dominio.MunicipioResumido;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Pagina;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Uf;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Validacao;
import io.github.danhenriquex.brasilaberto.localidades.erros.RespostaInesperadaDaFonte;
import io.github.danhenriquex.brasilaberto.localidades.fonte.ClienteIbge;
import io.github.danhenriquex.brasilaberto.localidades.fonte.RespostaFonte;
import java.time.Clock;
import java.util.List;
import java.util.function.Supplier;

/** Casos de uso do serviço de localidades. Não depende do Spring Web (portas e adaptadores, como no E1). */
public class ServicoLocalidades {

    protected final ClienteIbge ibge;
    protected final Clock relogio;
    protected final Configuracao config;
    protected final CacheComValidade cache;

    public ServicoLocalidades(ClienteIbge ibge, Clock relogio, Configuracao config, CacheComValidade cache) {
        this.ibge = ibge;
        this.relogio = relogio;
        this.config = config;
        this.cache = cache;
    }

    /** Toda consulta passa pela cópia guardada; o meta vem da entrada (coletado_em original e desatualizado). */
    protected <T> Obtido<T> obter(String chave, Supplier<RespostaFonte<T>> buscar) {
        CacheComValidade.Entrada<T> entrada = cache.obter(chave, buscar);
        return new Obtido<>(entrada.dados(), Meta.de(entrada.urlFonte(), entrada.coletadoEm(), entrada.desatualizado()),
                entrada.resultado());
    }

    // --- US1 ---

    public Resultado<List<Uf>> listarUfs() {
        Obtido<List<Uf>> obtido = obter("estados", ibge::obterEstados);
        return new Resultado<>(Dobra.ordenar(obtido.dados(), Uf::nome, Uf::codigo), null, obtido.meta(), obtido.cache());
    }

    public Resultado<Uf> obterUf(String param) {
        String codigo = Validacao.resolverUf(param);
        Obtido<List<Uf>> obtido = obter("estados", ibge::obterEstados);
        Uf uf = obtido.dados().stream()
                .filter(u -> u.codigo().equals(codigo))
                .findFirst()
                .orElseThrow(() -> new RespostaInesperadaDaFonte("a UF " + codigo + " não veio na lista de UFs do IBGE"));
        return new Resultado<>(uf, null, obtido.meta(), obtido.cache());
    }

    public Resultado<List<MunicipioResumido>> listarMunicipios(String paramUf, long pagina, long itens) {
        return listarMunicipios(paramUf, pagina, itens, null);
    }

    /** US4: com nome, filtra sem acento nem caixa sobre a cópia da UF, antes de ordenar e paginar. */
    public Resultado<List<MunicipioResumido>> listarMunicipios(String paramUf, long pagina, long itens, String nome) {
        Validacao.validarPaginacao(pagina, itens, config.itensMax());
        String filtro = nome == null ? null : Validacao.validarNome(nome);
        String codigo = Validacao.resolverUf(paramUf);
        Obtido<List<MunicipioResumido>> obtido =
                obter("estados/" + codigo + "/municipios", () -> ibge.obterMunicipiosDaUf(codigo));
        List<MunicipioResumido> selecionados =
                filtro == null ? obtido.dados() : Dobra.filtrarPorNome(obtido.dados(), filtro);
        Pagina<MunicipioResumido> fatia = Pagina.paginar(Dobra.ordenar(selecionados), pagina, (int) itens);
        return new Resultado<>(fatia.itens(), fatia.paginacao(), obtido.meta(), obtido.cache());
    }

    // --- US2 ---

    public Resultado<Municipio> obterMunicipio(String codigo) {
        String valido = Validacao.validarCodigoMunicipio(codigo);
        Obtido<Municipio> obtido = obter("municipios/" + valido, () -> ibge.obterMunicipio(valido));
        return new Resultado<>(obtido.dados(), null, obtido.meta(), obtido.cache());
    }
}

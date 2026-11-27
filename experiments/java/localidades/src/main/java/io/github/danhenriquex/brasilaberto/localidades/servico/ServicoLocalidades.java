package io.github.danhenriquex.brasilaberto.localidades.servico;

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
import java.time.Instant;
import java.util.List;
import java.util.function.Supplier;

/** Casos de uso do serviço de localidades. Não depende do Spring Web (portas e adaptadores, como no E1). */
public class ServicoLocalidades {

    protected final ClienteIbge ibge;
    protected final Clock relogio;
    protected final Configuracao config;

    public ServicoLocalidades(ClienteIbge ibge, Clock relogio, Configuracao config) {
        this.ibge = ibge;
        this.relogio = relogio;
        this.config = config;
    }

    /** Nesta fase consulta a fonte direto; a cópia guardada entra na US3 (T028). */
    protected <T> Obtido<T> obter(String chave, Supplier<RespostaFonte<T>> buscar) {
        Instant coletadoEm = relogio.instant();
        RespostaFonte<T> resposta = buscar.get();
        return new Obtido<>(resposta.dados(), Meta.de(resposta.urlFonte(), coletadoEm, false), "falta");
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

    public Resultado<List<MunicipioResumido>> listarMunicipios(String paramUf, int pagina, int itens) {
        Validacao.validarPaginacao(pagina, itens, config.itensMax());
        String codigo = Validacao.resolverUf(paramUf);
        Obtido<List<MunicipioResumido>> obtido =
                obter("estados/" + codigo + "/municipios", () -> ibge.obterMunicipiosDaUf(codigo));
        Pagina<MunicipioResumido> fatia = Pagina.paginar(Dobra.ordenar(obtido.dados()), pagina, itens);
        return new Resultado<>(fatia.itens(), fatia.paginacao(), obtido.meta(), obtido.cache());
    }

    // --- US2 ---

    public Resultado<Municipio> obterMunicipio(String codigo) {
        String valido = Validacao.validarCodigoMunicipio(codigo);
        Obtido<Municipio> obtido = obter("municipios/" + valido, () -> ibge.obterMunicipio(valido));
        return new Resultado<>(obtido.dados(), null, obtido.meta(), obtido.cache());
    }
}

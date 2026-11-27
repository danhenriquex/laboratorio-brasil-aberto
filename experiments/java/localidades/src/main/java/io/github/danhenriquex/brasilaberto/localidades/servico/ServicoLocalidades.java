package io.github.danhenriquex.brasilaberto.localidades.servico;

import io.github.danhenriquex.brasilaberto.localidades.config.Configuracao;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Meta;
import io.github.danhenriquex.brasilaberto.localidades.fonte.ClienteIbge;
import io.github.danhenriquex.brasilaberto.localidades.fonte.RespostaFonte;
import java.time.Clock;
import java.time.Instant;
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
}

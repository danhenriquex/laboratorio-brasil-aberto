package io.github.danhenriquex.brasilaberto.localidades.config;

import io.github.danhenriquex.brasilaberto.localidades.fonte.ClienteIbge;
import io.github.danhenriquex.brasilaberto.localidades.servico.ServicoLocalidades;
import java.time.Clock;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/** Liga as peças. Domínio, fonte e serviço não conhecem o Spring; só este arquivo e a camada api/operacao. */
@Configuration
@EnableConfigurationProperties(Configuracao.class)
public class Montagem {

    @Bean
    Clock relogio() {
        return Clock.systemUTC();
    }

    @Bean
    ClienteIbge clienteIbge(Configuracao config) {
        return new ClienteIbge(config, (recurso, segundos) -> {});
    }

    @Bean
    ServicoLocalidades servicoLocalidades(ClienteIbge ibge, Clock relogio, Configuracao config) {
        return new ServicoLocalidades(ibge, relogio, config);
    }
}

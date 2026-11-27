package io.github.danhenriquex.brasilaberto.localidades.config;

import io.github.danhenriquex.brasilaberto.localidades.cache.CacheComValidade;
import io.github.danhenriquex.brasilaberto.localidades.fonte.ClienteIbge;
import io.github.danhenriquex.brasilaberto.localidades.operacao.FiltroCorrelacao;
import io.github.danhenriquex.brasilaberto.localidades.operacao.Metricas;
import io.github.danhenriquex.brasilaberto.localidades.servico.ServicoLocalidades;
import java.time.Clock;
import java.time.Duration;
import java.util.function.LongSupplier;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;

/** Liga as peças. Domínio, fonte e serviço não conhecem o Spring; só este arquivo e a camada api/operacao. */
@Configuration
@EnableConfigurationProperties(Configuracao.class)
public class Montagem {

    @Bean
    Clock relogio() {
        return Clock.systemUTC();
    }

    /** Relógio monotônico da validade da cópia; os testes trocam por um relógio falso. */
    @Bean
    LongSupplier monotonico() {
        return System::nanoTime;
    }

    @Bean
    CacheComValidade cacheComValidade(Clock relogio, LongSupplier monotonico, Configuracao config) {
        return new CacheComValidade(relogio, monotonico, Duration.ofMillis(Math.round(config.validadeS() * 1000)));
    }

    @Bean
    ClienteIbge clienteIbge(Configuracao config, Metricas metricas) {
        return new ClienteIbge(config, (recurso, segundos) -> {
            metricas.observarFonte(recurso, segundos);
            // A consulta roda na thread do pedido que a iniciou; quem só esperou a consulta compartilhada não soma tempo.
            RequestAttributes atributos = RequestContextHolder.getRequestAttributes();
            if (atributos != null) {
                Object anterior = atributos.getAttribute(FiltroCorrelacao.ATRIBUTO_FONTE_S, RequestAttributes.SCOPE_REQUEST);
                double total = (anterior instanceof Double d ? d : 0.0) + segundos;
                atributos.setAttribute(FiltroCorrelacao.ATRIBUTO_FONTE_S, total, RequestAttributes.SCOPE_REQUEST);
            }
        });
    }

    @Bean
    ServicoLocalidades servicoLocalidades(ClienteIbge ibge, Clock relogio, Configuracao config, CacheComValidade cache) {
        return new ServicoLocalidades(ibge, relogio, config, cache);
    }
}

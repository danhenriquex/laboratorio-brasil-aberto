package io.github.danhenriquex.brasilaberto.localidades.operacao;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.DistributionSummary;
import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.stereotype.Component;

/**
 * Métricas com os nomes do contrato (R12 do E1; R8 do E4). A duração da fonte é um DistributionSummary sem
 * unidade base: um Timer acrescentaria o sufixo "_seconds" e o nome exposto deixaria de ser o do contrato.
 */
@Component
public class Metricas {

    private static final double[] FAIXAS_FONTE_S = {0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10};

    private final MeterRegistry registro;

    public Metricas(MeterRegistry registro) {
        this.registro = registro;
    }

    public void observarFonte(String recurso, double segundos) {
        DistributionSummary.builder("localidades.fonte.duracao.segundos")
                .description("Duração das consultas ao IBGE, por recurso.")
                .tag("recurso", recurso)
                .serviceLevelObjectives(FAIXAS_FONTE_S)
                .register(registro)
                .record(segundos);
    }

    public void registrarPedido(String rota, int status, String tipoErro, String cache) {
        Counter.builder("localidades.pedidos").description("Pedidos atendidos, por modelo de rota e status.")
                .tag("rota", rota).tag("status", String.valueOf(status)).register(registro).increment();
        if (tipoErro != null) {
            Counter.builder("localidades.erros").description("Erros devolvidos, por tipo de problema.")
                    .tag("tipo", tipoErro).register(registro).increment();
        }
        if (cache != null) {
            Counter.builder("localidades.cache").description("Uso da cópia guardada: acerto, falta ou desatualizado.")
                    .tag("resultado", cache).register(registro).increment();
        }
    }
}

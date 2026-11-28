package io.github.danhenriquex.brasilaberto.localidades.operacao;

import org.apache.catalina.Valve;
import org.apache.catalina.core.StandardHost;
import org.apache.catalina.valves.ErrorReportValve;
import org.springframework.boot.tomcat.servlet.TomcatServletWebServerFactory;
import org.springframework.boot.web.server.WebServerFactoryCustomizer;
import org.springframework.core.Ordered;
import org.springframework.stereotype.Component;

/**
 * Troca a válvula de erros do Tomcat pela ValvulaDeErros (T044). Registra a classe no host, que o Tomcat usa
 * também para os erros anteriores ao roteamento, e remove do pipeline qualquer outra ErrorReportValve (como a
 * que o próprio Spring Boot registra), para sobrar só a nossa. Roda depois da configuração do Spring Boot.
 *
 * <p>Também deixa o TRACE passar do conector (T047). Sem isso, o Tomcat responde 405 sozinho e o erro cai na
 * página /error do Spring Boot, fora do problem+json. Com o DespachanteSemEco, o TRACE recebe o mesmo 404 dos
 * outros métodos não suportados, e nada do pedido é ecoado de volta.
 */
@Component
public class ConfiguracaoTomcat implements WebServerFactoryCustomizer<TomcatServletWebServerFactory>, Ordered {

    private final Metricas metricas;

    public ConfiguracaoTomcat(Metricas metricas) {
        this.metricas = metricas;
    }

    @Override
    public void customize(TomcatServletWebServerFactory fabrica) {
        ValvulaDeErros.usarMetricas(metricas);
        fabrica.addConnectorCustomizers(conector -> conector.setAllowTrace(true));
        fabrica.addContextCustomizers(contexto -> {
            if (contexto.getParent() instanceof StandardHost host) {
                host.setErrorReportValveClass(ValvulaDeErros.class.getName());
            }
            var pipeline = contexto.getParent().getPipeline();
            for (Valve valvula : pipeline.getValves()) {
                if (valvula instanceof ErrorReportValve && !(valvula instanceof ValvulaDeErros)) {
                    pipeline.removeValve(valvula);
                }
            }
            pipeline.addValve(new ValvulaDeErros());
        });
    }

    @Override
    public int getOrder() {
        return Ordered.LOWEST_PRECEDENCE;
    }
}

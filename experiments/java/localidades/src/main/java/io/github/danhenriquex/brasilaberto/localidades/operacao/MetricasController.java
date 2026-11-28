package io.github.danhenriquex.brasilaberto.localidades.operacao;

import io.micrometer.prometheusmetrics.PrometheusMeterRegistry;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/** GET /metrics no formato texto do Prometheus (os endpoints do actuator ficam desligados). */
@RestController
public class MetricasController {

    private static final MediaType TEXTO_PROMETHEUS = MediaType.parseMediaType("text/plain; version=0.0.4; charset=utf-8");

    private final PrometheusMeterRegistry registro;

    public MetricasController(PrometheusMeterRegistry registro) {
        this.registro = registro;
    }

    @GetMapping("/metrics")
    public ResponseEntity<String> metricas() {
        return ResponseEntity.ok().contentType(TEXTO_PROMETHEUS).body(registro.scrape());
    }
}

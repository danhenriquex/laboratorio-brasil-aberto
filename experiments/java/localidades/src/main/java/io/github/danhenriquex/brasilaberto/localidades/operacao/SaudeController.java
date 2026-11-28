package io.github.danhenriquex.brasilaberto.localidades.operacao;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/** /health próprio: o do actuator responde {"status":"UP"} e o contrato exige {"status":"ok"}. Nunca consulta o IBGE. */
@RestController
public class SaudeController {

    @GetMapping("/health")
    public Map<String, String> saude() {
        return Map.of("status", "ok");
    }
}

package io.github.danhenriquex.brasilaberto.localidades.operacao;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import tools.jackson.databind.json.JsonMapper;

/**
 * Uma linha JSON por pedido no stdout, com os mesmos campos do E1 (R12 do E1; R9 do E4).
 * Não registra IP nem cabeçalhos além da correlação (Constituição VII).
 */
public final class RegistroPedidos {

    public static final String LOGGER = "localidades.pedidos";

    private static final Logger SAIDA = LoggerFactory.getLogger(LOGGER);
    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final DateTimeFormatter MOMENTO =
            DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'").withZone(ZoneOffset.UTC);

    private RegistroPedidos() {}

    public static void registrar(String correlacaoId, String metodo, String rota, int status, double duracaoMs,
            String cache, Double fonteMs) {
        Map<String, Object> campos = new LinkedHashMap<>();
        campos.put("momento", MOMENTO.format(Instant.now()));
        campos.put("nivel", status >= 500 ? "error" : "info");
        campos.put("correlacao_id", correlacaoId);
        campos.put("metodo", metodo);
        campos.put("rota", rota);
        campos.put("status", status);
        campos.put("duracao_ms", Math.round(duracaoMs * 10) / 10.0);
        campos.put("cache", cache);
        campos.put("fonte_ms", fonteMs == null ? null : Math.round(fonteMs * 10) / 10.0);
        String linha = JSON.writeValueAsString(campos);
        if (status >= 500) {
            SAIDA.error(linha);
        } else {
            SAIDA.info(linha);
        }
    }
}

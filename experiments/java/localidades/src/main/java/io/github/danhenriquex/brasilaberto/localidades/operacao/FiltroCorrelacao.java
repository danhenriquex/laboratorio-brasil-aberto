package io.github.danhenriquex.brasilaberto.localidades.operacao;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import io.github.danhenriquex.brasilaberto.localidades.api.Resposta;
import io.github.danhenriquex.brasilaberto.localidades.api.TratadorDeErros;
import java.io.IOException;
import java.util.UUID;
import java.util.regex.Pattern;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.servlet.HandlerMapping;

/**
 * X-Correlation-Id (R12 do E1): aceita 1 a 64 caracteres em [A-Za-z0-9._-]; senão gera um UUID v4.
 * No fim de cada pedido, registra as métricas e uma linha JSON (US5).
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class FiltroCorrelacao extends OncePerRequestFilter {

    public static final String CABECALHO = "X-Correlation-Id";
    public static final String ATRIBUTO = "correlacao_id";
    /** Tempo gasto com o IBGE no pedido, em segundos, anotado pelo ClienteIbge (via Montagem). */
    public static final String ATRIBUTO_FONTE_S = "fonte_s";
    private static final Pattern VALIDO = Pattern.compile("[A-Za-z0-9._-]{1,64}");

    public static String correlacaoDe(String valor) {
        return valor != null && VALIDO.matcher(valor).matches() ? valor : UUID.randomUUID().toString();
    }

    private final Metricas metricas;

    public FiltroCorrelacao(Metricas metricas) {
        this.metricas = metricas;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest pedido, HttpServletResponse resposta, FilterChain cadeia)
            throws ServletException, IOException {
        String correlacao = correlacaoDe(pedido.getHeader(CABECALHO));
        pedido.setAttribute(ATRIBUTO, correlacao);
        resposta.setHeader(CABECALHO, correlacao);
        long inicio = System.nanoTime();
        try {
            cadeia.doFilter(pedido, resposta);
        } finally {
            Object padrao = pedido.getAttribute(HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE);
            String rota = padrao != null ? padrao.toString() : "nao-encontrado";
            String cache = (String) pedido.getAttribute(Resposta.ATRIBUTO_CACHE);
            Double fonteS = (Double) pedido.getAttribute(ATRIBUTO_FONTE_S);
            metricas.registrarPedido(rota, resposta.getStatus(), (String) pedido.getAttribute(TratadorDeErros.ATRIBUTO_TIPO_ERRO), cache);
            RegistroPedidos.registrar(correlacao, pedido.getMethod(), rota, resposta.getStatus(),
                    (System.nanoTime() - inicio) / 1e6, cache, fonteS == null ? null : fonteS * 1000);
        }
    }
}

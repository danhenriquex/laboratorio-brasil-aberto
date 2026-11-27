package io.github.danhenriquex.brasilaberto.localidades.operacao;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.UUID;
import java.util.regex.Pattern;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/** X-Correlation-Id (R12 do E1): aceita 1 a 64 caracteres em [A-Za-z0-9._-]; senão gera um UUID v4. */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class FiltroCorrelacao extends OncePerRequestFilter {

    public static final String CABECALHO = "X-Correlation-Id";
    public static final String ATRIBUTO = "correlacao_id";
    private static final Pattern VALIDO = Pattern.compile("[A-Za-z0-9._-]{1,64}");

    public static String correlacaoDe(String valor) {
        return valor != null && VALIDO.matcher(valor).matches() ? valor : UUID.randomUUID().toString();
    }

    @Override
    protected void doFilterInternal(HttpServletRequest pedido, HttpServletResponse resposta, FilterChain cadeia)
            throws ServletException, IOException {
        String correlacao = correlacaoDe(pedido.getHeader(CABECALHO));
        pedido.setAttribute(ATRIBUTO, correlacao);
        resposta.setHeader(CABECALHO, correlacao);
        cadeia.doFilter(pedido, resposta);
    }
}

package io.github.danhenriquex.brasilaberto.localidades.operacao;

import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.web.servlet.DispatcherServlet;

/**
 * DispatcherServlet que trata o TRACE como qualquer outro método não suportado (T047): passa pelo filtro de
 * correlação, pelas métricas e pelo TratadorDeErros, e sai 404 em problem+json.
 *
 * <p>O padrão do Spring (spring.mvc.dispatch-trace-request=true) despacha o TRACE, mas, como a resposta não é
 * "message/http", ainda chama o HttpServlet.doTrace, que ecoa o pedido inteiro, cabeçalhos inclusive, depois
 * do corpo. Aqui nada é ecoado.
 */
public class DespachanteSemEco extends DispatcherServlet {

    @Override
    protected void doTrace(HttpServletRequest pedido, HttpServletResponse resposta) throws ServletException, IOException {
        processRequest(pedido, resposta);
    }
}

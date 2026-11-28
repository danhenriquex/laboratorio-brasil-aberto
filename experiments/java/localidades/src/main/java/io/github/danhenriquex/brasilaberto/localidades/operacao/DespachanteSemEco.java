package io.github.danhenriquex.brasilaberto.localidades.operacao;

import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import org.springframework.web.servlet.DispatcherServlet;
import org.springframework.web.servlet.HandlerExecutionChain;

/**
 * DispatcherServlet com dois ajustes de roteamento, para o E4 se comportar como o E1. Nos dois casos, o pedido
 * passa pelo filtro de correlação, pelas métricas e pelo TratadorDeErros, e sai 404 em problem+json.
 *
 * <p><b>TRACE (T047).</b> O padrão do Spring (spring.mvc.dispatch-trace-request=true) despacha o TRACE, mas,
 * como a resposta não é "message/http", ainda chama o HttpServlet.doTrace, que ecoa o pedido inteiro, cabeçalhos
 * inclusive, depois do corpo. Aqui o TRACE é tratado como qualquer outro método não suportado, e nada é ecoado.
 *
 * <p><b>Parâmetros de caminho (T050).</b> O Tomcat e o Spring descartam o trecho depois de ";" em cada segmento,
 * então "/v1/ufs;jsessionid=x" casaria com "/v1/ufs". Pela RFC 3986, o ";" faz parte do segmento, e no E1 esse
 * caminho não existe. Com ";" no caminho cru, nenhuma rota casa (NoHandlerFoundException → 404).
 */
public class DespachanteSemEco extends DispatcherServlet {

    @Override
    protected void doTrace(HttpServletRequest pedido, HttpServletResponse resposta) throws ServletException, IOException {
        processRequest(pedido, resposta);
    }

    @Override
    protected HandlerExecutionChain getHandler(HttpServletRequest pedido) throws Exception {
        return pedido.getRequestURI().indexOf(';') >= 0 ? null : super.getHandler(pedido);
    }
}

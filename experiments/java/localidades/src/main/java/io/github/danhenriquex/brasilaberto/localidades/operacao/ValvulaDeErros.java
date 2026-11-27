package io.github.danhenriquex.brasilaberto.localidades.operacao;

import java.io.IOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;
import org.apache.catalina.connector.Request;
import org.apache.catalina.connector.Response;
import org.apache.catalina.valves.ErrorReportValve;
import tools.jackson.databind.json.JsonMapper;

/**
 * Erros que o Tomcat gera antes de o pedido chegar ao Spring (codificação inválida no caminho, barra
 * codificada) saem no mesmo formato do resto do serviço: problem+json com X-Correlation-Id (T044).
 * Sem ela, o Tomcat devolveria a própria página HTML.
 */
public class ValvulaDeErros extends ErrorReportValve {

    private static final JsonMapper JSON = JsonMapper.builder().build();

    /** O Tomcat cria a válvula pela classe (construtor sem argumentos), então as métricas chegam por aqui. */
    private static volatile Metricas metricas;

    public static void usarMetricas(Metricas instancia) {
        metricas = instancia;
    }

    @Override
    protected void report(Request pedido, Response resposta, Throwable erro) {
        int status = resposta.getStatus();
        // Só os erros que ninguém escreveu ainda: os do Spring já saem em problem+json pelo TratadorDeErros.
        if (status < 400 || resposta.getContentWritten() > 0 || !resposta.setErrorReported()) {
            return;
        }
        String correlacao = FiltroCorrelacao.correlacaoDe(pedido.getHeader(FiltroCorrelacao.CABECALHO));
        boolean doCliente = status < 500;
        String tipo = status == 404 ? "nao-encontrado" : doCliente ? "entrada-invalida" : "erro-interno";
        int statusContrato = status == 404 ? 404 : doCliente ? 400 : 500;
        Map<String, Object> corpo = new LinkedHashMap<>();
        corpo.put("type", "urn:brasil-aberto:problema:" + tipo);
        corpo.put("title", status == 404 ? "Não encontrado" : doCliente ? "Entrada inválida" : "Erro interno do serviço");
        corpo.put("status", statusContrato);
        corpo.put("detail", doCliente ? "o endereço do pedido é inválido" : "erro interno do serviço");
        corpo.put("correlacao_id", correlacao);
        try {
            resposta.setStatus(statusContrato);
            resposta.setContentType("application/problem+json");
            resposta.setCharacterEncoding(StandardCharsets.UTF_8.name());
            resposta.setHeader(FiltroCorrelacao.CABECALHO, correlacao);
            Writer saida = resposta.getReporter();
            if (saida != null) {
                saida.write(JSON.writeValueAsString(corpo));
                saida.flush();
            }
        } catch (IOException | IllegalStateException e) {
            // a conexão pode já ter sido fechada; nada a fazer
        }
        if (metricas != null) {
            metricas.registrarPedido("nao-encontrado", statusContrato, tipo, null);
        }
        RegistroPedidos.registrar(correlacao, pedido.getMethod(), "nao-encontrado", statusContrato, 0, null, null);
    }
}

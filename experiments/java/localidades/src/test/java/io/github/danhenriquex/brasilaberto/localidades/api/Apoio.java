package io.github.danhenriquex.brasilaberto.localidades.api;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Pattern;
import org.springframework.test.web.servlet.MvcResult;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Asserções comuns dos testes de API, equivalentes ao assert_problema e assert_meta do E1. */
final class Apoio {

    static final JsonMapper JSON = JsonMapper.builder().build();
    static final Pattern COLETADO_EM = Pattern.compile("^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}Z$");

    private Apoio() {}

    static JsonNode json(MvcResult r) throws Exception {
        return JSON.readTree(r.getResponse().getContentAsString(StandardCharsets.UTF_8));
    }

    static JsonNode assertProblema(MvcResult r, int status, String tipo) throws Exception {
        assertThat(r.getResponse().getStatus()).as(r.getResponse().getContentAsString()).isEqualTo(status);
        assertThat(r.getResponse().getContentType()).startsWith("application/problem+json");
        JsonNode corpo = json(r);
        assertThat(corpo.get("type").asString()).isEqualTo("urn:brasil-aberto:problema:" + tipo);
        assertThat(corpo.get("status").asInt()).isEqualTo(status);
        assertThat(corpo.get("detail").asString()).isNotBlank();
        assertThat(corpo.get("correlacao_id").asString()).isEqualTo(r.getResponse().getHeader("X-Correlation-Id"));
        return corpo;
    }

    static void assertMeta(JsonNode meta, String urlFonte, boolean desatualizado) {
        assertThat(meta.get("fonte").asString()).isEqualTo("IBGE — API de localidades");
        assertThat(meta.get("url_fonte").asString()).isEqualTo(urlFonte);
        assertThat(meta.get("url_documentacao").asString()).isEqualTo("https://servicodados.ibge.gov.br/api/docs/localidades");
        assertThat(meta.get("coletado_em").asString()).matches(COLETADO_EM);
        assertThat(meta.get("desatualizado").asBoolean()).isEqualTo(desatualizado);
    }

    /** Resposta de um pedido cru: cabeçalhos com nome em minúsculas e o corpo já sem o "chunked". */
    record RespostaCrua(int status, Map<String, String> cabecalhos, String corpo, String bruto) {
        String cabecalho(String nome) {
            return cabecalhos.get(nome.toLowerCase(Locale.ROOT));
        }

        JsonNode json() {
            return JSON.readTree(corpo);
        }
    }

    /**
     * Pedido HTTP escrito à mão no socket, contra o Tomcat de verdade (T046, T047). O MockMvc não passa pela
     * decodificação da query nem pelo conector do Tomcat, e o HttpClient da JDK recusa um "%" inválido na URI.
     */
    static RespostaCrua pedidoCru(int porta, String metodo, String alvo, String... cabecalhosExtras) throws IOException {
        try (Socket socket = new Socket("127.0.0.1", porta)) {
            socket.setSoTimeout(10_000);
            var pedido = new StringBuilder(metodo + " " + alvo + " HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n");
            for (String cabecalho : cabecalhosExtras) {
                pedido.append(cabecalho).append("\r\n");
            }
            socket.getOutputStream().write(pedido.append("\r\n").toString().getBytes(StandardCharsets.US_ASCII));
            String bruto = new String(socket.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
            int fim = bruto.indexOf("\r\n\r\n");
            String[] linhas = bruto.substring(0, fim).split("\r\n");
            Map<String, String> cabecalhos = new HashMap<>();
            for (int i = 1; i < linhas.length; i++) {
                int doisPontos = linhas[i].indexOf(':');
                cabecalhos.put(linhas[i].substring(0, doisPontos).trim().toLowerCase(Locale.ROOT), linhas[i].substring(doisPontos + 1).trim());
            }
            String corpo = bruto.substring(fim + 4);
            if ("chunked".equalsIgnoreCase(cabecalhos.get("transfer-encoding"))) {
                corpo = semChunked(corpo);
            }
            return new RespostaCrua(Integer.parseInt(linhas[0].split(" ")[1]), cabecalhos, corpo, bruto);
        }
    }

    /** Desfaz o "chunked" byte a byte: o tamanho de cada pedaço conta bytes, e o corpo tem acentos. */
    private static String semChunked(String corpo) {
        byte[] bytes = corpo.getBytes(StandardCharsets.UTF_8);
        var saida = new ByteArrayOutputStream();
        int i = 0;
        while (true) {
            int fimLinha = i;
            while (bytes[fimLinha] != '\r') {
                fimLinha++;
            }
            int tamanho = Integer.parseInt(new String(bytes, i, fimLinha - i, StandardCharsets.US_ASCII).trim(), 16);
            if (tamanho == 0) {
                return saida.toString(StandardCharsets.UTF_8);
            }
            saida.write(bytes, fimLinha + 2, tamanho);
            i = fimLinha + 2 + tamanho + 2;
        }
    }
}

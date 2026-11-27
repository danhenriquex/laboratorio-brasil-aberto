package io.github.danhenriquex.brasilaberto.localidades.fonte;

import io.github.danhenriquex.brasilaberto.localidades.config.Configuracao;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Municipio;
import io.github.danhenriquex.brasilaberto.localidades.dominio.MunicipioResumido;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Regiao;
import io.github.danhenriquex.brasilaberto.localidades.dominio.RegiaoImediata;
import io.github.danhenriquex.brasilaberto.localidades.dominio.RegiaoIntermediaria;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Uf;
import io.github.danhenriquex.brasilaberto.localidades.dominio.UfResumida;
import io.github.danhenriquex.brasilaberto.localidades.erros.FonteIndisponivel;
import io.github.danhenriquex.brasilaberto.localidades.erros.FonteLenta;
import io.github.danhenriquex.brasilaberto.localidades.erros.NaoEncontrado;
import io.github.danhenriquex.brasilaberto.localidades.erros.RespostaInesperadaDaFonte;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.function.BiConsumer;
import java.util.regex.Pattern;
import tools.jackson.core.JacksonException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/**
 * Cliente da API de localidades do IBGE (research do E4, R4): prazo total com orTimeout, uma chamada por
 * consulta, classificação das falhas (R6 do E1) e normalização com o formato exato (T048 e T049 do E1).
 * As mensagens de erro nunca carregam o corpo devolvido pelo IBGE (FR-013).
 */
public class ClienteIbge {

    public static final String USER_AGENT = "laboratorio-brasil-aberto-localidades/0.1.0";

    private static final Pattern SIGLA_UF = Pattern.compile("[A-Z]{2}");
    private static final Pattern SIGLA_REGIAO = Pattern.compile("[A-Z]{1,2}");
    private static final JsonMapper JSON = JsonMapper.builder().build();

    private final String base;
    private final Duration prazo;
    private final BiConsumer<String, Double> aoMedir;
    private final HttpClient http;

    public ClienteIbge(Configuracao config, BiConsumer<String, Double> aoMedir) {
        this.base = config.ibgeUrl();
        this.prazo = Duration.ofMillis(Math.round(config.prazoFonteS() * 1000));
        this.aoMedir = aoMedir;
        this.http = HttpClient.newBuilder()
                .version(HttpClient.Version.HTTP_1_1)
                .connectTimeout(prazo)
                .followRedirects(HttpClient.Redirect.NEVER)
                .build();
    }

    public String url(String caminho) {
        return base + "/" + caminho;
    }

    /** Forma inesperada da resposta do IBGE. */
    private static final class FormaInesperada extends RuntimeException {
        FormaInesperada(String motivo) {
            super(motivo, null, false, false);
        }
    }

    private RespostaFonte<JsonNode> buscarJson(String caminho, String recurso) {
        String url = url(caminho);
        HttpRequest pedido = HttpRequest.newBuilder(URI.create(url))
                .header("User-Agent", USER_AGENT)
                .header("Accept", "application/json")
                .GET()
                .build();
        long inicio = System.nanoTime();
        HttpResponse<byte[]> resposta;
        try {
            resposta = http.sendAsync(pedido, HttpResponse.BodyHandlers.ofByteArray())
                    .orTimeout(prazo.toMillis(), TimeUnit.MILLISECONDS)
                    .get();
        } catch (InterruptedException erro) {
            Thread.currentThread().interrupt();
            throw new FonteIndisponivel("a consulta ao IBGE foi interrompida");
        } catch (ExecutionException erro) {
            Throwable causa = erro.getCause();
            if (causa instanceof TimeoutException || causa instanceof HttpTimeoutException) {
                throw new FonteLenta("o IBGE não respondeu em " + formatarSegundos() + " s");
            }
            if (causa instanceof IOException) {
                throw new FonteIndisponivel("não foi possível conectar ao IBGE");
            }
            throw new FonteIndisponivel("falha ao consultar o IBGE");
        } finally {
            aoMedir.accept(recurso, (System.nanoTime() - inicio) / 1e9);
        }

        int status = resposta.statusCode();
        if (status >= 500 || status == 429) {
            throw new FonteIndisponivel("o IBGE respondeu com status " + status);
        }
        if (status != 200) {
            throw new RespostaInesperadaDaFonte("o IBGE respondeu com status " + status);
        }
        try {
            return new RespostaFonte<>(JSON.readTree(resposta.body()), url);
        } catch (JacksonException erro) {
            throw new RespostaInesperadaDaFonte("o IBGE respondeu um conteúdo que não é JSON");
        }
    }

    private String formatarSegundos() {
        double s = prazo.toMillis() / 1000.0;
        return s == Math.floor(s) ? String.valueOf((long) s) : String.valueOf(s);
    }

    // --- normalização ---

    private static JsonNode campo(JsonNode objeto, String chave) {
        if (objeto == null || !objeto.isObject() || !objeto.has(chave) || objeto.get(chave).isNull()) {
            throw new FormaInesperada("campo obrigatório ausente: " + chave);
        }
        return objeto.get(chave);
    }

    private static String codigo(JsonNode objeto, int digitos) {
        JsonNode valor = campo(objeto, "id");
        String texto;
        if (valor.isIntegralNumber()) {
            texto = valor.asString();
        } else if (valor.isString()) {
            texto = valor.asString().strip();
        } else {
            throw new FormaInesperada("id com tipo inesperado");
        }
        // Tamanho exato: completar com zeros inventaria um código que o IBGE não publicou (T048 do E1).
        if (texto.length() != digitos || !texto.chars().allMatch(c -> c >= '0' && c <= '9')) {
            throw new FormaInesperada("id fora do formato de " + digitos + " dígitos");
        }
        return texto;
    }

    private static String texto(JsonNode objeto, String chave) {
        JsonNode valor = campo(objeto, chave);
        if (!valor.isString() || valor.asString().isBlank()) {
            throw new FormaInesperada("campo " + chave + " vazio ou não textual");
        }
        return valor.asString();
    }

    private static String sigla(JsonNode objeto, Pattern formato) {
        String valor = texto(objeto, "sigla");
        if (!formato.matcher(valor).matches()) {
            throw new FormaInesperada("sigla fora do formato esperado");
        }
        return valor;
    }

    private static List<JsonNode> lista(JsonNode dados) {
        if (!dados.isArray()) {
            throw new FormaInesperada("esperava uma lista");
        }
        List<JsonNode> itens = new ArrayList<>();
        dados.forEach(itens::add);
        return itens;
    }

    private static Uf uf(JsonNode objeto) {
        JsonNode regiao = campo(objeto, "regiao");
        return new Uf(codigo(objeto, 2), sigla(objeto, SIGLA_UF), texto(objeto, "nome"),
                new Regiao(codigo(regiao, 1), sigla(regiao, SIGLA_REGIAO), texto(regiao, "nome")));
    }

    private static Municipio municipio(JsonNode objeto) {
        JsonNode imediata = campo(objeto, "regiao-imediata");
        JsonNode intermediaria = campo(imediata, "regiao-intermediaria");
        JsonNode uf = campo(intermediaria, "UF");
        return new Municipio(codigo(objeto, 7), texto(objeto, "nome"),
                new UfResumida(codigo(uf, 2), sigla(uf, SIGLA_UF), texto(uf, "nome")),
                new RegiaoImediata(codigo(imediata, 6), texto(imediata, "nome")),
                new RegiaoIntermediaria(codigo(intermediaria, 4), texto(intermediaria, "nome")));
    }

    // --- recursos ---

    public RespostaFonte<List<Uf>> obterEstados() {
        var r = buscarJson("estados", "estados");
        try {
            List<JsonNode> itens = lista(r.dados());
            if (itens.isEmpty()) {
                throw new FormaInesperada("lista de UFs vazia");
            }
            return new RespostaFonte<>(itens.stream().map(ClienteIbge::uf).toList(), r.urlFonte());
        } catch (FormaInesperada erro) {
            throw new RespostaInesperadaDaFonte("a lista de UFs do IBGE veio fora do formato esperado (" + erro.getMessage() + ")");
        }
    }

    public RespostaFonte<List<MunicipioResumido>> obterMunicipiosDaUf(String codigoUf) {
        var r = buscarJson("estados/" + codigoUf + "/municipios", "municipios_da_uf");
        try {
            List<JsonNode> itens = lista(r.dados());
            if (itens.isEmpty()) {
                throw new FormaInesperada("lista vazia para uma UF existente");
            }
            return new RespostaFonte<>(
                    itens.stream().map(i -> new MunicipioResumido(codigo(i, 7), texto(i, "nome"))).toList(), r.urlFonte());
        } catch (FormaInesperada erro) {
            throw new RespostaInesperadaDaFonte(
                    "a lista de municípios da UF " + codigoUf + " veio fora do formato esperado (" + erro.getMessage() + ")");
        }
    }

    public RespostaFonte<Municipio> obterMunicipio(String codigo) {
        var r = buscarJson("municipios/" + codigo, "municipio");
        JsonNode dados = r.dados();
        if (dados.isArray() && dados.isEmpty()) {
            throw new NaoEncontrado("não existe município com o código " + codigo);
        }
        Municipio municipio;
        try {
            if (dados.isArray()) {
                if (dados.size() != 1) {
                    throw new FormaInesperada("esperava um único município");
                }
                dados = dados.get(0);
            }
            municipio = municipio(dados);
        } catch (FormaInesperada erro) {
            throw new RespostaInesperadaDaFonte("o município " + codigo + " veio fora do formato esperado (" + erro.getMessage() + ")");
        }
        if (!municipio.codigo().equals(codigo)) {
            throw new RespostaInesperadaDaFonte("o IBGE devolveu outro município ao pedir " + codigo);
        }
        return new RespostaFonte<>(municipio, r.urlFonte());
    }
}

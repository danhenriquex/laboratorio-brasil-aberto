package io.github.danhenriquex.brasilaberto.localidades.api;

import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.web.servlet.config.annotation.ContentNegotiationConfigurer;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * O formato da resposta não depende do cabeçalho Accept, como no E1 (T048). O contrato só declara
 * application/json para o sucesso e application/problem+json para o erro. Com a negociação padrão do Spring,
 * um Accept sem JSON (application/xml, text/html, text/plain) virava 500, e um Accept de problem+json fazia o
 * sucesso sair com o tipo de erro.
 */
@Configuration
public class FormatoDaResposta implements WebMvcConfigurer {

    @Override
    public void configureContentNegotiation(ContentNegotiationConfigurer negociacao) {
        negociacao.ignoreAcceptHeader(true).defaultContentType(MediaType.APPLICATION_JSON);
    }
}

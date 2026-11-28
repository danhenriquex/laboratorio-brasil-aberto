package io.github.danhenriquex.brasilaberto.localidades.api;

import io.github.danhenriquex.brasilaberto.localidades.erros.EntradaInvalida;
import io.github.danhenriquex.brasilaberto.localidades.erros.ErroDominio;
import io.github.danhenriquex.brasilaberto.localidades.erros.ErroInterno;
import io.github.danhenriquex.brasilaberto.localidades.erros.NaoEncontrado;
import io.github.danhenriquex.brasilaberto.localidades.operacao.FiltroCorrelacao;
import jakarta.servlet.http.HttpServletRequest;
import java.net.URI;
import org.apache.tomcat.util.http.InvalidParameterException;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.NoHandlerFoundException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

/** Erros em application/problem+json (RFC 9457) com o ProblemDetail nativo do Spring (research do E4, R6). */
@RestControllerAdvice
public class TratadorDeErros {

    public static final String ATRIBUTO_TIPO_ERRO = "erro_tipo";

    static ResponseEntity<ProblemDetail> problema(ErroDominio erro, HttpServletRequest pedido) {
        ProblemDetail corpo = ProblemDetail.forStatusAndDetail(HttpStatusCode.valueOf(erro.status()), erro.detalhe());
        corpo.setType(URI.create(erro.urn()));
        corpo.setTitle(erro.titulo());
        Object correlacao = pedido.getAttribute(FiltroCorrelacao.ATRIBUTO);
        corpo.setProperty("correlacao_id", correlacao != null ? correlacao : FiltroCorrelacao.correlacaoDe(null));
        pedido.setAttribute(ATRIBUTO_TIPO_ERRO, erro.tipo());
        return ResponseEntity.status(erro.status()).body(corpo);
    }

    @ExceptionHandler(ErroDominio.class)
    ResponseEntity<ProblemDetail> erroDeDominio(ErroDominio erro, HttpServletRequest pedido) {
        return problema(erro, pedido);
    }

    @ExceptionHandler({NoHandlerFoundException.class, NoResourceFoundException.class, HttpRequestMethodNotSupportedException.class})
    ResponseEntity<ProblemDetail> rotaInexistente(Exception erro, HttpServletRequest pedido) {
        return problema(new NaoEncontrado("a rota " + pedido.getRequestURI() + " não existe"), pedido);
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    ResponseEntity<ProblemDetail> parametroInvalido(MethodArgumentTypeMismatchException erro, HttpServletRequest pedido) {
        return problema(new EntradaInvalida(erro.getName() + ": valor inválido"), pedido);
    }

    /**
     * O Tomcat só decodifica a query quando o controller lê o primeiro parâmetro; se ela estiver mal codificada
     * (por exemplo "nome=%ZZ"), a falha é do pedido, não do serviço (T046).
     */
    @ExceptionHandler(InvalidParameterException.class)
    ResponseEntity<ProblemDetail> queryMalCodificada(InvalidParameterException erro, HttpServletRequest pedido) {
        return problema(new EntradaInvalida("os parâmetros da consulta têm codificação inválida"), pedido);
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<ProblemDetail> erroInesperado(Exception erro, HttpServletRequest pedido) {
        return problema(new ErroInterno("erro interno do serviço"), pedido);
    }
}

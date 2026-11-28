package io.github.danhenriquex.brasilaberto.localidades.erros;

/** Erro de domínio com o tipo de problema RFC 9457 (research do E1, R11). */
public abstract class ErroDominio extends RuntimeException {

    public static final String PREFIXO_URN = "urn:brasil-aberto:problema:";

    protected ErroDominio(String detalhe) {
        super(detalhe);
    }

    public abstract String tipo();

    public abstract String titulo();

    public abstract int status();

    public String urn() {
        return PREFIXO_URN + tipo();
    }

    public String detalhe() {
        return getMessage();
    }
}

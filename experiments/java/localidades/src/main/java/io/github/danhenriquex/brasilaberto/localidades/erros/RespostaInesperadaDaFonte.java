package io.github.danhenriquex.brasilaberto.localidades.erros;

public final class RespostaInesperadaDaFonte extends ErroDominio implements ErroDeFonte {

    public RespostaInesperadaDaFonte(String detalhe) {
        super(detalhe);
    }

    @Override
    public String tipo() {
        return "resposta-inesperada-da-fonte";
    }

    @Override
    public String titulo() {
        return "Resposta inesperada da fonte";
    }

    @Override
    public int status() {
        return 502;
    }
}

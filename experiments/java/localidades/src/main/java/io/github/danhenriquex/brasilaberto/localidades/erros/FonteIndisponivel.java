package io.github.danhenriquex.brasilaberto.localidades.erros;

public final class FonteIndisponivel extends ErroDominio implements ErroDeFonte {

    public FonteIndisponivel(String detalhe) {
        super(detalhe);
    }

    @Override
    public String tipo() {
        return "fonte-indisponivel";
    }

    @Override
    public String titulo() {
        return "Fonte indisponível";
    }

    @Override
    public int status() {
        return 502;
    }
}

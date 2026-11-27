package io.github.danhenriquex.brasilaberto.localidades.erros;

public final class FonteLenta extends ErroDominio implements ErroDeFonte {

    public FonteLenta(String detalhe) {
        super(detalhe);
    }

    @Override
    public String tipo() {
        return "fonte-lenta";
    }

    @Override
    public String titulo() {
        return "Fonte lenta";
    }

    @Override
    public int status() {
        return 504;
    }
}

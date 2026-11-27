package io.github.danhenriquex.brasilaberto.localidades.erros;

public final class EntradaInvalida extends ErroDominio {

    public EntradaInvalida(String detalhe) {
        super(detalhe);
    }

    @Override
    public String tipo() {
        return "entrada-invalida";
    }

    @Override
    public String titulo() {
        return "Entrada inválida";
    }

    @Override
    public int status() {
        return 400;
    }
}

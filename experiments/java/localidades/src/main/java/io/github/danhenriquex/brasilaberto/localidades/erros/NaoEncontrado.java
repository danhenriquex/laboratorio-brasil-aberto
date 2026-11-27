package io.github.danhenriquex.brasilaberto.localidades.erros;

public final class NaoEncontrado extends ErroDominio {

    public NaoEncontrado(String detalhe) {
        super(detalhe);
    }

    @Override
    public String tipo() {
        return "nao-encontrado";
    }

    @Override
    public String titulo() {
        return "Não encontrado";
    }

    @Override
    public int status() {
        return 404;
    }
}

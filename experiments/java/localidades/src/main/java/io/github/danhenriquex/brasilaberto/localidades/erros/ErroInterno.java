package io.github.danhenriquex.brasilaberto.localidades.erros;

public final class ErroInterno extends ErroDominio {

    public ErroInterno(String detalhe) {
        super(detalhe);
    }

    @Override
    public String tipo() {
        return "erro-interno";
    }

    @Override
    public String titulo() {
        return "Erro interno do serviço";
    }

    @Override
    public int status() {
        return 500;
    }
}

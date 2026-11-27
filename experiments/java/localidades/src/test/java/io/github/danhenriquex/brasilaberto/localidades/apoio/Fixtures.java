package io.github.danhenriquex.brasilaberto.localidades.apoio;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;

/** Lê as fixtures do IBGE compartilhadas com o E1 em contracts/localidades/fixtures-ibge/. */
public final class Fixtures {

    public static final Path PASTA = raizDoRepositorio().resolve("contracts/localidades/fixtures-ibge");

    private Fixtures() {}

    private static Path raizDoRepositorio() {
        Path atual = Path.of("").toAbsolutePath();
        while (atual != null) {
            if (Files.isDirectory(atual.resolve("contracts/localidades"))) {
                return atual;
            }
            atual = atual.getParent();
        }
        throw new IllegalStateException("raiz do repositório não encontrada");
    }

    public static byte[] bytes(String nome) {
        try {
            return Files.readAllBytes(PASTA.resolve(nome));
        } catch (IOException erro) {
            throw new UncheckedIOException(erro);
        }
    }

    public static String texto(String nome) {
        return new String(bytes(nome), java.nio.charset.StandardCharsets.UTF_8);
    }
}

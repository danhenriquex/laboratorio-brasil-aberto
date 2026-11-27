package io.github.danhenriquex.brasilaberto.localidades.dominio;

import java.text.Normalizer;
import java.util.Collection;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.regex.Pattern;

/**
 * Regra de dobra do R8 do E1: NFKD, sem marcas diacríticas (categoria Mn) e caixa ignorada.
 *
 * <p>A JDK não tem "casefold"; {@code toLowerCase(Locale.ROOT)} difere só em casos como "ß", que não
 * ocorrem em nomes de municípios. A paridade com o E1 é verificada pela suíte (FR-004).
 */
public final class Dobra {

    private static final Pattern MARCAS = Pattern.compile("\\p{Mn}+");

    private Dobra() {}

    public static String dobrar(String texto) {
        return MARCAS.matcher(Normalizer.normalize(texto, Normalizer.Form.NFKD)).replaceAll("").toLowerCase(Locale.ROOT);
    }

    /** Ordena por (nome dobrado, código), como no E1. */
    public static <T> List<T> ordenar(Collection<T> itens, java.util.function.Function<T, String> nome, java.util.function.Function<T, String> codigo) {
        return itens.stream()
                .sorted(Comparator.comparing((T item) -> dobrar(nome.apply(item))).thenComparing(codigo))
                .toList();
    }

    public static List<MunicipioResumido> ordenar(Collection<MunicipioResumido> itens) {
        return ordenar(itens, MunicipioResumido::nome, MunicipioResumido::codigo);
    }

    public static List<MunicipioResumido> filtrarPorNome(Collection<MunicipioResumido> itens, String nome) {
        String alvo = dobrar(nome.strip());
        return itens.stream().filter(m -> dobrar(m.nome()).contains(alvo)).toList();
    }
}

package io.github.danhenriquex.brasilaberto.localidades.dominio;

import java.util.List;

/** Uma página já filtrada e ordenada. Página além do fim devolve lista vazia com o total correto. */
public record Pagina<T>(List<T> itens, Paginacao paginacao) {

    public static <T> Pagina<T> paginar(List<T> colecao, int pagina, int itens) {
        int total = colecao.size();
        long inicio = (long) (pagina - 1) * itens;
        List<T> fatia = inicio >= total ? List.of() : colecao.subList((int) inicio, (int) Math.min(inicio + itens, total));
        int paginas = total == 0 ? 0 : (total + itens - 1) / itens;
        return new Pagina<>(List.copyOf(fatia), new Paginacao(pagina, itens, total, paginas));
    }
}

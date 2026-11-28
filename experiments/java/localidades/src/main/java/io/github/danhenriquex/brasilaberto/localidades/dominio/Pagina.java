package io.github.danhenriquex.brasilaberto.localidades.dominio;

import java.util.List;

/** Uma página já filtrada e ordenada. Página além do fim devolve lista vazia com o total correto. */
public record Pagina<T>(List<T> itens, Paginacao paginacao) {

    public static <T> Pagina<T> paginar(List<T> colecao, long pagina, int itens) {
        int total = colecao.size();
        // pagina pode ser enorme (o contrato não limita): além do fim, a lista vem vazia com o total correto
        List<T> fatia = pagina - 1 >= (total + itens - 1L) / itens ? List.of() : colecao.subList((int) ((pagina - 1) * itens), (int) Math.min((pagina - 1) * itens + itens, total));
        int paginas = total == 0 ? 0 : (total + itens - 1) / itens;
        return new Pagina<>(List.copyOf(fatia), new Paginacao(pagina, itens, total, paginas));
    }
}

package io.github.danhenriquex.brasilaberto.localidades.api;

import io.github.danhenriquex.brasilaberto.localidades.dominio.MunicipioResumido;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Uf;
import io.github.danhenriquex.brasilaberto.localidades.erros.EntradaInvalida;
import io.github.danhenriquex.brasilaberto.localidades.servico.ServicoLocalidades;
import jakarta.servlet.http.HttpServletRequest;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** GET /v1/ufs, /v1/ufs/{uf} e /v1/ufs/{uf}/municipios (US1). */
@RestController
public class UfsController {

    private final ServicoLocalidades servico;

    public UfsController(ServicoLocalidades servico) {
        this.servico = servico;
    }

    /** pagina e itens chegam como texto e são validados pelo domínio, para o detalhe citar o limite configurado. */
    static int inteiro(String nome, String valor, int padrao) {
        if (valor == null || valor.isBlank()) {
            return padrao;
        }
        try {
            return Integer.parseInt(valor.strip());
        } catch (NumberFormatException erro) {
            throw new EntradaInvalida(nome + " precisa ser um número inteiro, recebi '" + valor + "'");
        }
    }

    @GetMapping("/v1/ufs")
    public Resposta<List<Uf>> listarUfs(HttpServletRequest pedido) {
        return Resposta.de(servico.listarUfs(), pedido);
    }

    @GetMapping("/v1/ufs/{uf}")
    public Resposta<Uf> obterUf(@PathVariable String uf, HttpServletRequest pedido) {
        return Resposta.de(servico.obterUf(uf), pedido);
    }

    @GetMapping("/v1/ufs/{uf}/municipios")
    public Resposta<List<MunicipioResumido>> listarMunicipios(
            @PathVariable String uf,
            @RequestParam(required = false) String pagina,
            @RequestParam(required = false) String itens,
            HttpServletRequest pedido) {
        return Resposta.de(
                servico.listarMunicipios(uf, inteiro("pagina", pagina, 1), inteiro("itens", itens, 100)), pedido);
    }
}

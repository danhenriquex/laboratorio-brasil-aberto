package io.github.danhenriquex.brasilaberto.localidades.api;

import io.github.danhenriquex.brasilaberto.localidades.dominio.MunicipioResumido;
import io.github.danhenriquex.brasilaberto.localidades.dominio.Uf;
import io.github.danhenriquex.brasilaberto.localidades.erros.EntradaInvalida;
import io.github.danhenriquex.brasilaberto.localidades.servico.ServicoLocalidades;
import jakarta.servlet.http.HttpServletRequest;
import java.math.BigInteger;
import java.util.List;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

/** GET /v1/ufs, /v1/ufs/{uf} e /v1/ufs/{uf}/municipios (US1). */
@RestController
public class UfsController {

    private final ServicoLocalidades servico;

    public UfsController(ServicoLocalidades servico) {
        this.servico = servico;
    }

    private static final BigInteger LONG_MAX = BigInteger.valueOf(Long.MAX_VALUE);
    private static final BigInteger LONG_MIN = BigInteger.valueOf(Long.MIN_VALUE);

    /** Parâmetro repetido: vale o último valor, como no E1 (T045). */
    static String ultimo(HttpServletRequest pedido, String nome) {
        String[] valores = pedido.getParameterValues(nome);
        return valores == null || valores.length == 0 ? null : valores[valores.length - 1];
    }

    /**
     * pagina e itens chegam como texto e são validados pelo domínio, para o detalhe citar o limite configurado.
     * Lidos sem limite de tamanho (o contrato não limita pagina) e só então trazidos para long (T045).
     */
    static long inteiro(String nome, String valor, long padrao) {
        if (valor == null || valor.isBlank()) {
            return padrao;
        }
        BigInteger numero;
        try {
            numero = new BigInteger(valor.strip());
        } catch (NumberFormatException erro) {
            throw new EntradaInvalida(nome + " precisa ser um número inteiro, recebi '" + valor + "'");
        }
        return numero.max(LONG_MIN).min(LONG_MAX).longValue();
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
            HttpServletRequest pedido) {
        long pagina = inteiro("pagina", ultimo(pedido, "pagina"), 1);
        long itens = inteiro("itens", ultimo(pedido, "itens"), 100);
        return Resposta.de(servico.listarMunicipios(uf, pagina, itens, ultimo(pedido, "nome")), pedido);
    }
}

package io.github.danhenriquex.brasilaberto.localidades.dominio;

import io.github.danhenriquex.brasilaberto.localidades.erros.EntradaInvalida;
import io.github.danhenriquex.brasilaberto.localidades.erros.NaoEncontrado;
import java.util.Locale;
import java.util.regex.Pattern;

/** Validação de entrada antes de qualquer consulta ao IBGE (FR-012). Classes de caracteres ASCII. */
public final class Validacao {

    public static final int NOME_MIN = 2;
    public static final int NOME_MAX = 60;

    private static final Pattern SIGLA = Pattern.compile("[A-Za-z]{2}");
    private static final Pattern CODIGO_UF = Pattern.compile("[0-9]{2}");
    private static final Pattern CODIGO_MUNICIPIO = Pattern.compile("[0-9]{7}");

    private Validacao() {}

    /** Sigla (sem diferenciar maiúsculas) ou código de 2 dígitos → código da UF. */
    public static String resolverUf(String param) {
        String valor = param.strip();
        String codigo;
        if (SIGLA.matcher(valor).matches()) {
            codigo = UfsOficiais.SIGLA_PARA_CODIGO.get(valor.toUpperCase(Locale.ROOT));
        } else if (CODIGO_UF.matcher(valor).matches()) {
            codigo = UfsOficiais.CODIGO_PARA_SIGLA.containsKey(valor) ? valor : null;
        } else {
            throw new EntradaInvalida("UF inválida: use a sigla de 2 letras (ex.: RJ) ou o código de 2 dígitos (ex.: 33), recebi '" + param + "'");
        }
        if (codigo == null) {
            throw new NaoEncontrado("não existe UF '" + valor + "'");
        }
        return codigo;
    }

    public static String validarCodigoMunicipio(String codigo) {
        if (!CODIGO_MUNICIPIO.matcher(codigo).matches()) {
            throw new EntradaInvalida("código de município inválido: precisa ter exatamente 7 dígitos, recebi '" + codigo + "'");
        }
        return codigo;
    }

    public static void validarPaginacao(int pagina, int itens, int itensMax) {
        if (pagina < 1) {
            throw new EntradaInvalida("pagina precisa ser maior ou igual a 1, recebi " + pagina);
        }
        if (itens < 1 || itens > itensMax) {
            throw new EntradaInvalida("itens precisa estar entre 1 e " + itensMax + ", recebi " + itens);
        }
    }

    public static String validarNome(String nome) {
        String valor = nome.strip();
        if (valor.length() < NOME_MIN) {
            throw new EntradaInvalida("nome precisa ter pelo menos " + NOME_MIN + " caracteres, sem contar espaços nas pontas");
        }
        if (valor.length() > NOME_MAX) {
            throw new EntradaInvalida("nome pode ter no máximo " + NOME_MAX + " caracteres");
        }
        return valor;
    }
}

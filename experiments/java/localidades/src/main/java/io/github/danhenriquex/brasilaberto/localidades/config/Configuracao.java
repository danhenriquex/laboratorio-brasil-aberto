package io.github.danhenriquex.brasilaberto.localidades.config;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

/**
 * Configuração comum ao E1 e ao E4 (LOCALIDADES_*). Host e porta vão para server.address e server.port.
 * Valores inválidos impedem a partida (R10).
 *
 * <p>Prazo e validade ficam entre 1 ms e 10⁹ s (T049). Abaixo de 1 ms, o valor arredonda para zero e o
 * HttpClient recusa o prazo; acima de 10⁹ s (uns 31 anos), a validade não cabe no relógio monotônico em
 * nanossegundos, e o infinito deixaria a consulta ao IBGE sem prazo nenhum. Os limites ficam na validação
 * para que o erro saia no relatório do Spring (Property / Value / Reason), e não num stack trace.
 */
@Validated
@ConfigurationProperties("localidades")
public record Configuracao(
        @NotBlank @Pattern(regexp = "^https?://.+", message = "precisa começar com http:// ou https://") String ibgeUrl,
        @Positive @DecimalMin(value = "0.001", message = "precisa ser de pelo menos 0.001 (1 ms)")
        @DecimalMax(value = "1000000000", message = "precisa ser finito e de no máximo 1000000000 (10⁹ s)") double prazoFonteS,
        @Positive @DecimalMin(value = "0.001", message = "precisa ser de pelo menos 0.001 (1 ms)")
        @DecimalMax(value = "1000000000", message = "precisa ser finito e de no máximo 1000000000 (10⁹ s)") double validadeS,
        @Positive int itensMax) {

    public Configuracao {
        ibgeUrl = ibgeUrl == null ? null : ibgeUrl.strip().replaceAll("/+$", "");
    }
}

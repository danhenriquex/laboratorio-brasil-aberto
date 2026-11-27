package io.github.danhenriquex.brasilaberto.localidades.config;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

/**
 * Configuração comum ao E1 e ao E4 (LOCALIDADES_*). Host e porta vão para server.address e server.port.
 * Valores inválidos impedem a partida (R10).
 */
@Validated
@ConfigurationProperties("localidades")
public record Configuracao(
        @NotBlank @Pattern(regexp = "^https?://.+", message = "precisa começar com http:// ou https://") String ibgeUrl,
        @Positive double prazoFonteS,
        @Positive double validadeS,
        @Positive int itensMax) {

    public Configuracao {
        ibgeUrl = ibgeUrl == null ? null : ibgeUrl.strip().replaceAll("/+$", "");
    }
}

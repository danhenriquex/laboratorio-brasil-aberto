package io.github.danhenriquex.brasilaberto.localidades.config;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.ConfigDataApplicationContextInitializer;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.boot.validation.autoconfigure.ValidationAutoConfiguration;
import org.springframework.boot.autoconfigure.AutoConfigurations;
import org.springframework.context.annotation.Configuration;

/** Mesmos padrões e regras do R14 do E1, lidos pelas variáveis LOCALIDADES_* (mapeadas no application.properties). */
class ConfiguracaoTest {

    @Configuration
    @EnableConfigurationProperties(Configuracao.class)
    static class Contexto {}

    private final ApplicationContextRunner runner = new ApplicationContextRunner()
            .withInitializer(new ConfigDataApplicationContextInitializer())
            .withConfiguration(AutoConfigurations.of(ValidationAutoConfiguration.class))
            .withUserConfiguration(Contexto.class);

    @Test
    void padroes() {
        runner.run(ctx -> {
            var c = ctx.getBean(Configuracao.class);
            assertThat(c.ibgeUrl()).isEqualTo("https://servicodados.ibge.gov.br/api/v1/localidades");
            assertThat(c.prazoFonteS()).isEqualTo(10.0);
            assertThat(c.validadeS()).isEqualTo(86400.0);
            assertThat(c.itensMax()).isEqualTo(500);
            assertThat(ctx.getEnvironment().getProperty("server.address")).isEqualTo("127.0.0.1");
            assertThat(ctx.getEnvironment().getProperty("server.port")).isEqualTo("8000");
        });
    }

    @Test
    void leituraDasVariaveisLocalidades() {
        runner.withSystemProperties(
                        "LOCALIDADES_IBGE_URL=http://127.0.0.1:8099/api/v1/localidades/",
                        "LOCALIDADES_PRAZO_FONTE_S=1.5",
                        "LOCALIDADES_VALIDADE_S=2",
                        "LOCALIDADES_ITENS_MAX=50",
                        "LOCALIDADES_PORTA=8090",
                        "LOCALIDADES_HOST=0.0.0.0")
                .run(ctx -> {
                    var c = ctx.getBean(Configuracao.class);
                    assertThat(c.ibgeUrl()).isEqualTo("http://127.0.0.1:8099/api/v1/localidades");
                    assertThat(c.prazoFonteS()).isEqualTo(1.5);
                    assertThat(c.validadeS()).isEqualTo(2.0);
                    assertThat(c.itensMax()).isEqualTo(50);
                    assertThat(ctx.getEnvironment().getProperty("server.port")).isEqualTo("8090");
                    assertThat(ctx.getEnvironment().getProperty("server.address")).isEqualTo("0.0.0.0");
                });
    }

    @ParameterizedTest
    @CsvSource({
        "LOCALIDADES_PRAZO_FONTE_S,abc", "LOCALIDADES_PRAZO_FONTE_S,0", "LOCALIDADES_PRAZO_FONTE_S,-1",
        "LOCALIDADES_VALIDADE_S,x", "LOCALIDADES_ITENS_MAX,0", "LOCALIDADES_IBGE_URL,ftp://ibge"
    })
    void valoresInvalidosImpedemAPartida(String variavel, String valor) {
        runner.withSystemProperties(variavel + "=" + valor).run(ctx -> assertThat(ctx).hasFailed());
    }
}

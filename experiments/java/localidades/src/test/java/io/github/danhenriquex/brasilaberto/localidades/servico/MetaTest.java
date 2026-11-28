package io.github.danhenriquex.brasilaberto.localidades.servico;

import static org.assertj.core.api.Assertions.assertThat;

import io.github.danhenriquex.brasilaberto.localidades.dominio.Meta;
import java.time.Instant;
import org.junit.jupiter.api.Test;

class MetaTest {

    @Test
    void coletadoEmSempreComMilissegundosEZ() {
        assertThat(Meta.de("u", Instant.parse("2026-11-26T12:00:00Z"), false).coletadoEm()).isEqualTo("2026-11-26T12:00:00.000Z");
        assertThat(Meta.de("u", Instant.parse("2026-11-26T12:00:00.123456Z"), false).coletadoEm()).isEqualTo("2026-11-26T12:00:00.123Z");
    }

    @Test
    void procedenciaFixa() {
        var meta = Meta.de("https://ibge/estados", Instant.EPOCH, true);
        assertThat(meta.fonte()).isEqualTo("IBGE — API de localidades");
        assertThat(meta.urlDocumentacao()).isEqualTo("https://servicodados.ibge.gov.br/api/docs/localidades");
        assertThat(meta.urlFonte()).isEqualTo("https://ibge/estados");
        assertThat(meta.desatualizado()).isTrue();
    }
}

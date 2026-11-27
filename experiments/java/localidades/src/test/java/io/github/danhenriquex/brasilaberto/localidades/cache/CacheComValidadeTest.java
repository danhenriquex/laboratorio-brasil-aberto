package io.github.danhenriquex.brasilaberto.localidades.cache;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import io.github.danhenriquex.brasilaberto.localidades.apoio.RelogioFalso;
import io.github.danhenriquex.brasilaberto.localidades.erros.FonteIndisponivel;
import io.github.danhenriquex.brasilaberto.localidades.erros.FonteLenta;
import io.github.danhenriquex.brasilaberto.localidades.erros.NaoEncontrado;
import io.github.danhenriquex.brasilaberto.localidades.erros.RespostaInesperadaDaFonte;
import io.github.danhenriquex.brasilaberto.localidades.fonte.RespostaFonte;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Callable;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/** Mesmos casos do test_cache.py do E1, incluindo a falha compartilhada (T050 do E1). */
class CacheComValidadeTest {

    private final RelogioFalso relogio = new RelogioFalso();
    private final CacheComValidade cache = new CacheComValidade(relogio, relogio, Duration.ofSeconds(60));

    /** Fonte falsa que conta as chamadas e pode demorar ou falhar. */
    static final class BuscarFalso implements Supplier<RespostaFonte<String>> {
        final AtomicInteger chamadas = new AtomicInteger();
        volatile RuntimeException erro;
        volatile String valor = "dados-1";
        volatile long esperaMs;

        @Override
        public RespostaFonte<String> get() {
            chamadas.incrementAndGet();
            if (esperaMs > 0) {
                try {
                    Thread.sleep(esperaMs);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
            if (erro != null) {
                throw erro;
            }
            return new RespostaFonte<>(valor, "https://ibge/recurso");
        }
    }

    @Test
    void entradaValidaAtendeSemConsultar() {
        var buscar = new BuscarFalso();
        var primeira = cache.obter("k", buscar);
        relogio.avancar(Duration.ofSeconds(59));
        var segunda = cache.obter("k", buscar);
        assertThat(buscar.chamadas).hasValue(1);
        assertThat(primeira.resultado()).isEqualTo("falta");
        assertThat(segunda.resultado()).isEqualTo("acerto");
        assertThat(segunda.coletadoEm()).isEqualTo(primeira.coletadoEm());
        assertThat(segunda.dados()).isEqualTo("dados-1");
        assertThat(segunda.urlFonte()).isEqualTo("https://ibge/recurso");
        assertThat(segunda.desatualizado()).isFalse();
    }

    @Test
    void entradaVencidaRenova() {
        var buscar = new BuscarFalso();
        var primeira = cache.obter("k", buscar);
        relogio.avancar(Duration.ofSeconds(61));
        buscar.valor = "dados-2";
        var segunda = cache.obter("k", buscar);
        assertThat(buscar.chamadas).hasValue(2);
        assertThat(segunda.dados()).isEqualTo("dados-2");
        assertThat(segunda.resultado()).isEqualTo("falta");
        assertThat(segunda.coletadoEm()).isAfter(primeira.coletadoEm());
    }

    @ParameterizedTest
    @ValueSource(strings = {"indisponivel", "lenta", "inesperada"})
    void vencidaComFalhaServeCopiaDesatualizada(String tipo) {
        var buscar = new BuscarFalso();
        var primeira = cache.obter("k", buscar);
        relogio.avancar(Duration.ofHours(1));
        buscar.erro = switch (tipo) {
            case "indisponivel" -> new FonteIndisponivel("x");
            case "lenta" -> new FonteLenta("x");
            default -> new RespostaInesperadaDaFonte("x");
        };
        var segunda = cache.obter("k", buscar);
        var terceira = cache.obter("k", buscar); // continua vencida: tenta a fonte de novo
        assertThat(segunda.desatualizado()).isTrue();
        assertThat(segunda.resultado()).isEqualTo("desatualizado");
        assertThat(segunda.coletadoEm()).isEqualTo(primeira.coletadoEm());
        assertThat(segunda.dados()).isEqualTo("dados-1");
        assertThat(terceira.desatualizado()).isTrue();
        assertThat(buscar.chamadas).hasValue(3);
    }

    @Test
    void ausenteComFalhaPropaga() {
        var buscar = new BuscarFalso();
        buscar.erro = new FonteLenta("lenta");
        assertThatThrownBy(() -> cache.obter("k", buscar)).isInstanceOf(FonteLenta.class);
    }

    @Test
    void naoEncontradoEErrosNaoEntramNaCopia() {
        var buscar = new BuscarFalso();
        buscar.erro = new NaoEncontrado("não existe");
        assertThatThrownBy(() -> cache.obter("k", buscar)).isInstanceOf(NaoEncontrado.class);
        assertThatThrownBy(() -> cache.obter("k", buscar)).isInstanceOf(NaoEncontrado.class);
        buscar.erro = new FonteIndisponivel("fora");
        assertThatThrownBy(() -> cache.obter("k", buscar)).isInstanceOf(FonteIndisponivel.class);
        buscar.erro = null;
        assertThat(cache.obter("k", buscar).resultado()).isEqualTo("falta");
        assertThat(buscar.chamadas).hasValue(4);
    }

    @Test
    void naoEncontradoComCopiaVencidaPropaga() {
        var buscar = new BuscarFalso();
        cache.obter("k", buscar);
        relogio.avancar(Duration.ofSeconds(61));
        buscar.erro = new NaoEncontrado("deixou de existir");
        assertThatThrownBy(() -> cache.obter("k", buscar)).isInstanceOf(NaoEncontrado.class);
    }

    private <T> List<Object> simultaneos(int n, Callable<T> tarefa) throws Exception {
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            List<Future<T>> futuros = new ArrayList<>();
            for (int i = 0; i < n; i++) {
                futuros.add(executor.submit(tarefa));
            }
            List<Object> resultados = new ArrayList<>();
            for (var f : futuros) {
                try {
                    resultados.add(f.get());
                } catch (java.util.concurrent.ExecutionException e) {
                    resultados.add(e.getCause());
                }
            }
            return resultados;
        }
    }

    @Test
    void consultaUnicaPorChave() throws Exception {
        var buscar = new BuscarFalso();
        buscar.esperaMs = 100;
        var resultados = simultaneos(10, () -> cache.obter("k", buscar));
        var outra = cache.obter("outra", buscar);
        assertThat(buscar.chamadas).hasValue(2); // uma para "k" e uma para "outra"
        assertThat(resultados).map(r -> ((CacheComValidade.Entrada<?>) r).resultado())
                .containsExactlyInAnyOrder("falta", "acerto", "acerto", "acerto", "acerto", "acerto", "acerto", "acerto", "acerto", "acerto");
        assertThat(outra.resultado()).isEqualTo("falta");
    }

    @Test
    void falhaDaConsultaEmAndamentoECompartilhada() throws Exception {
        var buscar = new BuscarFalso();
        buscar.esperaMs = 150;
        buscar.erro = new FonteLenta("lenta");
        long inicio = System.nanoTime();
        var resultados = simultaneos(10, () -> cache.obter("k", buscar));
        long duracaoMs = (System.nanoTime() - inicio) / 1_000_000;
        assertThat(buscar.chamadas).hasValue(1); // a fonte com problema recebe uma única consulta
        assertThat(resultados).allMatch(r -> r instanceof FonteLenta);
        assertThat(duracaoMs).isLessThan(300); // ninguém espera em fila por mais de uma consulta
    }

    @Test
    void copiaVencidaServidaATodosQueEsperavam() throws Exception {
        var buscar = new BuscarFalso();
        cache.obter("k", buscar);
        relogio.avancar(Duration.ofSeconds(61));
        buscar.esperaMs = 100;
        buscar.erro = new FonteIndisponivel("fora");
        var resultados = simultaneos(5, () -> cache.obter("k", buscar));
        assertThat(buscar.chamadas).hasValue(2);
        assertThat(resultados).allMatch(r -> r instanceof CacheComValidade.Entrada<?> e && e.desatualizado() && e.resultado().equals("desatualizado"));
    }
}

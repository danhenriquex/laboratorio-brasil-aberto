package io.github.danhenriquex.brasilaberto.localidades.cache;

import io.github.danhenriquex.brasilaberto.localidades.erros.ErroDeFonte;
import io.github.danhenriquex.brasilaberto.localidades.fonte.RespostaFonte;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.LongSupplier;
import java.util.function.Supplier;

/**
 * Cópia guardada com validade, consulta única por chave e cópia vencida quando a fonte falha (R5 do E4).
 *
 * <p>Pedidos simultâneos pelo mesmo recurso aguardam a <b>mesma</b> consulta e recebem o mesmo resultado,
 * inclusive a falha (lição da T050 do E1): ninguém espera em fila por mais de um prazo, e a fonte com
 * problema recebe uma única consulta. "Não encontrado" e erros nunca entram na cópia.
 */
public class CacheComValidade {

    /** O que um pedido recebe: dados, procedência e o uso da cópia (acerto, falta ou desatualizado). */
    public record Entrada<T>(T dados, String urlFonte, Instant coletadoEm, boolean desatualizado, String resultado) {

        Entrada<T> comoAcerto() {
            return new Entrada<>(dados, urlFonte, coletadoEm, false, "acerto");
        }
    }

    private record Guardada(Object dados, String urlFonte, Instant coletadoEm, long expiraEmNanos) {}

    private final Clock relogio;
    private final LongSupplier monotonico;
    private final long validadeNanos;
    private final ConcurrentHashMap<String, Guardada> guardadas = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, CompletableFuture<Entrada<?>>> emAndamento = new ConcurrentHashMap<>();

    public CacheComValidade(Clock relogio, LongSupplier monotonico, Duration validade) {
        this.relogio = relogio;
        this.monotonico = monotonico;
        this.validadeNanos = validade.toNanos();
    }

    private Guardada valida(String chave) {
        Guardada guardada = guardadas.get(chave);
        return guardada != null && monotonico.getAsLong() - guardada.expiraEmNanos() < 0 ? guardada : null;
    }

    @SuppressWarnings("unchecked")
    private static <T> Entrada<T> de(Guardada g, boolean desatualizado, String resultado) {
        return new Entrada<>((T) g.dados(), g.urlFonte(), g.coletadoEm(), desatualizado, resultado);
    }

    @SuppressWarnings("unchecked")
    public <T> Entrada<T> obter(String chave, Supplier<RespostaFonte<T>> buscar) {
        Guardada guardada = valida(chave);
        if (guardada != null) {
            return de(guardada, false, "acerto");
        }

        CompletableFuture<Entrada<?>> nova = new CompletableFuture<>();
        CompletableFuture<Entrada<?>> existente = emAndamento.putIfAbsent(chave, nova);
        boolean iniciou = existente == null;
        CompletableFuture<Entrada<?>> consulta = iniciou ? nova : existente;

        if (iniciou) {
            try {
                Guardada agora = valida(chave); // outra consulta pode ter terminado entre a leitura e o registro
                if (agora != null) {
                    nova.complete(de(agora, false, "acerto"));
                } else {
                    Instant coletadoEm = relogio.instant();
                    RespostaFonte<T> resposta = buscar.get();
                    guardadas.put(chave, new Guardada(resposta.dados(), resposta.urlFonte(), coletadoEm,
                            monotonico.getAsLong() + validadeNanos));
                    nova.complete(new Entrada<>(resposta.dados(), resposta.urlFonte(), coletadoEm, false, "falta"));
                }
            } catch (RuntimeException erro) {
                nova.completeExceptionally(erro);
            } finally {
                emAndamento.remove(chave, nova);
            }
        }

        try {
            Entrada<T> entrada = (Entrada<T>) consulta.join();
            return iniciou ? entrada : entrada.comoAcerto();
        } catch (CompletionException embrulhada) {
            Throwable causa = embrulhada.getCause();
            if (causa instanceof ErroDeFonte) {
                Guardada vencida = guardadas.get(chave);
                if (vencida != null) {
                    return de(vencida, true, "desatualizado");
                }
            }
            if (causa instanceof RuntimeException erro) {
                throw erro;
            }
            throw embrulhada;
        }
    }

    /** Esvazia a cópia guardada (usado pelos testes, que reaproveitam o contexto do Spring). */
    public void limpar() {
        guardadas.clear();
    }
}

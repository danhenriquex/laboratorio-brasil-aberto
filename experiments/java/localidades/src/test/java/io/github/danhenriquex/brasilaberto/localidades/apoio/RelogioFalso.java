package io.github.danhenriquex.brasilaberto.localidades.apoio;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.function.LongSupplier;

/** Relógio de parede e relógio monotônico controlados pelo teste. */
public final class RelogioFalso extends Clock implements LongSupplier {

    private Instant agora = Instant.parse("2026-11-26T12:00:00.123Z");
    private long nanos = 1_000_000_000_000L;

    public void avancar(Duration duracao) {
        agora = agora.plus(duracao);
        nanos += duracao.toNanos();
    }

    @Override
    public Instant instant() {
        return agora;
    }

    @Override
    public long getAsLong() {
        return nanos;
    }

    @Override
    public ZoneId getZone() {
        return ZoneOffset.UTC;
    }

    @Override
    public Clock withZone(ZoneId zone) {
        return this;
    }
}

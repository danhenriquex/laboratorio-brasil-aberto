"""Métricas no formato do Prometheus, com os nomes do contrato (research.md, R12)."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest

_FAIXAS_FONTE_S = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


class Metricas:
    """Um registro por app, para não haver séries duplicadas entre testes."""

    def __init__(self) -> None:
        self.registro = CollectorRegistry()
        self.pedidos = Counter(
            "localidades_pedidos", "Pedidos atendidos, por modelo de rota e status.", ["rota", "status"], registry=self.registro
        )
        self.erros = Counter("localidades_erros", "Erros devolvidos, por tipo de problema.", ["tipo"], registry=self.registro)
        self.cache = Counter(
            "localidades_cache", "Uso da cópia guardada: acerto, falta ou desatualizado.", ["resultado"], registry=self.registro
        )
        self.fonte = Histogram(
            "localidades_fonte_duracao_segundos",
            "Duração das consultas ao IBGE, por recurso.",
            ["recurso"],
            buckets=_FAIXAS_FONTE_S,
            registry=self.registro,
        )

    def observar_fonte(self, recurso: str, segundos: float) -> None:
        self.fonte.labels(recurso=recurso).observe(segundos)

    def registrar_pedido(self, rota: str, status: int, tipo_erro: str | None, cache: str | None) -> None:
        self.pedidos.labels(rota=rota, status=str(status)).inc()
        if tipo_erro:
            self.erros.labels(tipo=tipo_erro).inc()
        if cache:
            self.cache.labels(resultado=cache).inc()

    def exportar(self) -> tuple[bytes, str]:
        return generate_latest(self.registro), CONTENT_TYPE_LATEST

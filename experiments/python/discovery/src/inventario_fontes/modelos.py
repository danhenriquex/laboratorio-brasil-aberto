"""Entidades do inventário (ver specs/001-inventario-fontes/data-model.md).

Todas são imutáveis. Nenhuma entidade tem atributo para guardar valores vindos
do corpo de uma resposta (FR-015): a amostra guarda só caminhos e tipos.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class Grau(StrEnum):
    CONFIRMADO = "confirmado"
    PARCIAL = "parcial"
    NAO_VERIFICADO = "nao_verificado"


class Situacao(StrEnum):
    RESPONDEU = "respondeu"
    FALHOU = "falhou"
    SEM_TESTE = "sem_teste"
    NAO_EXECUTADA = "nao_executada"


class Causa(StrEnum):
    TEMPO_ESGOTADO = "tempo_esgotado"
    INDISPONIVEL = "indisponivel"
    ERRO_TLS = "erro_tls"
    EXIGE_AUTENTICACAO = "exige_autenticacao"
    ACESSO_NEGADO = "acesso_negado"
    LIMITE_REQUISICOES = "limite_requisicoes"
    ERRO_FONTE = "erro_fonte"
    ERRO_REQUISICAO = "erro_requisicao"
    RESPOSTA_INVALIDA = "resposta_invalida"


class Formato(StrEnum):
    JSON = "json"
    CSV = "csv"
    XML = "xml"
    HTML = "html"
    TEXTO = "texto"
    VAZIO = "vazio"
    OUTRO = "outro"


class Auth(StrEnum):
    EXIGE = "exige"
    NAO_EXIGE = "nao_exige"
    INDETERMINADO = "indeterminado"


class TipoCampo(StrEnum):
    TEXTO = "texto"
    INTEIRO = "inteiro"
    DECIMAL = "decimal"
    BOOLEANO = "booleano"
    NULO = "nulo"
    DATA = "data"
    OBJETO = "objeto"
    LISTA = "lista"


class Aspecto(StrEnum):
    AUTENTICACAO = "autenticacao"
    DISPONIBILIDADE = "disponibilidade"
    FORMATO = "formato"


@dataclass(frozen=True)
class Configuracao:
    intervalo_s: float = 2.0
    tempo_limite_s: float = 15.0
    teto_bytes: int = 1_048_576
    max_redirecionamentos: int = 5

    def __post_init__(self) -> None:
        if self.intervalo_s < 1:
            raise ValueError("o intervalo entre consultas deve ser de pelo menos 1 segundo")
        if not 1 <= self.tempo_limite_s <= 60:
            raise ValueError("o tempo limite deve estar entre 1 e 60 segundos")
        if self.teto_bytes < 1:
            raise ValueError("o teto de leitura deve ser positivo")
        if self.max_redirecionamentos < 0:
            raise ValueError("o máximo de redirecionamentos não pode ser negativo")


@dataclass(frozen=True)
class Fonte:
    id: str
    nome: str
    dominio: str
    url_documentacao: str | None
    url_teste: str | None
    tipos_dado: tuple[str, ...]
    hipotese_acesso: str
    auth_esperada: str
    verificacao: Grau
    rodada: int
    notas: str | None = None

    @property
    def hipotese_auth(self) -> Auth:
        """`nao_exige` se `auth_esperada` começa com "nenhuma"; senão `exige`."""
        if self.auth_esperada.strip().casefold().startswith("nenhuma"):
            return Auth.NAO_EXIGE
        return Auth.EXIGE


@dataclass(frozen=True)
class Catalogo:
    caminho: str
    schema_version: int
    fontes: tuple[Fonte, ...]


@dataclass(frozen=True)
class Redirecionamento:
    status: int
    url: str


@dataclass(frozen=True)
class CampoAmostra:
    """Só caminho e tipos: não há atributo para valor, exemplo ou enumeração."""

    caminho: str
    tipos: tuple[TipoCampo, ...]


@dataclass(frozen=True)
class EstruturaAmostra:
    registros_inspecionados: int
    caminho_registros: str | None
    campos: tuple[CampoAmostra, ...]
    vazia: bool = False
    indisponivel_motivo: str | None = None


@dataclass(frozen=True)
class Divergencia:
    aspecto: Aspecto
    hipotese: str
    observado: str


@dataclass(frozen=True)
class ResultadoSondagem:
    fonte_id: str
    nome: str
    dominio: str
    url_documentacao: str | None
    rodada: int
    hipotese_acesso: str
    auth_esperada: str
    verificacao_catalogo: Grau
    situacao: Situacao
    verificacao_sugerida: Grau | None = None
    justificativa_verificacao: str = ""
    causa: Causa | None = None
    detalhe_causa: str | None = None
    url_teste: str | None = None
    url_final: str | None = None
    redirecionamentos: tuple[Redirecionamento, ...] = ()
    status_http: int | None = None
    latencia_ms: float | None = None
    coletado_em: datetime | None = None
    formato_declarado: str | None = None
    formato_detectado: Formato | None = None
    formato_divergente: bool = False
    tamanho_bytes: int | None = None
    tamanho_declarado_bytes: int | None = None
    truncada: bool = False
    auth_observada: Auth = Auth.INDETERMINADO
    indicio_autenticacao: str | None = None
    retry_after: str | None = None
    amostra: EstruturaAmostra | None = None
    divergencias: tuple[Divergencia, ...] = ()

    def __post_init__(self) -> None:
        if (self.situacao is Situacao.FALHOU) != (self.causa is not None):
            raise ValueError("situacao 'falhou' exige causa, e só ela pode ter causa")

    @classmethod
    def base(cls, fonte: Fonte, situacao: Situacao, **campos) -> ResultadoSondagem:
        return cls(
            fonte_id=fonte.id,
            nome=fonte.nome,
            dominio=fonte.dominio,
            url_documentacao=fonte.url_documentacao,
            rodada=fonte.rodada,
            hipotese_acesso=fonte.hipotese_acesso,
            auth_esperada=fonte.auth_esperada,
            verificacao_catalogo=fonte.verificacao,
            url_teste=fonte.url_teste,
            situacao=situacao,
            **campos,
        )


@dataclass(frozen=True)
class Resumo:
    total: int
    responderam: int
    falharam: int
    falhas_por_causa: dict[str, int]
    sem_teste: int
    nao_executadas: int
    com_divergencia: int

    @classmethod
    def de_resultados(cls, resultados: tuple[ResultadoSondagem, ...] | list[ResultadoSondagem]) -> Resumo:
        por_situacao = Counter(r.situacao for r in resultados)
        causas = Counter(r.causa.value for r in resultados if r.causa is not None)
        resumo = cls(
            total=len(resultados),
            responderam=por_situacao[Situacao.RESPONDEU],
            falharam=por_situacao[Situacao.FALHOU],
            falhas_por_causa=dict(sorted(causas.items())),
            sem_teste=por_situacao[Situacao.SEM_TESTE],
            nao_executadas=por_situacao[Situacao.NAO_EXECUTADA],
            com_divergencia=sum(1 for r in resultados if r.divergencias),
        )
        assert resumo.total == resumo.responderam + resumo.falharam + resumo.sem_teste + resumo.nao_executadas
        return resumo


@dataclass(frozen=True)
class Execucao:
    ferramenta: str
    catalogo_caminho: str
    catalogo_schema_version: int
    iniciada_em: datetime
    finalizada_em: datetime
    interrompida: bool
    configuracao: Configuracao
    aviso: str
    resumo: Resumo
    resultados: tuple[ResultadoSondagem, ...]
    filtro_rodadas: tuple[int, ...] = ()
    filtro_fontes: tuple[str, ...] = ()
    versao_relatorio: int = field(default=1)

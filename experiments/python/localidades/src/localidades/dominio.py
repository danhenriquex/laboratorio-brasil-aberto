"""Entidades e regras do domínio (data-model.md). Não importa FastAPI nem httpx."""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from localidades.erros import EntradaInvalida, NaoEncontrado

# Código e sigla das 27 UFs, usados só para validar e resolver a entrada (research.md, R1).
# Nomes e regiões vêm sempre do IBGE.
UFS_OFICIAIS: dict[str, str] = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO",
    "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA",
    "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS",
    "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}  # fmt: skip
_CODIGO_POR_SIGLA = {sigla: codigo for codigo, sigla in UFS_OFICIAIS.items()}

# re.ASCII: \d e [A-Za-z] não aceitam dígitos ou letras de outros alfabetos.
_SIGLA = re.compile(r"[A-Za-z]{2}", re.ASCII)
_CODIGO_UF = re.compile(r"[0-9]{2}", re.ASCII)
_CODIGO_MUNICIPIO = re.compile(r"[0-9]{7}", re.ASCII)

NOME_MIN, NOME_MAX = 2, 60


@dataclass(frozen=True)
class Regiao:
    codigo: str
    sigla: str
    nome: str


@dataclass(frozen=True)
class Uf:
    codigo: str
    sigla: str
    nome: str
    regiao: Regiao


@dataclass(frozen=True)
class UfResumida:
    codigo: str
    sigla: str
    nome: str


@dataclass(frozen=True)
class RegiaoImediata:
    codigo: str
    nome: str


@dataclass(frozen=True)
class RegiaoIntermediaria:
    codigo: str
    nome: str


@dataclass(frozen=True)
class MunicipioResumido:
    codigo: str
    nome: str


@dataclass(frozen=True)
class Municipio:
    codigo: str
    nome: str
    uf: UfResumida
    regiao_imediata: RegiaoImediata
    regiao_intermediaria: RegiaoIntermediaria


T = TypeVar("T")


@dataclass(frozen=True)
class Pagina(Generic[T]):
    itens: list[T]
    pagina: int
    tamanho: int
    total: int
    paginas: int


def dobrar(texto: str) -> str:
    """NFKD, sem marcas diacríticas (categoria Mn) e casefold (research.md, R8)."""
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if unicodedata.category(c) != "Mn").casefold()


def chave_ordenacao(item) -> tuple[str, str]:
    return (dobrar(item.nome), item.codigo)


def ordenar(itens: Iterable[T]) -> list[T]:
    return sorted(itens, key=chave_ordenacao)


def filtrar_por_nome(itens: Iterable[MunicipioResumido], nome: str) -> list[MunicipioResumido]:
    alvo = dobrar(nome.strip())
    return [item for item in itens if alvo in dobrar(item.nome)]


def paginar(colecao: Sequence[T], pagina: int, itens: int) -> Pagina[T]:
    """Fatia já filtrada e ordenada. Página além do fim devolve lista vazia com o total correto."""
    lista = list(colecao)
    total = len(lista)
    inicio = (pagina - 1) * itens
    return Pagina(
        itens=lista[inicio : inicio + itens],
        pagina=pagina,
        tamanho=itens,
        total=total,
        paginas=math.ceil(total / itens) if total else 0,
    )


def resolver_uf(param: str) -> str:
    """Sigla (sem diferenciar maiúsculas) ou código de 2 dígitos → código da UF."""
    valor = param.strip()
    if _SIGLA.fullmatch(valor):
        codigo = _CODIGO_POR_SIGLA.get(valor.upper())
    elif _CODIGO_UF.fullmatch(valor):
        codigo = valor if valor in UFS_OFICIAIS else None
    else:
        raise EntradaInvalida(f"UF inválida: use a sigla de 2 letras (ex.: RJ) ou o código de 2 dígitos (ex.: 33), recebi {param!r}")
    if codigo is None:
        raise NaoEncontrado(f"não existe UF {valor!r}")
    return codigo


def validar_codigo_municipio(codigo: str) -> str:
    if not _CODIGO_MUNICIPIO.fullmatch(codigo):
        raise EntradaInvalida(f"código de município inválido: precisa ter exatamente 7 dígitos, recebi {codigo!r}")
    return codigo


def validar_paginacao(pagina: int, itens: int, itens_max: int) -> None:
    if pagina < 1:
        raise EntradaInvalida(f"pagina precisa ser maior ou igual a 1, recebi {pagina}")
    if not 1 <= itens <= itens_max:
        raise EntradaInvalida(f"itens precisa estar entre 1 e {itens_max}, recebi {itens}")


def validar_nome(nome: str) -> str:
    valor = nome.strip()
    if len(valor) < NOME_MIN:
        raise EntradaInvalida(f"nome precisa ter pelo menos {NOME_MIN} caracteres, sem contar espaços nas pontas")
    if len(valor) > NOME_MAX:
        raise EntradaInvalida(f"nome pode ter no máximo {NOME_MAX} caracteres")
    return valor

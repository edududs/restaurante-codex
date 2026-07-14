"""Pessoas — os NPCs do restaurante, com personalidade, status e evolução.

CODEX: estado imutável + fail-fast + evolução por função pura.
    A Pessoa é um snapshot congelado; ela não se muta. Trabalhar produz uma NOVA
    Pessoa (mais cansada, mais experiente) via `aplicar_conclusao`. Stats fora de
    0–100 falham na construção — estado ilegal não nasce.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum

from restaurante.dominio.cardapio import Estacao
from restaurante.dominio.erros import ErroDeDominio

_MIN, _MAX = 0, 100
_CUSTO_ENERGIA = 8
_CUSTO_ENERGIA_EVENTO = 4
_GANHO_XP = 15
_XP_POR_NIVEL = 100


class AtributoInvalido(ErroDeDominio):
    """Um atributo de pessoa (0–100) foi construído fora do intervalo válido."""


class Humor(Enum):
    """Estado de espírito do NPC — deriva da energia e realimenta as situações."""

    INSPIRADO = "inspirado"
    NEUTRO = "neutro"
    CANSADO = "cansado"
    ESTRESSADO = "estressado"


def _validar(nome: str, valor: int) -> int:
    if not _MIN <= valor <= _MAX:
        raise AtributoInvalido(f"{nome} deve estar em 0–100, veio {valor}.")
    return valor


def _sem_experiencia() -> dict[Estacao, int]:
    """Factory tipada para o XP inicial vazio (mantém o pyright strict feliz)."""
    return {}


@dataclass(frozen=True, slots=True)
class Personalidade:
    """Traços que enviesam quais beats um NPC vive (0–100 cada)."""

    foco: int
    sociavel: int
    disciplina: int
    criatividade: int

    def __post_init__(self) -> None:
        for nome in ("foco", "sociavel", "disciplina", "criatividade"):
            _validar(nome, getattr(self, nome))


@dataclass(frozen=True, slots=True)
class Pessoa:
    """Um NPC: quem é, no que é bom, como está agora, e o que já aprendeu."""

    id: str
    nome: str
    personalidade: Personalidade
    skills: dict[Estacao, int]
    energia: int = 100
    experiencia: dict[Estacao, int] = field(default_factory=_sem_experiencia)
    humor: Humor = Humor.NEUTRO

    def __post_init__(self) -> None:
        _validar("energia", self.energia)
        for est, val in self.skills.items():
            _validar(f"skill[{est.value}]", val)

    def skill_em(self, estacao: Estacao) -> int:
        """Proficiência (0–100) na estação; 20 como piso para estação desconhecida."""
        return self.skills.get(estacao, 20)

    def nivel_em(self, estacao: Estacao) -> int:
        """Nível derivado da experiência acumulada naquela estação."""
        return nivel(self.experiencia.get(estacao, 0))


def nivel(xp: int) -> int:
    """Converte XP acumulado em nível (1 nível a cada 100 XP)."""
    return xp // _XP_POR_NIVEL


def _humor_por_energia(energia: int, *, houve_evento: bool) -> Humor:
    if houve_evento and energia < 60:  # noqa: PLR2004
        return Humor.ESTRESSADO
    if energia >= 70:  # noqa: PLR2004
        return Humor.INSPIRADO
    if energia >= 40:  # noqa: PLR2004
        return Humor.NEUTRO
    return Humor.CANSADO


def aplicar_conclusao(pessoa: Pessoa, estacao: Estacao, *, houve_evento: bool) -> Pessoa:
    """Devolve uma nova Pessoa após concluir uma tarefa: gasta energia, ganha XP, muda humor.

    CODEX: evolução como função pura — a mesma entrada produz sempre a mesma saída, e a
    Pessoa original nunca é mutada (facilita testar a progressão do NPC ao longo do turno).
    """
    custo = _CUSTO_ENERGIA + (_CUSTO_ENERGIA_EVENTO if houve_evento else 0)
    nova_energia = max(_MIN, pessoa.energia - custo)
    nova_xp = dict(pessoa.experiencia)
    nova_xp[estacao] = nova_xp.get(estacao, 0) + _GANHO_XP
    return replace(
        pessoa,
        energia=nova_energia,
        experiencia=nova_xp,
        humor=_humor_por_energia(nova_energia, houve_evento=houve_evento),
    )

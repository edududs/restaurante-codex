"""Modelo de tempo — como a duração de uma tarefa EMERGE dos 4 fatores + os beats.

CODEX: Mechanism, not Policy + função pura. Este é o mecanismo de cálculo: dado o estado
    da pessoa, o item e a lista de beats (produzida pela política de situações), combina
    tudo numa duração. Ele não decide *quais* beats existem — só soma. Retorna o breakdown
    completo para o Rich mostrar o "porquê" de cada número.
"""

from __future__ import annotations

from dataclasses import dataclass

from restaurante.dominio.beats import Beat, TipoBeat
from restaurante.dominio.cardapio import ItemCardapio
from restaurante.dominio.pessoas import Pessoa

_PISO_SEGUNDOS = 0.3


@dataclass(frozen=True, slots=True)
class DuracaoTarefa:
    """O resultado do cálculo, com cada fator exposto (transparência para o Rich)."""

    base: float
    mult_skill: float
    mult_fadiga: float
    mult_xp: float
    soma_beats: float
    total: float
    beats: tuple[Beat, ...]

    @property
    def houve_evento(self) -> bool:
        """True se algum beat foi um EVENTO externo (queimou, equipamento falhou…)."""
        return any(b.tipo is TipoBeat.EVENTO for b in self.beats)


def _mult_skill(skill: int) -> float:
    # skill 0 → 1.3× (lento); skill 100 → 0.7× (rápido).
    return 1.3 - 0.6 * (skill / 100)


def _mult_fadiga(energia: int) -> float:
    # energia cheia → 1.0×; energia zero → 1.5× (cansaço custa caro).
    return 1 + (100 - energia) / 100 * 0.5


def _mult_xp(nivel: int) -> float:
    # experiência acelera, com piso de 0.8× para não virar sobre-humano.
    return max(0.8, 1 - nivel * 0.03)


def duracao_tarefa(pessoa: Pessoa, item: ItemCardapio, beats: list[Beat]) -> DuracaoTarefa:
    """Combina base × skill × fadiga × xp + Σ beats → duração final (com piso)."""
    base = item.segundos_preparo
    mult_skill = _mult_skill(pessoa.skill_em(item.estacao))
    mult_fadiga = _mult_fadiga(pessoa.energia)
    mult_xp = _mult_xp(pessoa.nivel_em(item.estacao))
    soma_beats = sum(b.delta_s for b in beats)
    total = max(_PISO_SEGUNDOS, base * mult_skill * mult_fadiga * mult_xp + soma_beats)
    return DuracaoTarefa(
        base=base,
        mult_skill=mult_skill,
        mult_fadiga=mult_fadiga,
        mult_xp=mult_xp,
        soma_beats=soma_beats,
        total=total,
        beats=tuple(beats),
    )

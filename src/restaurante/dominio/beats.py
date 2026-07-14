"""Beat — o átomo da simulação Sims: um micro-evento que acontece durante uma tarefa.

CODEX: Make Illegal States Unrepresentable + mechanism×policy.
    Uma tarefa não tem duração fixa; ela é uma SEQUÊNCIA de beats. Cada beat carrega
    seu próprio delta de tempo e uma descrição humana (para o Rich narrar). O *quais*
    beats acontecem é decidido por uma política (GeradorDeSituacoes), não aqui — este
    módulo só define a forma do átomo.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TipoBeat(StrEnum):
    """A natureza de um micro-evento. O sinal do delta segue a semântica do tipo."""

    CONCENTRADO = "concentrado"  # ritmo normal, Δ ~ 0
    INSPIRADO = "inspirado"  # fluiu, Δ negativo (mais rápido)
    ATRAPALHOU = "atrapalhou"  # errou a mão, Δ positivo
    DISTRAIU = "distraiu"  # pensou noutra coisa, Δ positivo pequeno
    INTERAGIU = "interagiu"  # trocou ideia com um colega, Δ positivo pequeno
    EVENTO = "evento"  # algo externo (queimou, equipamento falhou), Δ variável


@dataclass(frozen=True, slots=True)
class Beat:
    """Um micro-evento vivido por um NPC durante uma tarefa."""

    tipo: TipoBeat
    texto: str
    delta_s: float

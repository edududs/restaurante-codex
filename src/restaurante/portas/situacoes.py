"""Porta de situações — a política que decide QUAIS beats um NPC vive numa tarefa.

CODEX: Mechanism, not Policy (Parte III). O motor da simulação (mecanismo) roda beats
    e soma tempos; ele não sabe *quais* situações acontecem nem por quê. Isso é política,
    injetada por esta porta. Trocar a "personalidade do mundo" = trocar o adapter, sem
    tocar no motor. O `rng` entra de fora para a decisão ser determinística e testável.
"""

from __future__ import annotations

from random import Random
from typing import Protocol

from restaurante.dominio.beats import Beat
from restaurante.dominio.cardapio import ItemCardapio
from restaurante.dominio.pessoas import Pessoa


class GeradorDeSituacoes(Protocol):
    """Dada uma pessoa, um item e uma fonte de aleatoriedade, produz a lista de beats."""

    def gerar(self, pessoa: Pessoa, item: ItemCardapio, rng: Random) -> list[Beat]:
        """Decide os micro-eventos daquela pessoa naquela tarefa (determinístico por `rng`)."""
        ...

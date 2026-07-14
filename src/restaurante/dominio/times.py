"""Times — quem responde por quais estações, e como o time trabalha.

CODEX: SSoT das responsabilidades. Quem pega qual tarefa não é decidido por um `if`
    espalhado no motor; é uma consequência de qual time é responsável pela estação.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from restaurante.dominio.cardapio import Estacao


class ModoExecucao(StrEnum):
    """Como o time encara o trabalho (enviesa levemente o desempenho, no futuro)."""

    FOCADO = "focado"
    MULTITAREFA = "multitarefa"


@dataclass(frozen=True, slots=True)
class Time:
    """Um time: seus membros (ids de Pessoa) e as estações pelas quais responde."""

    nome: str
    membros: tuple[str, ...]
    responsabilidades: frozenset[Estacao]
    modo: ModoExecucao = ModoExecucao.FOCADO

    def atende(self, estacao: Estacao) -> bool:
        """True se este time é responsável pela estação."""
        return estacao in self.responsabilidades

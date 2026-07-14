"""Apresentador coletor — guarda os eventos em vez de desenhar. Base dos testes e do replay.

CODEX: o teste do motor injeta este adapter no lugar do Rich e afirma sobre os eventos
    coletados — sem depender de terminal nem de Rich. Vazamento de implementação zero.
"""

from __future__ import annotations

from restaurante.portas.apresentador import SimEvent


class ApresentadorColetor:
    """Acumula todos os eventos emitidos, em ordem."""

    def __init__(self) -> None:
        self.eventos: list[SimEvent] = []

    def emitir(self, evento: SimEvent) -> None:
        """Guarda o evento."""
        self.eventos.append(evento)

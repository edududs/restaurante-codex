"""Relógio fake — reproduz o turno instantaneamente, somando o tempo lógico pedido.

CODEX: implementa a porta Relogio para os testes. Não espera nada real (os testes rodam
    instantâneos), mas registra `total_dormido` para asserções sobre o ritmo pedido.
"""

from __future__ import annotations

import asyncio


class RelogioFake:
    """Não pausa; apenas acumula quanto tempo lógico foi solicitado."""

    def __init__(self) -> None:
        self.total_dormido = 0.0

    async def dormir(self, segundos: float) -> None:
        """Registra o tempo pedido e cede o loop uma vez (sem espera real)."""
        self.total_dormido += segundos
        await asyncio.sleep(0)

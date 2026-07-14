"""Relógio real — pausa de verdade, com escala para a demo caber em segundos.

CODEX: implementa a porta Relogio. `escala` comprime o tempo (0.2 = 5× mais rápido).
"""

from __future__ import annotations

import asyncio


class RelogioReal:
    """Pausa `segundos * escala` de verdade no event loop."""

    def __init__(self, escala: float = 1.0) -> None:
        self._escala = escala

    async def dormir(self, segundos: float) -> None:
        """Pausa proporcional ao tempo lógico, escalado."""
        await asyncio.sleep(segundos * self._escala)

"""Porta de relógio — abstrai a passagem do tempo, para separar ritmo de determinismo.

CODEX: DIP + testabilidade. O motor não chama `asyncio.sleep` direto; ele pede ao Relógio.
    Em produção/demo, o RelógioReal pausa de verdade (com escala). Em teste, o RelógioFake
    não espera nada — o resultado da simulação já é determinístico (vem do seed), então o
    relógio só controla o *ritmo* da reprodução, nunca o *conteúdo*.
"""

from __future__ import annotations

from typing import Protocol


class Relogio(Protocol):
    """Fonte de tempo do replay. `dormir` pausa; nada mais."""

    async def dormir(self, segundos: float) -> None:
        """Aguarda (ou não, no fake) o número de segundos lógicos dado."""
        ...

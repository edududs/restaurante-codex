"""Porta de notificação — avisar o cliente sem saber COMO (console, SMS, push...).

CODEX: Information Hiding (Parte II) — a decisão "por qual canal avisamos" fica
    escondida atrás desta interface. O serviço manda `notificar(...)` e não sabe
    (nem precisa saber) se sai por terminal, WhatsApp ou fumaça.
"""

from __future__ import annotations

from typing import Protocol


class Notificador(Protocol):
    """Envia uma mensagem ao cliente. Assíncrono porque canais reais são I/O de rede."""

    async def notificar(self, mensagem: str) -> None:
        """Entrega `mensagem` ao cliente pelo canal que o adapter concreto implementar."""
        ...

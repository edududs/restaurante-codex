"""Adapter de notificação que imprime no terminal. Trocável por SMS/push/WhatsApp.

CODEX: este é o único lugar que sabe que a notificação sai por `print`. O serviço só
    conhece a porta `Notificador`. Imprimir aqui é o *trabalho* deste adapter — por isso
    o `T201` (proibição de print) está liberado só para este arquivo no pyproject.
"""

from __future__ import annotations

import asyncio


class NotificadorConsole:
    """Implementa `Notificador` escrevendo no stdout, com um pequeno atraso de I/O."""

    async def notificar(self, mensagem: str) -> None:
        """Escreve a mensagem no terminal, após uma latência simulada."""
        await asyncio.sleep(0.05)  # simula latência de rede de um canal real
        print(f"      📲 [notificação] {mensagem}")

"""Porta de persistência — guardar/recuperar pedidos sem saber ONDE.

CODEX: DIP + Repository Pattern. O adapter concreto pode ser memória, Postgres, Redis.
    A regra de negócio fala com esta interface genérica; nenhum serviço importa o SDK
    de um banco específico. Trocar o storage = novo adapter, zero mudança no domínio.
"""

from __future__ import annotations

from typing import Protocol

from restaurante.dominio.pedido import Pedido


class RepositorioPedidos(Protocol):
    """Armazena e recupera pedidos. Assíncrono porque um banco real é I/O."""

    async def salvar(self, pedido: Pedido) -> None:
        """Persiste o pedido (idempotente por `id`: mesmo id sobrescreve, não duplica)."""
        ...

    async def buscar(self, pedido_id: str) -> Pedido | None:
        """Recupera o pedido pelo id, ou `None` se não existir."""
        ...

    async def listar(self) -> tuple[Pedido, ...]:
        """Devolve todos os pedidos armazenados."""
        ...

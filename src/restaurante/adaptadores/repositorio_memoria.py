"""Adapter de persistência em memória — um dict fingindo ser banco.

CODEX: implementa a porta `RepositorioPedidos`. Para trocar por Postgres, basta um
    `RepositorioPostgres` que implemente a mesma interface — os serviços não percebem.
    Idempotência: salvar o mesmo pedido (mesmo id) duas vezes sobrescreve, não duplica.
"""

from __future__ import annotations

import asyncio

from restaurante.dominio.pedido import Pedido


class RepositorioMemoria:
    """Guarda pedidos num dicionário indexado por id."""

    def __init__(self) -> None:
        self._pedidos: dict[str, Pedido] = {}

    async def salvar(self, pedido: Pedido) -> None:
        """Guarda o pedido no dicionário, indexado por id (idempotente)."""
        await asyncio.sleep(0)  # ponto de suspensão: um banco real aguardaria I/O aqui
        self._pedidos[pedido.id] = pedido  # idempotente por id (SSoT do estado do pedido)

    async def buscar(self, pedido_id: str) -> Pedido | None:
        """Recupera o pedido pelo id, ou `None`."""
        await asyncio.sleep(0)
        return self._pedidos.get(pedido_id)

    async def listar(self) -> tuple[Pedido, ...]:
        """Devolve todos os pedidos guardados."""
        await asyncio.sleep(0)
        return tuple(self._pedidos.values())

"""Adapter de pagamento fake — simula um gateway, sem cobrar de verdade.

CODEX: em teste e em demo, injetamos este; em produção, um `PagamentoStripe`. O domínio
    não muda. É o que permite testar a regra sem um gateway real rodando (o Codex chama
    isso de não deixar o teste depender do vendor concreto).
"""

from __future__ import annotations

import asyncio
import uuid

from restaurante.dominio.dinheiro import Dinheiro
from restaurante.portas.pagamento import Comprovante


class PagamentoFake:
    """Aprova qualquer cobrança após uma latência simulada e devolve o comprovante."""

    async def cobrar(self, valor: Dinheiro) -> Comprovante:
        """Aprova a cobrança após latência simulada e devolve um comprovante fake."""
        await asyncio.sleep(0.1)  # simula a ida e volta ao gateway
        return Comprovante(id=f"pay_{uuid.uuid4().hex[:10]}", valor=valor)

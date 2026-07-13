"""Porta de pagamento — cobrar um valor sem acoplar o domínio a um gateway.

CODEX: DIP (Parte II). O `ServicoBalcao` depende de `Pagamento` (abstração), não de
    um SDK concreto (Stripe, Pagar.me...). Em teste, injetamos um adapter fake; em
    produção, um adapter real. O domínio nem fica sabendo da troca.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from restaurante.dominio.dinheiro import Dinheiro


@dataclass(frozen=True, slots=True)
class Comprovante:
    """Prova de que a cobrança ocorreu. É o que o gateway devolve."""

    id: str
    valor: Dinheiro


class Pagamento(Protocol):
    """Cobra um valor e devolve o comprovante. Assíncrono: gateway é I/O de rede."""

    async def cobrar(self, valor: Dinheiro) -> Comprovante:
        """Cobra `valor` no gateway e devolve o comprovante da transação."""
        ...

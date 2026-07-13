"""Porta de precificação — o ponto de extensão onde a POLÍTICA de preço se pluga.

CODEX: Mechanism, not Policy + Strategy Pattern (Parte III).
    O serviço que calcula o total (o *mecanismo*) não sabe se hoje é happy hour, se
    há desconto de aniversário ou nada disso. Ele recebe uma `EstrategiaPreco` (a
    *política*) de fora e a consulta. Uma regra nova de preço = uma implementação
    nova da porta, sem tocar no mecanismo. O oposto — um `if hora < 19` enterrado no
    caixa — seria política vazando pro mecanismo (o anti-padrão que o Codex aponta).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from restaurante.dominio.cardapio import ItemCardapio
from restaurante.dominio.dinheiro import Dinheiro


@dataclass(frozen=True, slots=True)
class ContextoPreco:
    """O que a política pode olhar pra decidir o preço. Hoje: a hora (0–23)."""

    hora: int


class EstrategiaPreco(Protocol):
    """Dado um item e um contexto, devolve o preço a cobrar por unidade."""

    def preco_do_item(self, item: ItemCardapio, contexto: ContextoPreco) -> Dinheiro:
        """Devolve o preço a cobrar por unidade de `item`, dado o `contexto`."""
        ...

"""Estratégias de preço — políticas plugáveis que implementam `EstrategiaPreco`.

CODEX: Strategy Pattern (Parte III) — cada variação do algoritmo de preço é um objeto
    intercambiável. O mecanismo (o serviço) escolhe qual usar; nenhum `switch` cresce.

CODEX: Rule of Three / AHA (Parte I — o freio) — repare que NÃO criamos uma mega-engine
    de regras configurável ("desconto por %, por item, por cupom, por hora, por..."). Só
    existem as duas políticas que realmente precisamos. Quando surgir a terceira variação
    de verdade, aí sim extraímos a abstração — com evidência, não com adivinhação.
"""

from __future__ import annotations

from restaurante.dominio.cardapio import Categoria, ItemCardapio
from restaurante.dominio.dinheiro import Dinheiro
from restaurante.portas.precificacao import ContextoPreco

_HAPPY_HOUR_INICIO = 17
_HAPPY_HOUR_FIM = 20
_DESCONTO_HAPPY_HOUR = 50


class PrecoDeTabela:
    """Política trivial: o preço é o preço-base do cardápio. Sem firula (KISS)."""

    def preco_do_item(self, item: ItemCardapio, contexto: ContextoPreco) -> Dinheiro:  # noqa: ARG002
        """Preço-base do cardápio, sem olhar o contexto."""
        # contexto é ignorado de propósito: esta política não olha a hora.
        return item.preco_base


class PrecoHappyHour:
    """Política: bebidas saem com 50% de desconto entre 17h e 20h; o resto, base.

    Isto é POLÍTICA plugada por fora — não um `if hora < 20` enterrado no caixa.
    Trocar a janela ou o desconto mexe só aqui, no lugar dono da regra.
    """

    def preco_do_item(self, item: ItemCardapio, contexto: ContextoPreco) -> Dinheiro:
        """Aplica 50% de desconto a bebidas dentro da janela; caso contrário, preço-base."""
        eh_happy_hour = _HAPPY_HOUR_INICIO <= contexto.hora < _HAPPY_HOUR_FIM
        if eh_happy_hour and item.categoria is Categoria.BEBIDA:
            return item.preco_base.aplicar_desconto(_DESCONTO_HAPPY_HOUR)
        return item.preco_base

"""Cálculo do total — o MECANISMO que consome a POLÍTICA de preço.

CODEX: Mechanism, not Policy (Parte III). Esta função sabe *como* somar (percorrer
    linhas, multiplicar por quantidade, acumular). Ela não sabe *qual* preço aplicar —
    isso vem da `EstrategiaPreco` injetada. O mesmo mecanismo serve à tabela normal, ao
    happy hour, ou a qualquer política futura, sem uma linha alterada aqui.
"""

from __future__ import annotations

from restaurante.dominio.dinheiro import ZERO, Dinheiro
from restaurante.dominio.pedido import Pedido
from restaurante.portas.precificacao import ContextoPreco, EstrategiaPreco


def calcular_total(
    pedido: Pedido,
    estrategia: EstrategiaPreco,
    contexto: ContextoPreco,
) -> Dinheiro:
    """Soma o pedido aplicando a política de preço recebida."""
    total = ZERO
    for linha in pedido.linhas:
        preco_unitario = estrategia.preco_do_item(linha.item, contexto)
        total = total + preco_unitario * linha.quantidade
    return total

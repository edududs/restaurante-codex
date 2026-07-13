"""Testes da cozinha assíncrona — provam concorrência e contenção de estação.

São testes de *tempo*: usam limites folgados para não ficarem instáveis, mas ainda
distinguem 'rodou em paralelo' de 'rodou em série'.
"""

from __future__ import annotations

import time

from restaurante.dominio.cardapio import Cardapio, Estacao
from restaurante.dominio.pedido import NoLocal, Pedido
from restaurante.servicos.cozinha import Cozinha


async def test_estacoes_diferentes_correm_em_paralelo() -> None:
    # Chopp (BAR, 1s) + Batata (FRITADEIRA, 4s): estações distintas → ~max(1,4), não 5.
    pedido = (
        Pedido(consumo=NoLocal(mesa=1))
        .com_item(Cardapio.buscar("Chopp"))
        .com_item(Cardapio.buscar("Batata frita"))
    )
    cozinha = Cozinha(escala=0.1)  # tempos viram 0.1s e 0.4s
    inicio = time.perf_counter()
    await cozinha.preparar(pedido)
    decorrido = time.perf_counter() - inicio
    # soma seria 0.5s; em paralelo fica perto de 0.4s. Exigimos < 0.5 (não serializou).
    assert decorrido < 0.5


async def test_mesma_estacao_serializa() -> None:
    # Hambúrguer (CHAPA, 6s) + Filé (CHAPA, 9s) com 1 boca → precisam enfileirar.
    pedido = (
        Pedido(consumo=NoLocal(mesa=1))
        .com_item(Cardapio.buscar("Hambúrguer"))
        .com_item(Cardapio.buscar("Filé"))
    )
    cozinha = Cozinha(capacidade=dict.fromkeys(Estacao, 1), escala=0.05)  # 0.3s e 0.45s
    inicio = time.perf_counter()
    await cozinha.preparar(pedido)
    decorrido = time.perf_counter() - inicio
    # se serializou, o total ~0.75s; o item mais longo sozinho seria só 0.45s.
    assert decorrido > 0.55


async def test_narrador_recebe_inicio_e_fim_de_cada_item() -> None:
    eventos: list[str] = []
    pedido = Pedido(consumo=NoLocal(mesa=1)).com_item(Cardapio.buscar("Chopp"))
    cozinha = Cozinha(escala=0.01)
    await cozinha.preparar(pedido, eventos.append)
    assert any("começou" in e for e in eventos)
    assert any("terminou" in e for e in eventos)

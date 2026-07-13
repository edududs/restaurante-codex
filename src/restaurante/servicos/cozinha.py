"""A cozinha — onde a assincronicidade deixa de ser abstrata e vira intuição.

CODEX (bônus deste repo): assincronicidade explicada por analogia física.

    Por que async, e não threads ou código sequencial? Um cozinheiro, enquanto o
    hambúrguer frita na chapa, NÃO fica parado olhando — ele vai montar a salada. O
    tempo de "fritar" é *espera de I/O* (o prato cozinha sozinho); durante essa espera,
    a mesma linha de execução faz outra coisa útil. Isso é `await`: "vou soltar a CPU
    enquanto isso assa; me acorde quando estiver pronto".

    Dois conceitos, dois mecanismos:
      • `asyncio.gather(...)`  → PARALELISMO lógico: começar todos os pratos "ao mesmo
        tempo" e esperar todos terminarem. É por isso que um pedido de 3 pratos não
        demora a soma dos tempos, e sim o tempo do prato mais lento.
      • `asyncio.Semaphore`    → RECURSO LIMITADO: cada estação (chapa, fritadeira) tem
        um número finito de bocas. Dois pratos da mesma estação NÃO cozinham juntos —
        um espera o outro. É a contenção real de recurso, modelada honestamente.

    Juntando os dois: pratos de estações diferentes correm em paralelo; pratos da mesma
    estação se enfileiram. Exatamente uma cozinha de verdade.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from restaurante.dominio.cardapio import Estacao
from restaurante.dominio.pedido import Pedido

# Sink de narração: a cozinha o *chama*, mas não decide o que ele faz (DI/observer).
Narrador = Callable[[str], None]


def sem_narracao(_: str) -> None:
    """Narrador padrão que não faz nada — a cozinha funciona igual sem observador."""


class Cozinha:
    """Prepara pedidos respeitando a capacidade de cada estação.

    `capacidade` diz quantos pratos cada estação faz ao mesmo tempo (bocas do fogão).
    `escala` comprime o tempo simulado para a demo rodar rápido (1.0 = tempo "real").
    """

    def __init__(
        self,
        capacidade: dict[Estacao, int] | None = None,
        escala: float = 1.0,
    ) -> None:
        cap = capacidade or dict.fromkeys(Estacao, 1)
        # Um semáforo por estação = as bocas disponíveis daquela estação.
        self._bocas: dict[Estacao, asyncio.Semaphore] = {
            estacao: asyncio.Semaphore(n) for estacao, n in cap.items()
        }
        self._escala = escala

    async def _preparar_linha(
        self,
        pedido_id: str,
        nome: str,
        estacao: Estacao,
        segundos: float,
        narrar: Narrador,
    ) -> None:
        # Espera uma boca livre na estação (contenção real de recurso).
        async with self._bocas[estacao]:
            narrar(f"[{pedido_id}] 🔥 {estacao.value} começou: {nome}")
            await asyncio.sleep(segundos * self._escala)  # o prato "cozinha" — I/O simulado
            narrar(f"[{pedido_id}] ✅ {estacao.value} terminou: {nome}")

    async def preparar(self, pedido: Pedido, narrar: Narrador = sem_narracao) -> None:
        """Prepara todas as linhas do pedido concorrentemente, por estação."""
        tarefas = [
            self._preparar_linha(
                pedido.id,
                linha.item.nome,
                linha.item.estacao,
                linha.item.segundos_preparo,
                narrar,
            )
            for linha in pedido.linhas
        ]
        # gather: dispara tudo e espera todos. O relógio anda uma vez, não N vezes.
        await asyncio.gather(*tarefas)

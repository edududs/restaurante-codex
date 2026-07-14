"""Demo narrada — rode e *veja* os princípios do Codex acontecendo.

    uv run python demo.py

A saída é cronometrada: repare que dois pedidos disparados juntos NÃO somam os tempos —
a cozinha os prepara em paralelo, exceto quando disputam a mesma estação. É a
assincronicidade visível a olho nu.
"""

from __future__ import annotations

import asyncio
import io
import sys
import time

from restaurante.adaptadores.precos import PrecoDeTabela, PrecoHappyHour
from restaurante.app import montar_restaurante
from restaurante.config.catalogo import Cardapio
from restaurante.dominio.cardapio import Estacao
from restaurante.dominio.erros import ErroDeDominio
from restaurante.dominio.pedido import Delivery, NoLocal, ParaViagem, Pedido
from restaurante.portas.precificacao import ContextoPreco
from restaurante.servicos.conta import calcular_total

# Windows usa cp1252 no console por padrão e não encoda emoji/box-drawing. Reembrulhamos
# o stdout num writer UTF-8 para a demo ficar bonita em qualquer plataforma.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

_INICIO = time.perf_counter()


def _t() -> str:
    """Carimbo de tempo desde o início, para enxergar a concorrência."""
    return f"{time.perf_counter() - _INICIO:5.2f}s"


def narrar(msg: str) -> None:
    """Sink de narração injetado na cozinha — imprime com o relógio."""
    print(f"  {_t()} │ {msg}")


def titulo(texto: str) -> None:
    """Imprime o cabeçalho de uma cena da demonstração."""
    print(f"\n{'─' * 70}\n▶  {texto}\n{'─' * 70}")


async def cena_ciclo_de_vida() -> None:
    """Um pedido, do 'confirmado' ao 'entregue', narrado passo a passo."""
    titulo("CENA 1 — ciclo de vida de um pedido (máquina de estados + async)")
    restaurante = montar_restaurante(escala=0.3)

    pedido = (
        Pedido(consumo=NoLocal(mesa=7))
        .com_item(Cardapio.buscar("Hambúrguer"))
        .com_item(Cardapio.buscar("Batata frita"))
        .com_item(Cardapio.buscar("Chopp"))
    )
    print(f"  Pedido {pedido.id} na mesa 7: hambúrguer + batata + chopp")
    final = await restaurante.balcao.atender(pedido, ContextoPreco(hora=13), narrar)
    print(f"  Estado final: {final.estado.value.upper()}  ✔")


async def cena_concorrencia() -> None:
    """Três pedidos ao mesmo tempo: veja as estações sendo disputadas."""
    titulo("CENA 2 — três pedidos concorrentes (asyncio.gather + estações limitadas)")
    # Uma boca por estação: dois pratos de chapa NÃO fritam juntos (contenção real).
    restaurante = montar_restaurante(escala=0.3, capacidade=dict.fromkeys(Estacao, 1))

    p1 = (
        Pedido(consumo=NoLocal(mesa=1))
        .com_item(Cardapio.buscar("Filé"))
        .com_item(Cardapio.buscar("Batata frita"))
    )
    p2 = (
        Pedido(consumo=ParaViagem())
        .com_item(Cardapio.buscar("Hambúrguer"))
        .com_item(Cardapio.buscar("Onion rings"))
    )
    p3 = (
        Pedido(consumo=Delivery(endereco="Rua das Flores, 100"))
        .com_item(Cardapio.buscar("Salada Caesar"))
        .com_item(Cardapio.buscar("Suco natural"))
    )

    print("  3 pedidos disparados JUNTOS. Filé e Hambúrguer disputam a chapa;")
    print("  salada e bebidas correm livres em suas estações.\n")
    inicio = time.perf_counter()
    await asyncio.gather(
        restaurante.balcao.atender(p1, ContextoPreco(hora=13), narrar),
        restaurante.balcao.atender(p2, ContextoPreco(hora=13), narrar),
        restaurante.balcao.atender(p3, ContextoPreco(hora=13), narrar),
    )
    decorrido = time.perf_counter() - inicio
    print(f"\n  3 pedidos prontos em {decorrido:.2f}s — menos que a soma dos tempos.")


async def cena_politica_de_preco() -> None:
    """Mesma comanda, duas políticas de preço plugadas por fora."""
    titulo("CENA 3 — mecanismo × política: happy hour é plugável, não um 'if' no caixa")
    comanda = (
        Pedido(consumo=NoLocal(mesa=3))
        .com_item(Cardapio.buscar("Chopp"), 4)
        .com_item(Cardapio.buscar("Hambúrguer"), 2)
    )
    contexto_hh = ContextoPreco(hora=18)  # dentro do happy hour

    # O MESMO mecanismo (calcular_total) recebe duas políticas diferentes por fora.
    total_normal = calcular_total(comanda, PrecoDeTabela(), contexto_hh)
    total_hh = calcular_total(comanda, PrecoHappyHour(), contexto_hh)
    print("  4 chopps + 2 hambúrgueres às 18h:")
    print(f"    política PrecoDeTabela : {total_normal}")
    print(f"    política PrecoHappyHour: {total_hh}   (chopp com 50% off)")
    print("  O mecanismo de somar é o MESMO. Só a política injetada mudou.")


async def cena_fail_fast() -> None:
    """Estados ilegais falham cedo e alto, em vez de contaminar o fluxo."""
    titulo("CENA 4 — fail-fast: o domínio recusa estados inválidos na origem")

    vazio = Pedido(consumo=ParaViagem())
    try:
        vazio.confirmar()
    except ErroDeDominio as erro:
        print(f"  ✋ Confirmar pedido vazio → {type(erro).__name__}: {erro}")

    entregue = (
        Pedido(consumo=NoLocal(mesa=9))
        .com_item(Cardapio.buscar("Chopp"))
        .confirmar()
        .iniciar_preparo()
        .marcar_pronto()
        .entregar()
    )
    try:
        entregue.cancelar()  # cancelar algo já entregue é transição ilegal
    except ErroDeDominio as erro:
        print(f"  ✋ Cancelar pedido entregue → {type(erro).__name__}: {erro}")
    print("  Nenhum estado inválido seguiu viagem. O erro apareceu onde nasceu.")


async def main() -> None:
    """Roda todas as cenas da demonstração, em sequência."""
    print("\n🍔  RESTAURANTE-CODEX — engenharia de software servida à mesa\n")
    await cena_ciclo_de_vida()
    await cena_concorrencia()
    await cena_politica_de_preco()
    await cena_fail_fast()
    print("\n✨  Fim. Leia os `# CODEX:` no código e os docs/ para o 'porquê' de cada peça.\n")


if __name__ == "__main__":
    asyncio.run(main())

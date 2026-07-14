"""Demo Sims — o mesmo restaurante, agora com NPCs de carne-e-beat.

    uv run python demo_sim.py

Cada NPC vive *beats* (fluiu, se atrapalhou, distraiu, interagiu, sofreu um evento) que
fazem o tempo de cada tarefa **emergir**, em vez de ser fixo. `planejar_turno` é 100%
determinístico dada a `SEED`; troque a seed (ou uma skill em `adaptadores/elenco.py`) e
veja o turno inteiro contar outra história.
"""

from __future__ import annotations

import asyncio
import io
import sys

from restaurante.adaptadores.apresentador_rich import ApresentadorRich
from restaurante.adaptadores.elenco import BIOS, criar_elenco
from restaurante.adaptadores.relogio_real import RelogioReal
from restaurante.adaptadores.situacoes_sims import SituacoesSims
from restaurante.dominio.cardapio import Cardapio
from restaurante.dominio.pedido import Delivery, NoLocal, ParaViagem, Pedido
from restaurante.servicos.motor import planejar_turno, reproduzir

# Windows usa cp1252 no console por padrão e não encoda emoji/box-drawing. Reembrulhamos
# o stdout num writer UTF-8 para a demo ficar bonita em qualquer plataforma.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

SEED = 42


def _pedidos() -> list[Pedido]:
    """Monta 3 pedidos variados, cobrindo as 4 estações (chapa/fritadeira/saladas/bar)."""
    mesa = (
        Pedido(consumo=NoLocal(mesa=5))
        .com_item(Cardapio.buscar("Hambúrguer"))
        .com_item(Cardapio.buscar("Batata frita"))
        .com_item(Cardapio.buscar("Chopp"))
    )
    viagem = (
        Pedido(consumo=ParaViagem())
        .com_item(Cardapio.buscar("Filé"))
        .com_item(Cardapio.buscar("Salada Caesar"))
    )
    delivery = (
        Pedido(consumo=Delivery(endereco="Rua das Palmeiras, 42"))
        .com_item(Cardapio.buscar("Onion rings"))
        .com_item(Cardapio.buscar("Suco natural"))
    )
    return [mesa, viagem, delivery]


async def main() -> None:
    """Planeja o turno inteiro (puro) e reproduz com ritmo real, via a pele Rich."""
    print("\n🎬  RESTAURANTE-CODEX — a fase Sims: NPCs de verdade, tempo emergente\n")
    roster, times = criar_elenco()
    plano = planejar_turno(_pedidos(), roster, times, SituacoesSims(), seed=SEED)
    apresentador = ApresentadorRich(bios=BIOS)
    await reproduzir(plano, RelogioReal(escala=0.25), apresentador)
    print(
        "\n✨  Fim do turno. Troque a SEED ou uma skill em adaptadores/elenco.py e rode de novo.\n"
    )


if __name__ == "__main__":
    asyncio.run(main())

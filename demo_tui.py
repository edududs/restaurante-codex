"""Demo Sims — dashboard ao vivo (Textual), a mesma simulação de demo_sim.py em tela cheia.

    uv run python demo_tui.py

`demo_sim.py` narra o turno em log Rich, linha a linha; este script abre a MESMA
simulação — mesmo `planejar_turno` puro, mesmo `reproduzir` async — só que consumida por
`SimuladorApp`, o adapter que implementa a porta `Apresentador` como uma TUI Textual ao
vivo (equipe, estações, feed, pedidos). O motor não sabe qual pele está ligada.
"""

from __future__ import annotations

import io
import sys

from restaurante.adaptadores.apresentador_textual import SimuladorApp
from restaurante.adaptadores.elenco import BIOS, criar_elenco
from restaurante.adaptadores.relogio_real import RelogioReal
from restaurante.adaptadores.situacoes_sims import SituacoesSims
from restaurante.dominio.cardapio import Cardapio
from restaurante.dominio.pedido import Delivery, NoLocal, ParaViagem, Pedido
from restaurante.servicos.motor import planejar_turno

# Windows usa cp1252 no console por padrão e não encoda emoji/box-drawing. Reembrulhamos
# o stdout num writer UTF-8 para o dashboard ficar bonito em qualquer plataforma.
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


def main() -> None:
    """Planeja o turno inteiro (puro) e reproduz num dashboard Textual ao vivo."""
    roster, times = criar_elenco()
    plano = planejar_turno(_pedidos(), roster, times, SituacoesSims(), seed=SEED)
    # Ritmo didático (~1.5×): cada micro-evento "respira" e dá pra acompanhar tudo.
    app = SimuladorApp(plano, RelogioReal(escala=1.5), BIOS, roster)
    app.run()


if __name__ == "__main__":
    main()

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
from restaurante.config.carregador import carregar_cenario
from restaurante.portas.relogio import Relogio
from restaurante.servicos.motor import planejar_turno


def montar_app(relogio: Relogio | None = None) -> SimuladorApp:
    """Monta o app do cenário (config/cenario.json). `relogio` injetável para testes.

    `escala` vem do cenário (didática, ~1.5×): cada micro-evento "respira". Sem side-effects
    no import — importar este módulo não abre TUI nem mexe no stdout, então dá pra testá-lo.
    """
    seed, escala, pedidos = carregar_cenario()
    roster, times = criar_elenco()
    plano = planejar_turno(pedidos, roster, times, SituacoesSims(), seed=seed)
    return SimuladorApp(plano, relogio or RelogioReal(escala=escala), BIOS, roster)


def main() -> None:
    """Reconfigura o stdout p/ UTF-8 (Windows) e roda o dashboard Textual ao vivo."""
    # cp1252 no console do Windows não encoda emoji/box-drawing; reembrulha em UTF-8.
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    montar_app().run()


if __name__ == "__main__":
    main()

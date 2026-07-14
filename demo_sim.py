"""Demo Sims — o mesmo restaurante, agora com NPCs de carne-e-beat.

    uv run python demo_sim.py

Cada NPC vive *beats* (fluiu, se atrapalhou, distraiu, interagiu, sofreu um evento) que
fazem o tempo de cada tarefa **emergir**, em vez de ser fixo. `planejar_turno` é 100%
determinístico dada a seed; troque a seed em `config/cenario.json` (ou exporte
`RESTAURANTE_SEED=<n>` — pydantic-settings dá precedência ao env), ou uma skill em
`config/elenco.json`, e veja o turno inteiro contar outra história.
"""

from __future__ import annotations

import asyncio
import io
import sys

from restaurante.adaptadores.apresentador_rich import ApresentadorRich
from restaurante.adaptadores.elenco import BIOS, criar_elenco
from restaurante.adaptadores.relogio_real import RelogioReal
from restaurante.adaptadores.situacoes_sims import SituacoesSims
from restaurante.config.carregador import carregar_cenario
from restaurante.servicos.motor import planejar_turno, reproduzir

# Windows usa cp1252 no console por padrão e não encoda emoji/box-drawing. Reembrulhamos
# o stdout num writer UTF-8 para a demo ficar bonita em qualquer plataforma.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)


async def main() -> None:
    """Planeja o turno inteiro (puro) e reproduz com ritmo real, via a pele Rich."""
    print("\n🎬  RESTAURANTE-CODEX — a fase Sims: NPCs de verdade, tempo emergente\n")
    seed, escala, pedidos = carregar_cenario()
    roster, times = criar_elenco()
    plano = planejar_turno(pedidos, roster, times, SituacoesSims(), seed=seed)
    apresentador = ApresentadorRich(bios=BIOS)
    # `escala` vem de config/cenario.json (didática, ~1.5×): cada micro-evento
    # "respira" e dá pra acompanhar tudo.
    await reproduzir(plano, RelogioReal(escala=escala), apresentador)
    print(
        "\n✨  Fim do turno. Troque a seed em config/cenario.json (ou RESTAURANTE_SEED) "
        "ou uma skill em config/elenco.json e rode de novo.\n"
    )


if __name__ == "__main__":
    asyncio.run(main())

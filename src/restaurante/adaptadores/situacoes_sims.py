"""Política "Sims" — a vida interior dos NPCs virando beats.

CODEX: Strategy/mechanism×policy. Esta é UMA política concreta da porta GeradorDeSituacoes.
    Ela olha personalidade, humor, skill e energia (os 4 fatores) e sorteia — com `rng`
    semeado — os micro-eventos daquela pessoa naquela tarefa. Outra "personalidade de mundo"
    seria outro adapter; o motor não muda. Determinística: mesma seed → mesma história.
"""

from __future__ import annotations

from random import Random

from restaurante.dominio.beats import Beat, TipoBeat
from restaurante.dominio.cardapio import ItemCardapio
from restaurante.dominio.pessoas import Humor, Pessoa

# Knobs da política (documentados e tunáveis num lugar só — SSoT da "física social").
_PROB_INSPIRA = 0.5
_PROB_ATRAPALHO_BASE = 0.6
_BONUS_ATRAPALHO_MAU_HUMOR = 0.3
_PROB_DISTRAI = 0.5
_PROB_INTERAGE = 0.4
_PROB_EVENTO = 0.08

_PENSAMENTOS = (
    "pensou no fim de semana 💭",
    "lembrou de uma música 🎵",
    "reparou num cliente famoso 👀",
    "ficou com fome do próprio prato 😋",
)
_EVENTOS: tuple[tuple[str, float], ...] = (
    ("queimou e refez do zero 🔥", 2.5),
    ("o equipamento travou ⚙️", 1.2),
    ("pegou o horário de pico 🏃", 0.8),
)


class SituacoesSims:
    """Gera beats no estilo Sims a partir do estado do NPC."""

    def gerar(self, pessoa: Pessoa, item: ItemCardapio, rng: Random) -> list[Beat]:
        """Sorteia os micro-eventos da pessoa nesta tarefa (ver os knobs acima)."""
        skill = pessoa.skill_em(item.estacao) / 100
        cria = pessoa.personalidade.criatividade / 100
        disc = pessoa.personalidade.disciplina / 100
        soc = pessoa.personalidade.sociavel / 100
        mau_humor = pessoa.humor in (Humor.CANSADO, Humor.ESTRESSADO)

        beats = [Beat(TipoBeat.CONCENTRADO, f"assume a {item.estacao.value}", 0.0)]

        if rng.random() < cria * _PROB_INSPIRA:
            beats.append(
                Beat(TipoBeat.INSPIRADO, f"fluiu em {item.nome}", -round(rng.uniform(0.3, 1.0), 2))
            )

        prob_atrapalho = (1 - skill) * _PROB_ATRAPALHO_BASE + (
            _BONUS_ATRAPALHO_MAU_HUMOR if mau_humor else 0
        )
        if rng.random() < prob_atrapalho:
            beats.append(
                Beat(
                    TipoBeat.ATRAPALHOU, "se atrapalhou na receita", round(rng.uniform(0.5, 1.5), 2)
                )
            )

        if rng.random() < (1 - disc) * _PROB_DISTRAI:
            beats.append(
                Beat(TipoBeat.DISTRAIU, rng.choice(_PENSAMENTOS), round(rng.uniform(0.2, 0.6), 2))
            )

        if rng.random() < soc * _PROB_INTERAGE:
            beats.append(
                Beat(
                    TipoBeat.INTERAGIU,
                    "trocou ideia com um colega",
                    round(rng.uniform(0.2, 0.5), 2),
                )
            )

        if rng.random() < _PROB_EVENTO:
            texto, delta = rng.choice(_EVENTOS)
            beats.append(Beat(TipoBeat.EVENTO, texto, delta))

        return beats

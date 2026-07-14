"""Porta de apresentação — o motor conta o que acontece; quem desenha é problema do adapter.

CODEX: DIP + mechanism×policy. O motor emite `SimEvent`s tipados (o QUE aconteceu, com o
    tempo lógico `t`). Como isso vira pixels — blocos Rich, log simples, ou nada (coletor de
    teste) — é decisão do adapter. Trocar a pele não toca no motor.

CODEX: SimEvent é um tipo-soma — cada evento é um caso distinto, e um `match` sobre ele é
    exaustivo (o type checker cobra), então nenhum evento é esquecido no renderer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from restaurante.dominio.beats import Beat
from restaurante.dominio.cardapio import Estacao
from restaurante.dominio.pessoas import Humor
from restaurante.servicos.modelo_tempo import DuracaoTarefa


@dataclass(frozen=True, slots=True)
class ResumoNPC:
    """O balanço de um NPC ao fim do turno (para o painel de stats)."""

    nome: str
    tarefas: int
    tempo_trabalhado: float
    xp_ganho: int
    eventos_sofridos: int
    energia_final: int
    humor_final: Humor


@dataclass(frozen=True, slots=True)
class PedidoRecebido:
    """Um pedido entrou no fluxo."""

    t: float
    pedido_id: str
    descricao: str


@dataclass(frozen=True, slots=True)
class TarefaIniciada:
    """Um NPC assumiu um item numa estação."""

    t: float
    pessoa: str
    item: str
    estacao: Estacao


@dataclass(frozen=True, slots=True)
class BeatOcorreu:
    """Um micro-evento aconteceu durante a tarefa (a 'vida interior' do NPC)."""

    t: float
    pessoa: str
    item: str
    beat: Beat


@dataclass(frozen=True, slots=True)
class TarefaConcluida:
    """Um item ficou pronto; carrega o breakdown do tempo (o 'porquê')."""

    t: float
    pessoa: str
    item: str
    duracao: DuracaoTarefa


@dataclass(frozen=True, slots=True)
class PedidoPronto:
    """Todos os itens de um pedido saíram."""

    t: float
    pedido_id: str
    total_s: float


@dataclass(frozen=True, slots=True)
class TurnoResumo:
    """Fecha o turno com o balanço por NPC (base para a timeline/stats)."""

    t: float
    npcs: tuple[ResumoNPC, ...]


SimEvent = (
    PedidoRecebido | TarefaIniciada | BeatOcorreu | TarefaConcluida | PedidoPronto | TurnoResumo
)
"""União fechada dos eventos que o motor pode emitir."""


class Apresentador(Protocol):
    """Recebe cada evento da simulação e decide o que fazer com ele (desenhar, coletar…)."""

    def emitir(self, evento: SimEvent) -> None:
        """Processa um evento da simulação (chamado em ordem cronológica pelo motor)."""
        ...

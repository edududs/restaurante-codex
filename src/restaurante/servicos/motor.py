"""Motor da simulação — planeja o turno (puro) e reproduz (async fino).

CODEX: SoC radical entre determinismo e ritmo.
    `planejar_turno` é uma FUNÇÃO PURA: dado seed + elenco + pedidos, computa o turno inteiro
    — quem faz o quê, quando (timeline), com quais beats, e como cada NPC evolui. Nenhuma
    espera, nenhum I/O, 100% determinístico e testável.
    `reproduzir` é uma casca ASSÍNCRONA mínima: recebe o plano pronto e só dá o *ritmo*,
    dormindo (via porta Relogio) o intervalo entre eventos e emitindo cada um ao apresentador.
    O relógio real dá o show ao vivo; o fake reproduz instantâneo nos testes. O CONTEÚDO é o
    mesmo — só o ritmo muda.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from random import Random

from restaurante.dominio.cardapio import Estacao, ItemCardapio
from restaurante.dominio.erros import ErroDeDominio
from restaurante.dominio.pedido import Consumo, Delivery, NoLocal, ParaViagem, Pedido
from restaurante.dominio.pessoas import Pessoa, aplicar_conclusao
from restaurante.dominio.times import Time
from restaurante.portas.apresentador import (
    Apresentador,
    BeatOcorreu,
    PedidoPronto,
    PedidoRecebido,
    ResumoNPC,
    SimEvent,
    TarefaConcluida,
    TarefaIniciada,
    TurnoResumo,
)
from restaurante.portas.relogio import Relogio
from restaurante.portas.situacoes import GeradorDeSituacoes
from restaurante.servicos.modelo_tempo import duracao_tarefa


class SemResponsavel(ErroDeDominio):
    """Nenhum time responde por uma estação exigida por um pedido (config incompleta)."""


@dataclass(frozen=True, slots=True)
class PlanoTurno:
    """O resultado determinístico do planejamento: eventos em ordem + elenco final."""

    eventos: tuple[SimEvent, ...]
    roster_final: dict[str, Pessoa]


def _descreve_consumo(consumo: Consumo) -> str:
    match consumo:
        case NoLocal(mesa):
            return f"mesa {mesa}"
        case ParaViagem():
            return "para viagem"
        case Delivery(endereco):
            return f"delivery ({endereco})"


def _escolher_npc(
    estacao: Estacao,
    times: list[Time],
    estado: dict[str, Pessoa],
    cursor_pessoa: dict[str, float],
) -> str:
    """Escolhe o NPC apto: livre mais cedo, depois mais habilidoso, depois id (determinístico)."""
    candidatos = [
        pid for time in times if time.atende(estacao) for pid in time.membros if pid in estado
    ]
    if not candidatos:
        raise SemResponsavel(f"Nenhum time responde pela estação {estacao.value}.")
    return min(
        candidatos,
        key=lambda pid: (cursor_pessoa[pid], -estado[pid].skill_em(estacao), pid),
    )


def _itens_do_pedido(pedido: Pedido) -> list[ItemCardapio]:
    return [linha.item for linha in pedido.linhas for _ in range(linha.quantidade)]


def planejar_turno(
    pedidos: list[Pedido],
    roster: dict[str, Pessoa],
    times: list[Time],
    gerador: GeradorDeSituacoes,
    seed: int,
) -> PlanoTurno:
    """Computa o turno inteiro de forma pura e determinística (mesmo seed → mesmo plano)."""
    rng = Random(seed)
    estado = dict(roster)
    cursor_estacao: defaultdict[Estacao, float] = defaultdict(float)
    cursor_pessoa: defaultdict[str, float] = defaultdict(float)
    eventos: list[SimEvent] = []

    tarefas = defaultdict[str, int](int)
    tempo = defaultdict[str, float](float)
    xp = defaultdict[str, int](int)
    eventos_sofridos = defaultdict[str, int](int)

    for pedido in pedidos:
        inicio_pedido = float("inf")
        fim_pedido = 0.0
        for item in _itens_do_pedido(pedido):
            pid = _escolher_npc(item.estacao, times, estado, cursor_pessoa)
            pessoa = estado[pid]
            beats = gerador.gerar(pessoa, item, rng)
            dur = duracao_tarefa(pessoa, item, beats)

            inicio = max(cursor_estacao[item.estacao], cursor_pessoa[pid])
            fim = inicio + dur.total
            eventos.append(
                TarefaIniciada(t=inicio, pessoa=pessoa.nome, item=item.nome, estacao=item.estacao)
            )
            n = len(beats)
            for i, beat in enumerate(beats):
                tb = inicio + (i + 1) / (n + 1) * dur.total
                eventos.append(BeatOcorreu(t=tb, pessoa=pessoa.nome, item=item.nome, beat=beat))
            eventos.append(TarefaConcluida(t=fim, pessoa=pessoa.nome, item=item.nome, duracao=dur))

            cursor_estacao[item.estacao] = fim
            cursor_pessoa[pid] = fim
            inicio_pedido = min(inicio_pedido, inicio)
            fim_pedido = max(fim_pedido, fim)

            estado[pid] = aplicar_conclusao(pessoa, item.estacao, houve_evento=dur.houve_evento)
            tarefas[pid] += 1
            tempo[pid] += dur.total
            xp[pid] += estado[pid].experiencia[item.estacao] - pessoa.experiencia.get(
                item.estacao, 0
            )
            if dur.houve_evento:
                eventos_sofridos[pid] += 1

        eventos.append(
            PedidoRecebido(
                t=inicio_pedido, pedido_id=pedido.id, descricao=_descreve_consumo(pedido.consumo)
            )
        )
        eventos.append(
            PedidoPronto(t=fim_pedido, pedido_id=pedido.id, total_s=fim_pedido - inicio_pedido)
        )

    fim_turno = max((cursor_pessoa[p] for p in cursor_pessoa), default=0.0)
    resumos = tuple(
        ResumoNPC(
            nome=estado[pid].nome,
            tarefas=tarefas[pid],
            tempo_trabalhado=round(tempo[pid], 2),
            xp_ganho=xp[pid],
            eventos_sofridos=eventos_sofridos[pid],
            energia_final=estado[pid].energia,
            humor_final=estado[pid].humor,
        )
        for pid in sorted(tarefas)
    )
    eventos.append(TurnoResumo(t=fim_turno, npcs=resumos))

    eventos.sort(key=lambda e: e.t)
    return PlanoTurno(eventos=tuple(eventos), roster_final=estado)


async def reproduzir(plano: PlanoTurno, relogio: Relogio, apresentador: Apresentador) -> None:
    """Reproduz o plano dando o ritmo: dorme entre eventos e emite cada um em ordem."""
    t_anterior = 0.0
    for evento in plano.eventos:
        dt = evento.t - t_anterior
        if dt > 0:
            await relogio.dormir(dt)
        t_anterior = evento.t
        apresentador.emitir(evento)

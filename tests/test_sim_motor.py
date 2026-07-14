"""Testes da Fase 2 — o motor (planejamento puro + replay async)."""

from __future__ import annotations

import math

import pytest

from restaurante.adaptadores.apresentador_coletor import ApresentadorColetor
from restaurante.adaptadores.relogio_fake import RelogioFake
from restaurante.adaptadores.situacoes_sims import SituacoesSims
from restaurante.config.catalogo import Cardapio
from restaurante.dominio.cardapio import Estacao
from restaurante.dominio.pedido import NoLocal, Pedido
from restaurante.dominio.pessoas import Personalidade, Pessoa
from restaurante.dominio.times import Time
from restaurante.portas.apresentador import (
    PedidoPronto,
    TarefaConcluida,
    TarefaIniciada,
    TurnoResumo,
)
from restaurante.servicos.motor import SemResponsavel, planejar_turno, reproduzir

_PERS = Personalidade(foco=70, sociavel=50, disciplina=70, criatividade=60)


def _roster() -> dict[str, Pessoa]:
    return {
        "ana": Pessoa("ana", "Ana", _PERS, {Estacao.CHAPA: 80, Estacao.BAR: 30}),
        "bruno": Pessoa("bruno", "Bruno", _PERS, {Estacao.BAR: 75, Estacao.FRITADEIRA: 60}),
        "caio": Pessoa("caio", "Caio", _PERS, {Estacao.SALADAS: 70, Estacao.FRITADEIRA: 50}),
    }


def _times() -> list[Time]:
    return [
        Time(
            "Cozinha",
            ("ana", "caio"),
            frozenset({Estacao.CHAPA, Estacao.FRITADEIRA, Estacao.SALADAS}),
        ),
        Time("Bar", ("bruno",), frozenset({Estacao.BAR})),
    ]


def _pedido(*itens: tuple[str, int]) -> Pedido:
    pedido = Pedido(consumo=NoLocal(mesa=1))
    for nome, qtd in itens:
        pedido = pedido.com_item(Cardapio.buscar(nome), qtd)
    return pedido


def _iniciadas(plano_eventos: tuple[object, ...]) -> list[TarefaIniciada]:
    return [e for e in plano_eventos if isinstance(e, TarefaIniciada)]


def test_planejamento_e_deterministico() -> None:
    args = ([_pedido(("Hambúrguer", 2), ("Chopp", 1))], _roster(), _times(), SituacoesSims())
    a = planejar_turno(*args, seed=7)
    b = planejar_turno(*args, seed=7)
    assert a.eventos == b.eventos


def test_turno_produz_os_eventos_esperados() -> None:
    plano = planejar_turno([_pedido(("Chopp", 1))], _roster(), _times(), SituacoesSims(), seed=1)
    tipos = {type(e).__name__ for e in plano.eventos}
    assert {
        "PedidoRecebido",
        "TarefaIniciada",
        "TarefaConcluida",
        "PedidoPronto",
        "TurnoResumo",
    } <= tipos
    resumos = [e for e in plano.eventos if isinstance(e, TurnoResumo)]
    assert resumos
    assert resumos[0].npcs


def test_mesma_estacao_serializa() -> None:
    # 2 hambúrgueres (CHAPA) — a estação é recurso único, então a 2ª começa após a 1ª acabar.
    plano = planejar_turno(
        [_pedido(("Hambúrguer", 2))], _roster(), _times(), SituacoesSims(), seed=3
    )
    chapa = sorted(
        (e for e in _iniciadas(plano.eventos) if e.estacao is Estacao.CHAPA), key=lambda e: e.t
    )
    concluidas = sorted(
        (e for e in plano.eventos if isinstance(e, TarefaConcluida)), key=lambda e: e.t
    )
    assert len(chapa) == 2
    assert chapa[1].t >= concluidas[0].t - 1e-9  # a 2ª só inicia depois da 1ª concluir


def test_estacoes_diferentes_comecam_juntas() -> None:
    plano = planejar_turno(
        [_pedido(("Hambúrguer", 1), ("Chopp", 1))], _roster(), _times(), SituacoesSims(), seed=2
    )
    inicios = {e.estacao: e.t for e in _iniciadas(plano.eventos)}
    assert inicios[Estacao.CHAPA] == 0.0
    assert inicios[Estacao.BAR] == 0.0


def test_npcs_evoluem_no_turno() -> None:
    roster = _roster()
    plano = planejar_turno([_pedido(("Hambúrguer", 3))], roster, _times(), SituacoesSims(), seed=5)
    trabalhou = plano.roster_final["ana"]
    assert trabalhou.energia < roster["ana"].energia
    assert trabalhou.experiencia.get(Estacao.CHAPA, 0) > 0


def test_sem_time_responsavel_falha() -> None:
    times_incompletos = [Time("Bar", ("bruno",), frozenset({Estacao.BAR}))]
    with pytest.raises(SemResponsavel):
        planejar_turno(
            [_pedido(("Hambúrguer", 1))], _roster(), times_incompletos, SituacoesSims(), seed=1
        )


async def test_replay_emite_tudo_em_ordem_e_paga_o_tempo() -> None:
    plano = planejar_turno(
        [_pedido(("Hambúrguer", 1), ("Salada Caesar", 1))],
        _roster(),
        _times(),
        SituacoesSims(),
        seed=9,
    )
    coletor = ApresentadorColetor()
    relogio = RelogioFake()
    await reproduzir(plano, relogio, coletor)

    assert coletor.eventos == list(plano.eventos)
    ultimo = plano.eventos[-1]
    assert math.isclose(relogio.total_dormido, ultimo.t, abs_tol=1e-9)


async def test_replay_pedido_pronto_reporta_duracao() -> None:
    plano = planejar_turno([_pedido(("Chopp", 1))], _roster(), _times(), SituacoesSims(), seed=4)
    coletor = ApresentadorColetor()
    await reproduzir(plano, RelogioFake(), coletor)
    prontos = [e for e in coletor.eventos if isinstance(e, PedidoPronto)]
    assert prontos
    assert prontos[0].total_s > 0

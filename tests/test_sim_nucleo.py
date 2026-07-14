"""Testes do núcleo Sims (Fase 1): pessoas, modelo de tempo e determinismo das situações."""

from __future__ import annotations

import math
from random import Random

import pytest

from restaurante.adaptadores.situacoes_sims import SituacoesSims
from restaurante.dominio.beats import Beat, TipoBeat
from restaurante.dominio.cardapio import Cardapio, Estacao
from restaurante.dominio.pessoas import (
    AtributoInvalido,
    Humor,
    Personalidade,
    Pessoa,
    aplicar_conclusao,
    nivel,
)
from restaurante.servicos.modelo_tempo import duracao_tarefa

_PERS = Personalidade(foco=70, sociavel=60, disciplina=65, criatividade=75)
_HAMBURGUER = Cardapio.buscar("Hambúrguer")  # CHAPA, 6.0s


def _pessoa(**kw: object) -> Pessoa:
    base: dict[str, object] = {
        "id": "p1",
        "nome": "Ana",
        "personalidade": _PERS,
        "skills": {Estacao.CHAPA: 50},
        "energia": 100,
    }
    base.update(kw)
    return Pessoa(**base)  # type: ignore[arg-type]


# ── Determinismo (o coração testável) ─────────────────────────────────────────
def test_situacoes_sao_deterministicas_por_seed() -> None:
    ger = SituacoesSims()
    ana = _pessoa()
    beats_a = ger.gerar(ana, _HAMBURGUER, Random(42))
    beats_b = ger.gerar(ana, _HAMBURGUER, Random(42))
    assert [(b.tipo, b.texto, b.delta_s) for b in beats_a] == [
        (b.tipo, b.texto, b.delta_s) for b in beats_b
    ]


def test_seeds_diferentes_podem_divergir() -> None:
    ger = SituacoesSims()
    ana = _pessoa()
    # Varre algumas seeds; pelo menos uma deve produzir histórias diferentes.
    historias = {
        tuple((b.tipo, b.delta_s) for b in ger.gerar(ana, _HAMBURGUER, Random(s))) for s in range(8)
    }
    assert len(historias) > 1


# ── Os 4 fatores no modelo de tempo ───────────────────────────────────────────
def test_skill_mais_alto_reduz_o_tempo() -> None:
    lento = duracao_tarefa(_pessoa(skills={Estacao.CHAPA: 20}), _HAMBURGUER, [])
    rapido = duracao_tarefa(_pessoa(skills={Estacao.CHAPA: 90}), _HAMBURGUER, [])
    assert rapido.total < lento.total


def test_energia_baixa_aumenta_o_tempo() -> None:
    descansada = duracao_tarefa(_pessoa(energia=100), _HAMBURGUER, [])
    exausta = duracao_tarefa(_pessoa(energia=10), _HAMBURGUER, [])
    assert exausta.total > descansada.total


def test_experiencia_reduz_o_tempo() -> None:
    novata = duracao_tarefa(_pessoa(experiencia={Estacao.CHAPA: 0}), _HAMBURGUER, [])
    veterana = duracao_tarefa(_pessoa(experiencia={Estacao.CHAPA: 400}), _HAMBURGUER, [])
    assert veterana.total < novata.total


def test_beats_somam_no_total() -> None:
    sem = duracao_tarefa(_pessoa(), _HAMBURGUER, [])
    com = duracao_tarefa(_pessoa(), _HAMBURGUER, [Beat(TipoBeat.ATRAPALHOU, "x", 1.0)])
    assert math.isclose(com.total - sem.total, 1.0, abs_tol=1e-9)


def test_breakdown_expoe_evento() -> None:
    d = duracao_tarefa(_pessoa(), _HAMBURGUER, [Beat(TipoBeat.EVENTO, "queimou", 2.5)])
    assert d.houve_evento is True


# ── Pessoa: validação e evolução ──────────────────────────────────────────────
def test_atributo_fora_do_intervalo_falha() -> None:
    with pytest.raises(AtributoInvalido):
        Personalidade(foco=200, sociavel=10, disciplina=10, criatividade=10)
    with pytest.raises(AtributoInvalido):
        _pessoa(energia=-5)
    with pytest.raises(AtributoInvalido):
        _pessoa(skills={Estacao.CHAPA: 150})


def test_nivel_por_xp() -> None:
    assert nivel(0) == 0
    assert nivel(250) == 2


def test_conclusao_gasta_energia_e_ganha_xp_sem_mutar_original() -> None:
    ana = _pessoa(energia=100)
    depois = aplicar_conclusao(ana, Estacao.CHAPA, houve_evento=False)
    assert depois.energia == 92
    assert depois.experiencia[Estacao.CHAPA] == 15
    assert ana.energia == 100  # original imutável
    assert ana.experiencia == {}


def test_evento_custa_energia_extra_e_estressa() -> None:
    ana = _pessoa(energia=50)
    depois = aplicar_conclusao(ana, Estacao.CHAPA, houve_evento=True)
    assert depois.energia == 38  # 50 - (8 + 4)
    assert depois.humor is Humor.ESTRESSADO


def test_humor_cansado_com_energia_baixa() -> None:
    ana = _pessoa(energia=30)
    depois = aplicar_conclusao(ana, Estacao.CHAPA, houve_evento=False)
    assert depois.humor is Humor.CANSADO

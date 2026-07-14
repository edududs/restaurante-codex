"""Testes da Fase 5 — o boundary de config: parse do JSON, validado por Pydantic v2.

CODEX: PARSE, DON'T VALIDATE — estes testes provam duas coisas: (1) o caminho feliz
    (defaults do repo carregam e o jogo roda com eles); (2) o caminho de erro (JSON
    malformado/incompleto falha ALTO, no boundary, com uma `ValidationError` — nunca
    silenciosamente, e nunca três camadas depois dentro do domínio).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from pydantic import TypeAdapter, ValidationError

from restaurante.adaptadores.situacoes_sims import SituacoesSims
from restaurante.config.carregador import (
    carregar_cardapio,
    carregar_cenario,
    carregar_elenco,
    carregar_tema,
)
from restaurante.config.modelos import (
    ConsumoCfg,
    DeliveryCfg,
    ElencoCfg,
    ItemCfg,
    MesaCfg,
    ViagemCfg,
)
from restaurante.dominio.beats import TipoBeat
from restaurante.dominio.cardapio import Estacao
from restaurante.servicos.motor import planejar_turno


@pytest.fixture(autouse=True)
def _cache_limpo() -> Iterator[None]:  # pyright: ignore[reportUnusedFunction]
    """Cada teste começa e termina com os loaders sem estado de chamadas anteriores.

    Necessário porque `@functools.cache` faz o parse UMA vez por processo — sem isso,
    um teste que muda o env (`RESTAURANTE_SEED`) ou aponta pra um JSON inválido
    poluiria o cache visto pelos testes seguintes. `autouse=True`: pytest injeta esta
    fixture implicitamente em cada teste deste módulo — o type checker não enxerga
    esse uso via nome de convenção do pytest, daí o `pyright: ignore` acima.
    """
    for loader in (carregar_cardapio, carregar_elenco, carregar_tema, carregar_cenario):
        loader.cache_clear()
    yield
    for loader in (carregar_cardapio, carregar_elenco, carregar_tema, carregar_cenario):
        loader.cache_clear()


# ── Caminho feliz: os defaults do repo carregam e o jogo roda ──────────────────
def test_defaults_carregam_e_nao_ficam_vazios() -> None:
    cardapio = carregar_cardapio()
    roster, times, bios = carregar_elenco()
    tema = carregar_tema()
    seed, escala, pedidos = carregar_cenario()

    assert cardapio
    assert roster
    assert times
    assert bios
    assert tema
    assert pedidos
    assert seed >= 0
    assert escala > 0


def test_o_turno_roda_com_a_config_default() -> None:
    roster, times, _bios = carregar_elenco()
    seed, _escala, pedidos = carregar_cenario()
    plano = planejar_turno(pedidos, roster, times, SituacoesSims(), seed=seed)
    assert plano.eventos
    assert plano.roster_final


# ── extra="forbid": chave desconhecida no JSON é erro ───────────────────────────
def test_chave_desconhecida_falha_com_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        ItemCfg.model_validate(
            {
                "nome": "Hambúrguer",
                "preco_reais": 28.0,
                "estacao": "chapa",
                "segundos_preparo": 6.0,
                "categoria": "prato",
                "campo_que_nao_existe": "typo",
            }
        )


# ── Discriminated union do consumo ──────────────────────────────────────────────
_ADAPTER_CONSUMO: TypeAdapter[MesaCfg | ViagemCfg | DeliveryCfg] = TypeAdapter(ConsumoCfg)


def test_discriminated_union_escolhe_o_variant_certo() -> None:
    consumo = _ADAPTER_CONSUMO.validate_python({"tipo": "delivery", "endereco": "Rua X, 1"})
    assert isinstance(consumo, DeliveryCfg)
    assert consumo.endereco == "Rua X, 1"


def test_discriminated_union_valida_a_faixa_do_variant() -> None:
    mesa = _ADAPTER_CONSUMO.validate_python({"tipo": "mesa", "numero": 5})
    assert isinstance(mesa, MesaCfg)
    with pytest.raises(ValidationError):
        _ADAPTER_CONSUMO.validate_python({"tipo": "mesa", "numero": 0})  # ge=1


# ── model_validator cross-field do elenco ───────────────────────────────────────
def _elenco_base() -> dict[str, list[dict[str, object]]]:
    return {
        "npcs": [
            {
                "id": "Ana",
                "nome": "Ana",
                "bio": "craque da chapa",
                "personalidade": {
                    "foco": 80,
                    "sociavel": 40,
                    "disciplina": 80,
                    "criatividade": 45,
                },
                "skills": {"chapa": 90},
            }
        ],
        "times": [
            {
                "nome": "Cozinha",
                "membros": ["Ana"],
                "responsabilidades": ["chapa", "fritadeira", "saladas", "bar"],
                "modo": "focado",
            }
        ],
    }


def test_elenco_valido_cobre_todas_as_estacoes() -> None:
    cfg = ElencoCfg.model_validate(_elenco_base())
    assert cfg.npcs
    assert cfg.times


def test_time_citando_npc_inexistente_falha() -> None:
    dados = _elenco_base()
    dados["times"][0]["membros"] = ["Ana", "Fantasma"]
    with pytest.raises(ValidationError, match="Fantasma"):
        ElencoCfg.model_validate(dados)


def test_elenco_que_nao_cobre_uma_estacao_falha() -> None:
    dados = _elenco_base()
    dados["times"][0]["responsabilidades"] = ["chapa"]  # falta fritadeira/saladas/bar
    with pytest.raises(ValidationError, match="bar"):
        ElencoCfg.model_validate(dados)


# ── pydantic-settings: env > json > default ─────────────────────────────────────
def test_env_var_sobrepoe_o_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESTAURANTE_SEED", "999")
    seed, _escala, _pedidos = carregar_cenario()
    assert seed == 999


def test_sem_env_var_usa_o_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RESTAURANTE_SEED", raising=False)
    seed, _escala, _pedidos = carregar_cenario()
    assert seed == 42  # config/cenario.json


def test_tema_cobre_os_tipos_de_beat_narraveis() -> None:
    tema = carregar_tema()
    narraveis = {
        TipoBeat.INSPIRADO,
        TipoBeat.ATRAPALHOU,
        TipoBeat.DISTRAIU,
        TipoBeat.INTERAGIU,
        TipoBeat.EVENTO,
    }
    assert narraveis <= tema.keys()


def test_cardapio_cobre_as_4_estacoes() -> None:
    cardapio = carregar_cardapio()
    estacoes = {item.estacao for item in cardapio.values()}
    assert estacoes == set(Estacao)

"""Carregador — lê os JSON de `config/`, valida (Pydantic) e devolve tipos do DOMÍNIO.

CODEX: PARSE, DON'T VALIDATE, ponta a ponta. Este módulo é a ÚNICA ponte entre o dado
    cru (arquivo em disco) e o domínio (dataclasses puras). Cada `carregar_*` faz DUAS
    coisas, nesta ordem: (1) valida com o modelo Pydantic certo — se o JSON estiver
    errado, o `ValidationError` sobe AQUI, com o path exato do campo (fail-fast, a
    fonte do erro é óbvia); (2) MAPEIA o modelo já validado para o tipo de domínio
    equivalente. Depois deste ponto — em `dominio/*`, em `servicos/*` — nunca mais
    existe pydantic, só dataclasses puras, como sempre foi.

CODEX: cache — cada loader é `@functools.cache`: o parse acontece uma vez por processo
    (o JSON não muda em runtime), e chamadas repetidas (`Cardapio.buscar` a cada item de
    pedido, por exemplo) não reabrem nem revalidam o arquivo.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import assert_never

from pydantic_settings import SettingsConfigDict

from restaurante.config.modelos import (
    CARDAPIO_ADAPTER,
    CenarioCfg,
    ConsumoCfg,
    DeliveryCfg,
    ElencoCfg,
    MesaCfg,
    PedidoCfg,
    TemaCfg,
    ViagemCfg,
)
from restaurante.dominio.beats import TipoBeat
from restaurante.dominio.cardapio import ItemCardapio
from restaurante.dominio.dinheiro import Dinheiro
from restaurante.dominio.erros import ItemForaDoCardapio
from restaurante.dominio.pedido import Consumo, Delivery, NoLocal, ParaViagem, Pedido
from restaurante.dominio.pessoas import Personalidade, Pessoa
from restaurante.dominio.times import Time

# Raiz do repo, calculada a partir deste arquivo — funciona não importa o cwd de onde
# `uv run` foi disparado (mais robusto que um caminho relativo tipo "config/x.json").
_RAIZ = Path(__file__).resolve().parents[3]
_CONFIG = _RAIZ / "config"


def _consumo_do_dominio(consumo_cfg: ConsumoCfg) -> Consumo:
    """Mapeia o variant do discriminated union para o caso correspondente do tipo-soma."""
    match consumo_cfg:
        case MesaCfg(numero=numero):
            return NoLocal(mesa=numero)
        case ViagemCfg():
            return ParaViagem()
        case DeliveryCfg(endereco=endereco):
            return Delivery(endereco=endereco)
        case _:  # pragma: no cover - guarda de exaustividade (Codex: assert_never)
            assert_never(consumo_cfg)


def _pedido_do_dominio(pedido_cfg: PedidoCfg, cardapio: dict[str, ItemCardapio]) -> Pedido:
    """Monta um `Pedido` (rascunho) a partir do config validado + o cardápio carregado."""
    pedido = Pedido(consumo=_consumo_do_dominio(pedido_cfg.consumo))
    for item_cfg in pedido_cfg.itens:
        item = cardapio.get(item_cfg.item)
        if item is None:
            disponiveis = ", ".join(sorted(cardapio))
            raise ItemForaDoCardapio(
                f"'{item_cfg.item}' não está no cardápio. Temos: {disponiveis}."
            )
        pedido = pedido.com_item(item, item_cfg.quantidade)
    return pedido


@functools.cache
def carregar_cardapio(caminho: Path | None = None) -> dict[str, ItemCardapio]:
    """Lê e valida `config/cardapio.json`; devolve nome -> `ItemCardapio` (domínio puro)."""
    caminho_real = caminho if caminho is not None else _CONFIG / "cardapio.json"
    itens_cfg = CARDAPIO_ADAPTER.validate_json(caminho_real.read_bytes())
    return {
        item.nome: ItemCardapio(
            nome=item.nome,
            preco_base=Dinheiro(round(item.preco_reais * 100)),
            estacao=item.estacao,
            segundos_preparo=item.segundos_preparo,
            categoria=item.categoria,
        )
        for item in itens_cfg
    }


@functools.cache
def carregar_elenco(
    caminho: Path | None = None,
) -> tuple[dict[str, Pessoa], list[Time], dict[str, str]]:
    """Lê e valida `config/elenco.json`; devolve (roster, times, bios) — tudo domínio puro."""
    caminho_real = caminho if caminho is not None else _CONFIG / "elenco.json"
    cfg = ElencoCfg.model_validate_json(caminho_real.read_bytes())

    roster = {
        npc.id: Pessoa(
            id=npc.id,
            nome=npc.nome,
            personalidade=Personalidade(
                foco=npc.personalidade.foco,
                sociavel=npc.personalidade.sociavel,
                disciplina=npc.personalidade.disciplina,
                criatividade=npc.personalidade.criatividade,
            ),
            skills=dict(npc.skills),
        )
        for npc in cfg.npcs
    }
    times = [
        Time(
            nome=time_cfg.nome,
            membros=time_cfg.membros,
            responsabilidades=time_cfg.responsabilidades,
            modo=time_cfg.modo,
        )
        for time_cfg in cfg.times
    ]
    bios = {npc.id: npc.bio for npc in cfg.npcs}
    return roster, times, bios


@functools.cache
def carregar_tema(caminho: Path | None = None) -> dict[TipoBeat, tuple[str, str]]:
    """Lê e valida `config/tema.json`; devolve `TipoBeat -> (emoji, cor)`."""
    caminho_real = caminho if caminho is not None else _CONFIG / "tema.json"
    cfg = TemaCfg.model_validate_json(caminho_real.read_bytes())
    return {tipo: (estilo.emoji, estilo.cor) for tipo, estilo in cfg.beats.items()}


@functools.cache
def carregar_cenario(caminho: Path | None = None) -> tuple[int, float, list[Pedido]]:
    """Lê e valida o cenário — env > `config/cenario.json` > default — via pydantic-settings.

    Devolve (seed, escala, pedidos) prontos para `planejar_turno`. O `json_file` é
    reapontado dinamicamente para o caminho resolvido (absoluto, calculado a partir
    deste arquivo) para o loader funcionar não importa o cwd de onde foi chamado —
    `CenarioCfg.model_config` mantém o `"config/cenario.json"` relativo como o
    default didático (o que aparece se você instanciar `CenarioCfg()` direto).
    """
    caminho_real = caminho if caminho is not None else _CONFIG / "cenario.json"

    class _CenarioDoArquivo(CenarioCfg):
        model_config = SettingsConfigDict(
            env_prefix="RESTAURANTE_",
            json_file=str(caminho_real),
            json_file_encoding="utf-8",
            extra="forbid",
        )

    cfg = _CenarioDoArquivo()
    cardapio = carregar_cardapio()
    pedidos = [_pedido_do_dominio(pedido_cfg, cardapio) for pedido_cfg in cfg.pedidos]
    return cfg.seed, cfg.escala, pedidos


__all__ = ["carregar_cardapio", "carregar_cenario", "carregar_elenco", "carregar_tema"]

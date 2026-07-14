"""Modelos Pydantic v2 — o boundary que valida JSON cru ANTES de virar domínio.

CODEX: PARSE, DON'T VALIDATE (aplicado ao boundary externo).
    A ideia central do capítulo: não espalhe `if`/asserts de validação pelo código
    checando "isso está certo?" toda vez que um dado é usado. Em vez disso, faça o
    PARSE uma única vez, na borda (aqui), transformando dado cru (`dict`/JSON solto,
    tipado como `Any`) num tipo que só existe se já for válido. Depois desse ponto,
    o resto do programa — e em especial o DOMÍNIO (`dominio/*`, dataclasses puras,
    zero pydantic) — trabalha com tipos que **já provam** a validade por construção.
    Se o JSON está errado, o erro aparece AQUI, com o path exato do campo (fail-fast),
    não três camadas depois como um `KeyError` ou um `AttributeError` obscuro.

CODEX: Make Illegal States Unrepresentable, na borda. `extra="forbid"` recusa chave
    desconhecida (typo no JSON = erro, não silêncio). Os `Annotated[...]` com `Field`
    recusam faixas impossíveis (skill fora de 0–100, preço negativo) antes que o
    domínio precise se defender de novo. O discriminated union de `ConsumoCfg` espelha
    o tipo-soma que `dominio/pedido.py::Consumo` já modela — a validação escolhe o
    variant certo pelo campo `tipo`, sem `if`/`isinstance` manual.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, TypeAdapter, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from pydantic_settings.sources import JsonConfigSettingsSource

from restaurante.dominio.beats import TipoBeat
from restaurante.dominio.cardapio import Categoria, Estacao
from restaurante.dominio.times import ModoExecucao

type Atributo = Annotated[int, Field(ge=0, le=100)]
"""Um atributo 0–100 (skill numa estação, traço de personalidade) — reutilizado
em vários modelos (PEP 695 `type` + `Annotated`: um só lugar dono da faixa)."""


class _Base(BaseModel):
    """Base comum aos modelos de config: chave estranha e mutação pós-parse são erro.

    `extra="forbid"` — um typo no JSON (`"esatcao"` em vez de `"estacao"`) vira
    `ValidationError` na hora, não um campo silenciosamente ignorado. `frozen=True` —
    o objeto validado não muda depois (o mesmo espírito imutável do domínio).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)


# ── Cardápio ──────────────────────────────────────────────────────────────────
class ItemCfg(_Base):
    """Um item do cardápio, como aparece cru em `config/cardapio.json`."""

    nome: str
    preco_reais: Annotated[float, Field(ge=0)]
    estacao: Estacao
    segundos_preparo: Annotated[float, Field(gt=0)]
    categoria: Categoria


CARDAPIO_ADAPTER = TypeAdapter(list[ItemCfg])
"""Valida o array JSON top-level do cardápio sem precisar de um model-wrapper —
`TypeAdapter` é o jeito Pydantic v2 de validar QUALQUER tipo, não só `BaseModel`."""


# ── Elenco: NPCs e times ────────────────────────────────────────────────────────
class PersonalidadeCfg(_Base):
    """Os 4 traços que enviesam os beats de um NPC — mesma forma de `Personalidade`."""

    foco: Atributo
    sociavel: Atributo
    disciplina: Atributo
    criatividade: Atributo


class NpcCfg(_Base):
    """Um NPC cru: quem é, sua bio, personalidade e skills por estação."""

    id: str
    nome: str
    bio: str
    personalidade: PersonalidadeCfg
    skills: dict[Estacao, Atributo]


class TimeCfg(_Base):
    """Um time cru: membros (ids de NPC) e as estações pelas quais responde."""

    nome: str
    membros: tuple[str, ...]
    responsabilidades: frozenset[Estacao]
    modo: ModoExecucao = ModoExecucao.FOCADO


class ElencoCfg(_Base):
    """O elenco inteiro — NPCs + times — com as invariantes cross-field do restaurante.

    CODEX: `model_validator(mode="after")` é onde regras que atravessam MÚLTIPLOS
        campos (ou múltiplos itens de uma lista) vivem — um `Field(...)` sozinho só
        valida um campo isolado. Aqui, duas invariantes que o domínio (`motor.py`)
        SUPÕE verdadeiras e não reverifica: todo membro de time existe, e as
        estações estão todas cobertas por algum time (senão `SemResponsavel`
        explode em runtime, na simulação, longe da causa real — o JSON incompleto).
    """

    npcs: tuple[NpcCfg, ...]
    times: tuple[TimeCfg, ...]

    @model_validator(mode="after")
    def _membros_existem(self) -> ElencoCfg:
        """Todo `membro` citado por um time precisa ser o id de algum npc declarado."""
        ids_conhecidos = {npc.id for npc in self.npcs}
        for time in self.times:
            desconhecidos = [m for m in time.membros if m not in ids_conhecidos]
            if desconhecidos:
                raise ValueError(f"time '{time.nome}' cita npc(s) inexistente(s): {desconhecidos}")
        return self

    @model_validator(mode="after")
    def _cobre_todas_as_estacoes(self) -> ElencoCfg:
        """A união das responsabilidades dos times precisa cobrir TODAS as estações."""
        cobertas = {estacao for time in self.times for estacao in time.responsabilidades}
        faltando = set(Estacao) - cobertas
        if faltando:
            nomes = sorted(estacao.value for estacao in faltando)
            raise ValueError(f"nenhum time responde por: {nomes}")
        return self


# ── Tema: cores e emoji dos beats ────────────────────────────────────────────────
class BeatEstiloCfg(_Base):
    """A marca visual (emoji + estilo Rich) de um tipo de beat."""

    emoji: str
    cor: str


class TemaCfg(_Base):
    """O tema inteiro: um `BeatEstiloCfg` por `TipoBeat` narrável."""

    beats: dict[TipoBeat, BeatEstiloCfg]


# ── Cenário: consumo (discriminated union), pedidos, seed/escala ───────────────
class MesaCfg(_Base):
    """Consumo na mesa — espelha `dominio.pedido.NoLocal`."""

    tipo: Literal["mesa"]
    numero: Annotated[int, Field(ge=1)]


class ViagemCfg(_Base):
    """Retirada no balcão — espelha `dominio.pedido.ParaViagem`."""

    tipo: Literal["viagem"]


class DeliveryCfg(_Base):
    """Entrega — espelha `dominio.pedido.Delivery`."""

    tipo: Literal["delivery"]
    endereco: str


type ConsumoCfg = Annotated[MesaCfg | ViagemCfg | DeliveryCfg, Field(discriminator="tipo")]
"""Discriminated union: o campo `tipo` escolhe o variant certo direto, sem tentar os
três em ordem (`smart` union) — mais rápido e os erros apontam exatamente o variant
que deveria ter validado, em vez de uma lista confusa de "não bateu com nenhum"."""


class ItemPedidoCfg(_Base):
    """Uma linha de pedido crua: nome do item do cardápio + quantidade."""

    item: str
    quantidade: Annotated[int, Field(ge=1)]


class PedidoCfg(_Base):
    """Um pedido cru: como é consumido + as linhas."""

    consumo: ConsumoCfg
    itens: tuple[ItemPedidoCfg, ...]


def _escala_positiva(valor: float) -> float:
    """`AfterValidator` funcional: valida que a escala do relógio é > 0.

    Senão o tempo para ou anda pra trás — um estado sem sentido físico para a
    reprodução do turno.
    """
    if valor <= 0:
        raise ValueError(f"escala deve ser > 0, veio {valor}")
    return valor


class CenarioCfg(BaseSettings):
    """O cenário de demonstração: seed, escala do relógio e os pedidos do turno.

    CODEX: pydantic-settings — o cenário é o único config com um caso de uso real
        pra variar por AMBIENTE (rodar a demo com outra seed sem editar o JSON, ex.:
        `RESTAURANTE_SEED=7 uv run python demo_sim.py`). `BaseSettings` soma fontes:
        env var > arquivo JSON > default do campo (a ordem que `settings_customise_sources`
        declara abaixo) — a mesma "cascata de config" que qualquer app 12-factor usa,
        só que cada camada já sai VALIDADA pelo mesmo modelo.
    """

    model_config = SettingsConfigDict(
        env_prefix="RESTAURANTE_",
        json_file="config/cenario.json",
        # Explícito: sem isto, `JsonConfigSettingsSource` abre o arquivo com o encoding
        # padrão da plataforma (cp1252 no Windows) — corrompe acento em "Hambúrguer" etc.
        json_file_encoding="utf-8",
        extra="forbid",
    )

    seed: int = 42
    escala: Annotated[float, AfterValidator(_escala_positiva)] = 1.5
    pedidos: tuple[PedidoCfg, ...] = ()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,  # noqa: ARG003
        file_secret_settings: PydanticBaseSettingsSource,  # noqa: ARG003
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Precedência env > json > default: a fonte mais à esquerda vence o conflito."""
        return (env_settings, JsonConfigSettingsSource(settings_cls), init_settings)


__all__ = [
    "CARDAPIO_ADAPTER",
    "BeatEstiloCfg",
    "CenarioCfg",
    "DeliveryCfg",
    "ElencoCfg",
    "ItemCfg",
    "ItemPedidoCfg",
    "MesaCfg",
    "NpcCfg",
    "PedidoCfg",
    "PersonalidadeCfg",
    "TemaCfg",
    "TimeCfg",
    "ViagemCfg",
]

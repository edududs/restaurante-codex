"""Cardápio — os TIPOS puros de um item de cardápio (esqueleto, Parte I do Codex).

CODEX: PARSE, DON'T VALIDATE — o domínio só define a FORMA do fato (`ItemCardapio`,
    `Estacao`, `Categoria`); os DADOS ("o hambúrguer custa R$ 28,00 e sai da chapa")
    moram em `config/cardapio.json`, validados no boundary por
    `config/modelos.py::CARDAPIO_ADAPTER` e carregados por
    `config/carregador.py::carregar_cardapio()`. A fachada `config/catalogo.py::Cardapio`
    expõe a mesma API de sempre (`buscar`/`todos`) — o domínio nunca importa pydantic,
    só define o tipo que o boundary preenche.

CODEX: Estação como enum ↔ Mechanism/Policy — a estação diz *onde* o prato é feito;
    a cozinha (mecanismo) só sabe agendar por estação, não conhece pratos específicos.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from restaurante.dominio.dinheiro import Dinheiro


class Estacao(StrEnum):
    """Onde, na cozinha, um item é preparado. Base para o paralelismo (asyncio).

    CODEX: `StrEnum` (não `Enum` puro) — o `.value` já era string; herdar de
        `StrEnum` faz o próprio membro se comportar como string no round-trip
        JSON (o boundary em `config/` serializa/desserializa sem tradução manual).
        Comparação por identidade (`estacao is Estacao.CHAPA`) continua válida.
    """

    CHAPA = "chapa"
    FRITADEIRA = "fritadeira"
    SALADAS = "saladas"
    BAR = "bar"


class Categoria(StrEnum):
    """Classe do item — usada por *políticas* de preço (ex.: happy hour em bebidas)."""

    PRATO = "prato"
    ACOMPANHAMENTO = "acompanhamento"
    BEBIDA = "bebida"


@dataclass(frozen=True, slots=True)
class ItemCardapio:
    """Um fato do cardápio: nome, preço-base, onde é feito, quanto demora, categoria."""

    nome: str
    preco_base: Dinheiro
    estacao: Estacao
    segundos_preparo: float
    categoria: Categoria

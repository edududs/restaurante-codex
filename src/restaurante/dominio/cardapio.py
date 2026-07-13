"""Cardápio — a Fonte Única da Verdade dos itens e seus preços-base.

CODEX: SSoT / Single Source of Truth (Parte I).

    Cada *fato* ("o hambúrguer custa R$ 28,00 e sai da chapa") mora em UM lugar.
    Todo o resto — o total do pedido, o preço com desconto de happy hour, o texto
    do recibo — *deriva* daqui. Ninguém redigita o preço em outro lugar.

    A pergunta que materializa o princípio: *"já não existe algo centralizado?"*.
    Se o preço aparecesse também, digamos, hardcoded no serviço de pagamento, teríamos
    duas fontes — e a divergência entre elas não seria um risco, seria uma certeza no
    tempo. Aqui há uma fonte; o resto obedece e reflete.

CODEX: Estação como enum ↔ Mechanism/Policy — a estação diz *onde* o prato é feito;
    a cozinha (mecanismo) só sabe agendar por estação, não conhece pratos específicos.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from restaurante.dominio.dinheiro import Dinheiro
from restaurante.dominio.erros import ItemForaDoCardapio


class Estacao(Enum):
    """Onde, na cozinha, um item é preparado. Base para o paralelismo (asyncio)."""

    CHAPA = "chapa"
    FRITADEIRA = "fritadeira"
    SALADAS = "saladas"
    BAR = "bar"


class Categoria(Enum):
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


# A FONTE. Um dicionário nome -> fato. Imutável na prática (não editamos em runtime).
_ITENS: dict[str, ItemCardapio] = {
    item.nome: item
    for item in (
        ItemCardapio("Hambúrguer", Dinheiro.de_reais(28), Estacao.CHAPA, 6.0, Categoria.PRATO),
        ItemCardapio("Filé", Dinheiro.de_reais(52), Estacao.CHAPA, 9.0, Categoria.PRATO),
        ItemCardapio(
            "Batata frita", Dinheiro.de_reais(18), Estacao.FRITADEIRA, 4.0, Categoria.ACOMPANHAMENTO
        ),
        ItemCardapio(
            "Onion rings", Dinheiro.de_reais(22), Estacao.FRITADEIRA, 5.0, Categoria.ACOMPANHAMENTO
        ),
        ItemCardapio("Salada Caesar", Dinheiro.de_reais(26), Estacao.SALADAS, 3.0, Categoria.PRATO),
        ItemCardapio("Chopp", Dinheiro.de_reais(12), Estacao.BAR, 1.0, Categoria.BEBIDA),
        ItemCardapio("Suco natural", Dinheiro.de_reais(14), Estacao.BAR, 2.0, Categoria.BEBIDA),
    )
}


class Cardapio:
    """Fachada de leitura da fonte. Esconde a estrutura interna (Information Hiding)."""

    @staticmethod
    def buscar(nome: str) -> ItemCardapio:
        """Retorna o item ou falha alto se não existe (fail-fast, não retorna None)."""
        item = _ITENS.get(nome)
        if item is None:
            disponiveis = ", ".join(sorted(_ITENS))
            raise ItemForaDoCardapio(f"'{nome}' não está no cardápio. Temos: {disponiveis}.")
        return item

    @staticmethod
    def todos() -> tuple[ItemCardapio, ...]:
        """Projeção somente-leitura da fonte."""
        return tuple(_ITENS.values())

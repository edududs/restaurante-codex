"""Catálogo — a fachada de leitura do cardápio, agora carregado do boundary validado.

CODEX: PARSE, DON'T VALIDATE — quem decide QUANDO/COMO o cardápio é carregado e
    validado mora em `config/` (boundary), nunca no domínio. `dominio/cardapio.py`
    define só a FORMA do fato (`ItemCardapio`); esta classe é a fachada pública que
    `demo_sim.py`, `demo_tui.py`, `demo.py` e os testes usam — a MESMA API de sempre
    (`buscar`/`todos`), agora backed por `config/cardapio.json` em vez de um dict
    hardcoded no código. Trocar a fonte (JSON hoje, outro formato amanhã) não pede
    mudar quem consome `Cardapio` — só este arquivo e `carregador.py`.
"""

from __future__ import annotations

from restaurante.config.carregador import carregar_cardapio
from restaurante.dominio.cardapio import ItemCardapio
from restaurante.dominio.erros import ItemForaDoCardapio


class Cardapio:
    """Fachada de leitura do cardápio validado. Esconde a estrutura interna."""

    @staticmethod
    def buscar(nome: str) -> ItemCardapio:
        """Retorna o item ou falha alto se não existe (fail-fast, não retorna None)."""
        itens = carregar_cardapio()
        item = itens.get(nome)
        if item is None:
            disponiveis = ", ".join(sorted(itens))
            raise ItemForaDoCardapio(f"'{nome}' não está no cardápio. Temos: {disponiveis}.")
        return item

    @staticmethod
    def todos() -> tuple[ItemCardapio, ...]:
        """Projeção somente-leitura do cardápio validado."""
        return tuple(carregar_cardapio().values())


__all__ = ["Cardapio"]

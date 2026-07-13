"""Erros de domínio — o vocabulário de falhas do restaurante.

CODEX: Fail Fast / Fail Loud (Parte IV).
    Um erro deve ser detectado o mais perto possível da origem e falhar de forma
    barulhenta, em vez de deixar um estado inválido seguir viagem e explodir três
    camadas depois — onde o stack trace não ajuda a achar a causa.

    Por isso cada regra violada tem um tipo de erro *nomeado*: quem lê o `except`
    sabe exatamente o que deu errado, e a mensagem aponta a fonte, não o sintoma.
"""

from __future__ import annotations


class ErroDeDominio(Exception):
    """Raiz de todos os erros de regra de negócio do restaurante.

    Ter uma raiz comum deixa quem chama escolher a granularidade do `except`:
    pegar tudo (`ErroDeDominio`) ou um caso específico (`TransicaoInvalida`).
    """


class ValorMonetarioInvalido(ErroDeDominio):
    """Tentou-se construir dinheiro num estado impossível (ex.: preço negativo)."""


class ItemForaDoCardapio(ErroDeDominio):
    """Pediram um item que não existe na fonte da verdade (o cardápio)."""


class PedidoVazio(ErroDeDominio):
    """Tentou-se fechar/preparar um pedido sem nenhum item."""


class TransicaoInvalida(ErroDeDominio):
    """Tentou-se mover o pedido para um estado que a máquina não permite.

    CODEX: Make Illegal States Unrepresentable — quando o *tipo* não consegue
    impedir a transição, a máquina de estados a rejeita em runtime, cedo e alto.
    """

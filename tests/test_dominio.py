"""Testes do domínio puro — dinheiro, cardápio e a máquina de estados do pedido."""

from __future__ import annotations

import pytest

from restaurante.config.catalogo import Cardapio
from restaurante.dominio.dinheiro import Dinheiro
from restaurante.dominio.erros import (
    ItemForaDoCardapio,
    PedidoVazio,
    TransicaoInvalida,
    ValorMonetarioInvalido,
)
from restaurante.dominio.pedido import Delivery, NoLocal, ParaViagem, Pedido


def test_dinheiro_nao_aceita_negativo() -> None:
    with pytest.raises(ValorMonetarioInvalido):
        Dinheiro(-1)


def test_dinheiro_soma_e_multiplica_em_centavos() -> None:
    assert (Dinheiro.de_reais(10) + Dinheiro.de_reais(5, 50)).centavos == 1550
    assert (Dinheiro.de_reais(12, 90) * 3).centavos == 3870


def test_dinheiro_desconto_e_formatacao() -> None:
    assert Dinheiro.de_reais(20).aplicar_desconto(50) == Dinheiro.de_reais(10)
    assert str(Dinheiro.de_reais(8, 5)) == "R$ 8,05"


def test_cardapio_e_fonte_da_verdade() -> None:
    assert Cardapio.buscar("Chopp").preco_base == Dinheiro.de_reais(12)
    with pytest.raises(ItemForaDoCardapio):
        Cardapio.buscar("Sushi")


def test_confirmar_pedido_vazio_falha() -> None:
    with pytest.raises(PedidoVazio):
        Pedido(consumo=ParaViagem()).confirmar()


def test_transicao_ilegal_e_recusada() -> None:
    confirmado = Pedido(consumo=NoLocal(mesa=1)).com_item(Cardapio.buscar("Chopp")).confirmar()
    # confirmado -> entregue não existe no mapa de transições:
    with pytest.raises(TransicaoInvalida):
        confirmado.entregar()


def test_nao_da_pra_adicionar_item_apos_confirmar() -> None:
    confirmado = Pedido(consumo=NoLocal(mesa=1)).com_item(Cardapio.buscar("Chopp")).confirmar()
    with pytest.raises(TransicaoInvalida):
        confirmado.com_item(Cardapio.buscar("Filé"))


def test_ciclo_de_vida_feliz() -> None:
    entregue = (
        Pedido(consumo=NoLocal(mesa=1))
        .com_item(Cardapio.buscar("Chopp"))
        .confirmar()
        .iniciar_preparo()
        .marcar_pronto()
        .entregar()
    )
    assert entregue.estado.value == "entregue"


def test_consumo_e_tipo_soma_exaustivo() -> None:
    def descreve(consumo: NoLocal | ParaViagem | Delivery) -> str:
        match consumo:
            case NoLocal(mesa):
                return f"mesa {mesa}"
            case ParaViagem():
                return "balcão"
            case Delivery(endereco):
                return endereco

    assert descreve(NoLocal(mesa=5)) == "mesa 5"
    assert descreve(ParaViagem()) == "balcão"
    assert descreve(Delivery(endereco="Rua X")) == "Rua X"

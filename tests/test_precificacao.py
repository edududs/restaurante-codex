"""Testes das políticas de preço e do mecanismo de cálculo do total."""

from __future__ import annotations

from restaurante.adaptadores.precos import PrecoDeTabela, PrecoHappyHour
from restaurante.config.catalogo import Cardapio
from restaurante.dominio.dinheiro import Dinheiro
from restaurante.dominio.pedido import NoLocal, Pedido
from restaurante.portas.precificacao import ContextoPreco
from restaurante.servicos.conta import calcular_total


def test_tabela_ignora_a_hora() -> None:
    chopp = Cardapio.buscar("Chopp")
    politica = PrecoDeTabela()
    assert politica.preco_do_item(chopp, ContextoPreco(hora=18)) == Dinheiro.de_reais(12)
    assert politica.preco_do_item(chopp, ContextoPreco(hora=9)) == Dinheiro.de_reais(12)


def test_happy_hour_desconta_bebida_na_janela() -> None:
    chopp = Cardapio.buscar("Chopp")
    politica = PrecoHappyHour()
    assert politica.preco_do_item(chopp, ContextoPreco(hora=18)) == Dinheiro.de_reais(6)


def test_happy_hour_nao_desconta_fora_da_janela() -> None:
    chopp = Cardapio.buscar("Chopp")
    politica = PrecoHappyHour()
    assert politica.preco_do_item(chopp, ContextoPreco(hora=13)) == Dinheiro.de_reais(12)


def test_happy_hour_fronteira_inicio_e_inclusiva() -> None:
    # 17h é o primeiro instante do happy hour → já vale o desconto.
    chopp = Cardapio.buscar("Chopp")
    assert PrecoHappyHour().preco_do_item(chopp, ContextoPreco(hora=17)) == Dinheiro.de_reais(6)


def test_happy_hour_fronteira_fim_e_exclusiva() -> None:
    # 20h é o fim EXCLUSIVO (janela 17 <= hora < 20) → preço cheio, sem desconto.
    # Este teste fixa a fronteira: mata a mutação `< _HAPPY_HOUR_FIM` -> `<=`.
    chopp = Cardapio.buscar("Chopp")
    assert PrecoHappyHour().preco_do_item(chopp, ContextoPreco(hora=20)) == Dinheiro.de_reais(12)


def test_happy_hour_so_vale_para_bebida() -> None:
    hamburguer = Cardapio.buscar("Hambúrguer")
    politica = PrecoHappyHour()
    # comida não entra no desconto, mesmo dentro da janela:
    assert politica.preco_do_item(hamburguer, ContextoPreco(hora=18)) == Dinheiro.de_reais(28)


def test_mesmo_mecanismo_totais_diferentes() -> None:
    comanda = (
        Pedido(consumo=NoLocal(mesa=3))
        .com_item(Cardapio.buscar("Chopp"), 4)
        .com_item(Cardapio.buscar("Hambúrguer"), 2)
    )
    ctx = ContextoPreco(hora=18)
    # 4×12 + 2×28 = 104
    assert calcular_total(comanda, PrecoDeTabela(), ctx) == Dinheiro.de_reais(104)
    # 4×6 (happy hour) + 2×28 = 80
    assert calcular_total(comanda, PrecoHappyHour(), ctx) == Dinheiro.de_reais(80)

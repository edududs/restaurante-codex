"""Testes end-to-end — o sistema montado pelo composition root, ponta a ponta.

Cobrem os três caminhos que o Codex/TLC pede na camada e2e: happy, edge e error.
De quebra, mostram o poder das portas: trocamos os adapters reais por *espiões* no
teste (implementando a mesma interface) para observar o fluxo — sem tocar no domínio.
"""

from __future__ import annotations

import pytest

from restaurante.adaptadores.pagamento_fake import PagamentoFake
from restaurante.adaptadores.precos import PrecoDeTabela, PrecoHappyHour
from restaurante.adaptadores.repositorio_memoria import RepositorioMemoria
from restaurante.app import montar_restaurante
from restaurante.config.catalogo import Cardapio
from restaurante.dominio.dinheiro import Dinheiro
from restaurante.dominio.erros import PedidoVazio
from restaurante.dominio.pedido import Delivery, EstadoPedido, NoLocal, ParaViagem, Pedido
from restaurante.portas.pagamento import Comprovante
from restaurante.portas.precificacao import ContextoPreco
from restaurante.servicos.balcao import ServicoBalcao
from restaurante.servicos.cozinha import Cozinha


class _NotificadorEspiao:
    """Test double da porta `Notificador` — guarda as mensagens em vez de enviar."""

    def __init__(self) -> None:
        self.mensagens: list[str] = []

    async def notificar(self, mensagem: str) -> None:
        self.mensagens.append(mensagem)


class _PagamentoEspiao:
    """Test double da porta `Pagamento` — registra quanto foi cobrado."""

    def __init__(self) -> None:
        self.cobrado: Dinheiro | None = None

    async def cobrar(self, valor: Dinheiro) -> Comprovante:
        self.cobrado = valor
        return Comprovante(id="pay_teste", valor=valor)


async def test_e2e_happy_pedido_percorre_ate_entregue() -> None:
    restaurante = montar_restaurante(escala=0.02)
    pedido = (
        Pedido(consumo=Delivery(endereco="Rua A, 1"))
        .com_item(Cardapio.buscar("Hambúrguer"))
        .com_item(Cardapio.buscar("Batata frita"))
    )
    final = await restaurante.balcao.atender(pedido, ContextoPreco(hora=13))

    assert final.estado is EstadoPedido.ENTREGUE
    persistido = await restaurante.repositorio.buscar(final.id)
    assert persistido is not None
    assert persistido.estado is EstadoPedido.ENTREGUE


async def test_e2e_notifica_confirmacao_e_pronto() -> None:
    espiao = _NotificadorEspiao()
    balcao = ServicoBalcao(
        repositorio=RepositorioMemoria(),
        pagamento=PagamentoFake(),
        notificador=espiao,
        estrategia_preco=PrecoDeTabela(),
        cozinha=Cozinha(escala=0.02),
    )
    pedido = Pedido(consumo=NoLocal(mesa=4)).com_item(Cardapio.buscar("Chopp"))
    await balcao.atender(pedido, ContextoPreco(hora=13))

    assert any("confirmado" in m for m in espiao.mensagens)
    assert any("PRONTO" in m for m in espiao.mensagens)


async def test_e2e_error_pedido_vazio_propaga_falha() -> None:
    restaurante = montar_restaurante(escala=0.02)
    vazio = Pedido(consumo=ParaViagem())
    with pytest.raises(PedidoVazio):
        await restaurante.balcao.cobrar_e_confirmar(vazio, ContextoPreco(hora=13))


async def test_e2e_happy_hour_desconta_no_valor_cobrado() -> None:
    pagamento = _PagamentoEspiao()
    balcao = ServicoBalcao(
        repositorio=RepositorioMemoria(),
        pagamento=pagamento,
        notificador=_NotificadorEspiao(),
        estrategia_preco=PrecoHappyHour(),
        cozinha=Cozinha(escala=0.02),
    )
    # 2 chopps às 18h: 2×6 (happy hour) = 12, não 2×12 = 24.
    pedido = Pedido(consumo=NoLocal(mesa=1)).com_item(Cardapio.buscar("Chopp"), 2)
    await balcao.cobrar_e_confirmar(pedido, ContextoPreco(hora=18))

    assert pagamento.cobrado == Dinheiro.de_reais(12)

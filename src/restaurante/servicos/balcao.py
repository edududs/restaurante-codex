"""ServicoBalcao — o app-service que orquestra o ciclo de vida de um pedido.

CODEX: SoC / arquitetura em camadas (Parte II). Este é o serviço de orquestração de
    negócio: ele conhece a *sequência* (confirmar → cobrar → salvar → preparar → entregar)
    mas delega cada passo às portas. Ele não sabe imprimir, não sabe SQL, não sabe o
    gateway. Recebe tudo pronto no construtor — injeção de dependência pura.

CODEX: Law of Demeter (Parte II). O serviço fala só com seus colaboradores diretos
    (as portas injetadas). Não navega `pedido.linhas[0].item.estacao...` pra tomar
    decisão — pede ao domínio (`pedido.confirmar()`) e à cozinha (`preparar`).
"""

from __future__ import annotations

from restaurante.dominio.pedido import Pedido
from restaurante.portas.notificacao import Notificador
from restaurante.portas.pagamento import Comprovante, Pagamento
from restaurante.portas.precificacao import ContextoPreco, EstrategiaPreco
from restaurante.portas.repositorio import RepositorioPedidos
from restaurante.servicos.conta import calcular_total
from restaurante.servicos.cozinha import Cozinha, Narrador, sem_narracao


class ServicoBalcao:
    """Recebe pedidos e conduz cada um do 'confirmado' ao 'entregue'."""

    def __init__(
        self,
        repositorio: RepositorioPedidos,
        pagamento: Pagamento,
        notificador: Notificador,
        estrategia_preco: EstrategiaPreco,
        cozinha: Cozinha,
    ) -> None:
        self._repositorio = repositorio
        self._pagamento = pagamento
        self._notificador = notificador
        self._estrategia = estrategia_preco
        self._cozinha = cozinha

    async def cobrar_e_confirmar(
        self,
        pedido: Pedido,
        contexto: ContextoPreco,
    ) -> tuple[Pedido, Comprovante]:
        """Confirma o pedido (fail-fast se vazio), cobra o total e persiste."""
        confirmado = pedido.confirmar()  # levanta PedidoVazio se não houver itens
        total = calcular_total(confirmado, self._estrategia, contexto)
        comprovante = await self._pagamento.cobrar(total)
        await self._repositorio.salvar(confirmado)
        await self._notificador.notificar(
            f"Pedido {confirmado.id} confirmado. Total {total} (pago: {comprovante.id})."
        )
        return confirmado, comprovante

    async def atender(
        self,
        pedido: Pedido,
        contexto: ContextoPreco,
        narrar: Narrador = sem_narracao,
    ) -> Pedido:
        """Executa o ciclo completo: confirma, cobra, prepara na cozinha e entrega."""
        atual, _ = await self.cobrar_e_confirmar(pedido, contexto)

        atual = atual.iniciar_preparo()
        await self._repositorio.salvar(atual)
        await self._cozinha.preparar(atual, narrar)

        atual = atual.marcar_pronto()
        await self._repositorio.salvar(atual)
        await self._notificador.notificar(f"Pedido {atual.id} está PRONTO! 🍽️")

        atual = atual.entregar()
        await self._repositorio.salvar(atual)
        return atual

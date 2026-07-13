"""Pedido — a máquina de estados e o tipo-soma que blindam o fluxo.

Este arquivo concentra dois princípios do Codex que costumam ser mal aplicados.

CODEX: Make Illegal States Unrepresentable (Parte IV) — via `Consumo`.
    Um pedido é consumido de UMA de três formas: na mesa, para viagem, ou delivery.
    A modelagem ingênua seria três campos nuláveis (`mesa`, `para_viagem`, `endereco`)
    — que permitem os DOIS estados ilegais: todos nulos, ou mais de um preenchido.
    Em vez disso usamos um **tipo-soma** (união de dataclasses): só um dos casos pode
    existir por construção. O `match` no consumo é exaustivo — o type checker cobra.

CODEX: Fail Fast + máquina de estados (Parte IV) — via `EstadoPedido`.
    As transições válidas moram num único mapa (a SSoT da máquina). Tentar uma
    transição ilegal falha alto (`TransicaoInvalida`), não silenciosamente. O `Pedido`
    é imutável: cada transição devolve um NOVO pedido, nunca muta o atual.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from enum import Enum

from restaurante.dominio.cardapio import ItemCardapio
from restaurante.dominio.erros import PedidoVazio, TransicaoInvalida


# ── Consumo: o tipo-soma (só um caso existe por vez) ───────────────────────────
@dataclass(frozen=True, slots=True)
class NoLocal:
    """Consumo na mesa. Carrega — e exige — o número da mesa."""

    mesa: int


@dataclass(frozen=True, slots=True)
class ParaViagem:
    """Retirada no balcão. Não carrega dado nenhum — e é impossível dar-lhe um."""


@dataclass(frozen=True, slots=True)
class Delivery:
    """Entrega. Carrega — e exige — o endereço. Impossível existir sem ele."""

    endereco: str


Consumo = NoLocal | ParaViagem | Delivery
"""União fechada: a decisão 'como o cliente consome' só admite estes três casos."""


# ── Estado: a máquina ──────────────────────────────────────────────────────────
class EstadoPedido(Enum):
    """Estados por onde um pedido passa. As transições legais estão em `_TRANSICOES`."""

    RASCUNHO = "rascunho"
    CONFIRMADO = "confirmado"
    EM_PREPARO = "em_preparo"
    PRONTO = "pronto"
    ENTREGUE = "entregue"
    CANCELADO = "cancelado"


# CODEX: SSoT da máquina de estados — a regra "quem pode virar o quê" existe UMA vez.
# Trocar o fluxo do restaurante = editar este mapa, e mais nada.
_TRANSICOES: dict[EstadoPedido, frozenset[EstadoPedido]] = {
    EstadoPedido.RASCUNHO: frozenset({EstadoPedido.CONFIRMADO, EstadoPedido.CANCELADO}),
    EstadoPedido.CONFIRMADO: frozenset({EstadoPedido.EM_PREPARO, EstadoPedido.CANCELADO}),
    EstadoPedido.EM_PREPARO: frozenset({EstadoPedido.PRONTO}),
    EstadoPedido.PRONTO: frozenset({EstadoPedido.ENTREGUE}),
    EstadoPedido.ENTREGUE: frozenset(),
    EstadoPedido.CANCELADO: frozenset(),
}


@dataclass(frozen=True, slots=True)
class LinhaPedido:
    """Um item do cardápio com a quantidade pedida."""

    item: ItemCardapio
    quantidade: int


@dataclass(frozen=True, slots=True)
class Pedido:
    """Um pedido imutável. Toda operação devolve um novo `Pedido`."""

    consumo: Consumo
    linhas: tuple[LinhaPedido, ...] = ()
    estado: EstadoPedido = EstadoPedido.RASCUNHO
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def com_item(self, item: ItemCardapio, quantidade: int = 1) -> Pedido:
        """Adiciona um item. Só permitido enquanto o pedido é RASCUNHO."""
        if self.estado is not EstadoPedido.RASCUNHO:
            raise TransicaoInvalida(f"Não dá pra adicionar item num pedido {self.estado.value}.")
        return replace(self, linhas=(*self.linhas, LinhaPedido(item, quantidade)))

    def _transicionar(self, novo: EstadoPedido) -> Pedido:
        # CODEX: Fail Fast — a transição ilegal para aqui, não três camadas à frente.
        if novo not in _TRANSICOES[self.estado]:
            raise TransicaoInvalida(f"Transição ilegal: {self.estado.value} -> {novo.value}.")
        return replace(self, estado=novo)

    def confirmar(self) -> Pedido:
        """Cliente fechou a conta. Um pedido vazio não pode ser confirmado (fail-fast)."""
        if not self.linhas:
            raise PedidoVazio("Não dá pra confirmar um pedido sem itens.")
        return self._transicionar(EstadoPedido.CONFIRMADO)

    def iniciar_preparo(self) -> Pedido:
        """Cozinha assumiu o pedido."""
        return self._transicionar(EstadoPedido.EM_PREPARO)

    def marcar_pronto(self) -> Pedido:
        """Todos os itens saíram."""
        return self._transicionar(EstadoPedido.PRONTO)

    def entregar(self) -> Pedido:
        """Entregue ao cliente (na mesa, balcão ou porta)."""
        return self._transicionar(EstadoPedido.ENTREGUE)

    def cancelar(self) -> Pedido:
        """Cancela — só antes de entrar em preparo (ver `_TRANSICOES`)."""
        return self._transicionar(EstadoPedido.CANCELADO)

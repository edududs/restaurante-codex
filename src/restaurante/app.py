"""Composition root — o único lugar que conhece as implementações concretas.

CODEX: Dependency Injection na prática (Parte III). Repare que este é o ÚNICO módulo do
    sistema que importa adapters concretos (`RepositorioMemoria`, `PagamentoFake`, ...).
    Todo o resto fala com as portas. Quer produção de verdade? Troque as linhas de
    montagem aqui por `PagamentoStripe`, `RepositorioPostgres`, `NotificadorWhatsApp` —
    e nenhum serviço, nenhuma regra de domínio, precisa mudar. Este arquivo é a "tomada"
    onde os componentes se conectam.
"""

from __future__ import annotations

from dataclasses import dataclass

from restaurante.adaptadores.notificador_console import NotificadorConsole
from restaurante.adaptadores.pagamento_fake import PagamentoFake
from restaurante.adaptadores.precos import PrecoDeTabela, PrecoHappyHour
from restaurante.adaptadores.repositorio_memoria import RepositorioMemoria
from restaurante.dominio.cardapio import Estacao
from restaurante.portas.repositorio import RepositorioPedidos
from restaurante.servicos.balcao import ServicoBalcao
from restaurante.servicos.cozinha import Cozinha


@dataclass(frozen=True, slots=True)
class Restaurante:
    """O sistema montado e pronto para atender. Expõe o balcão e o repositório."""

    balcao: ServicoBalcao
    repositorio: RepositorioPedidos


def montar_restaurante(
    *,
    happy_hour: bool = False,
    escala: float = 1.0,
    capacidade: dict[Estacao, int] | None = None,
) -> Restaurante:
    """Instancia e injeta todos os componentes. Muda a política de preço por um flag."""
    repositorio = RepositorioMemoria()
    pagamento = PagamentoFake()
    notificador = NotificadorConsole()
    # A escolha da política de preço mora aqui, não enterrada no cálculo do total.
    estrategia = PrecoHappyHour() if happy_hour else PrecoDeTabela()
    cozinha = Cozinha(capacidade=capacidade, escala=escala)

    balcao = ServicoBalcao(
        repositorio=repositorio,
        pagamento=pagamento,
        notificador=notificador,
        estrategia_preco=estrategia,
        cozinha=cozinha,
    )
    return Restaurante(balcao=balcao, repositorio=repositorio)

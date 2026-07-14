"""Teste do dashboard Textual (Fase 4): headless, prova que os widgets são populados."""

from __future__ import annotations

import io

from rich.console import Console
from textual.visual import VisualType
from textual.widgets import RichLog, Static

from restaurante.adaptadores.apresentador_textual import SimuladorApp
from restaurante.adaptadores.elenco import criar_elenco
from restaurante.adaptadores.relogio_fake import RelogioFake
from restaurante.adaptadores.situacoes_sims import SituacoesSims
from restaurante.config.catalogo import Cardapio
from restaurante.dominio.pedido import NoLocal, Pedido
from restaurante.servicos.motor import planejar_turno

_TETO_ITERACOES_PAUSA = 200


def _pedidos_de_teste() -> list[Pedido]:
    """Um pedido pequeno, cobrindo chapa e bar — o bastante para exercitar o dashboard."""
    pedido = (
        Pedido(consumo=NoLocal(mesa=3))
        .com_item(Cardapio.buscar("Hambúrguer"))
        .com_item(Cardapio.buscar("Chopp"))
    )
    return [pedido]


def _texto_de(conteudo: VisualType) -> str:
    """Renderiza o `.content` de um Static (Rich renderable) para string, para asserções.

    `Console.print` aceita `*objects: Any` (é o próprio design da API do rich), então
    passar o `VisualType` do Textual direto é seguro em runtime — só o type checker
    não consegue provar a interseção entre os dois vocabulários de tipo.
    """
    buffer = io.StringIO()
    Console(file=buffer, width=120).print(conteudo)
    return buffer.getvalue()


async def test_dashboard_popula_widgets() -> None:
    roster, times = criar_elenco()
    plano = planejar_turno(_pedidos_de_teste(), roster, times, SituacoesSims(), seed=1)
    app = SimuladorApp(plano, RelogioFake(), {}, roster)  # RelogioFake = instantâneo

    async with app.run_test() as pilot:
        # Espera o worker do turno terminar. `wait_for_complete` existe no WorkerManager
        # desta versão do Textual; um teto de pausas evita loop infinito se não existisse.
        if hasattr(app.workers, "wait_for_complete"):
            # O stub do Textual deixa o generic de Worker parcialmente Unknown — não é
            # coisa nossa para corrigir, só documentar o porquê do ignore.
            await app.workers.wait_for_complete()  # pyright: ignore[reportUnknownMemberType]
        else:  # pragma: no cover - rede de segurança para outra versão do Textual
            for _ in range(_TETO_ITERACOES_PAUSA):
                if not app.workers:
                    break
                await pilot.pause()
        await pilot.pause()

        # O feed recebeu conteúdo (o turno narrou algo).
        feed = app.query_one("#feed", RichLog)
        assert len(feed.lines) > 0
        texto_feed = "".join(strip.text for strip in feed.lines)
        assert "recebido" in texto_feed
        assert "concluiu" in texto_feed
        assert "pronto" in texto_feed

        # O painel de pedidos foi atualizado: o pedido terminou "pronto".
        painel_pedidos = app.query_one("#painel-pedidos", Static)
        assert "pronto" in _texto_de(painel_pedidos.content)

        # O painel de equipe reflete a evolução de pelo menos um NPC (energia caiu do
        # valor inicial de 100 — só acontece se `_tarefa_concluida` atualizou o estado).
        # Acesso a estado privado do adapter é proposital aqui (teste gray-box do que
        # alimenta o widget), por isso os ignores documentados de lint e type checker.
        energias = app._energia.values()  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
        assert any(energia < 100 for energia in energias)
        painel_equipe = app.query_one("#painel-equipe", Static)
        texto_equipe = _texto_de(painel_equipe.content)
        assert any(nome in texto_equipe for nome in roster)

        # A app não crashou e sinalizou o fim do turno.
        assert app.title == "Fim de turno"

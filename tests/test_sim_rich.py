"""Teste do renderer Rich (Fase 3): prova, em runtime, que o `match` é exaustivo."""

from __future__ import annotations

import io

from rich.console import Console

from restaurante.adaptadores.apresentador_rich import ApresentadorRich
from restaurante.dominio.beats import Beat, TipoBeat
from restaurante.dominio.cardapio import Estacao
from restaurante.dominio.pessoas import Humor
from restaurante.portas.apresentador import (
    BeatOcorreu,
    PedidoPronto,
    PedidoRecebido,
    ResumoNPC,
    TarefaConcluida,
    TarefaIniciada,
    TurnoResumo,
)
from restaurante.servicos.modelo_tempo import DuracaoTarefa


def _emitir_um_de_cada(largura: int) -> str:
    """Alimenta um evento de cada tipo de SimEvent e devolve a saída renderizada."""
    buffer = io.StringIO()
    console = Console(file=buffer, width=largura)
    apresentador = ApresentadorRich(bios={"Ana": "craque da chapa"}, console=console)

    duracao = DuracaoTarefa(
        base=6.0,
        mult_skill=0.9,
        mult_fadiga=1.1,
        mult_xp=0.95,
        soma_beats=0.5,
        total=6.5,
        beats=(Beat(TipoBeat.INSPIRADO, "fluiu", -0.3),),
    )
    resumo = ResumoNPC(
        nome="Ana",
        tarefas=3,
        tempo_trabalhado=18.5,
        xp_ganho=45,
        eventos_sofridos=1,
        energia_final=76,
        humor_final=Humor.NEUTRO,
    )

    # Um evento de CADA um dos 6 tipos de SimEvent.
    apresentador.emitir(PedidoRecebido(t=0.0, pedido_id="p1", descricao="mesa 5"))
    apresentador.emitir(
        TarefaIniciada(t=0.0, pessoa="Ana", item="Hambúrguer", estacao=Estacao.CHAPA)
    )
    apresentador.emitir(
        BeatOcorreu(
            t=1.0,
            pessoa="Ana",
            item="Hambúrguer",
            beat=Beat(TipoBeat.ATRAPALHOU, "se atrapalhou", 1.2),
        )
    )
    apresentador.emitir(
        TarefaConcluida(
            t=6.5, pessoa="Ana", item="Hambúrguer", duracao=duracao, energia=88, humor=Humor.NEUTRO
        )
    )
    apresentador.emitir(PedidoPronto(t=6.5, pedido_id="p1", total_s=6.5))
    apresentador.emitir(TurnoResumo(t=6.5, npcs=(resumo,)))

    return buffer.getvalue()


def test_renderer_processa_todos_os_tipos_de_evento_sem_crashar() -> None:
    # Prova em runtime que o `match` de emitir() cobre os 6 tipos (exaustividade).
    saida = _emitir_um_de_cada(largura=100)
    assert saida != ""
    assert "se atrapalhou" in saida  # o stream de beats renderiza
    assert "mesa 5" in saida  # o pedido recebido renderiza


def test_tabela_de_stats_tem_todas_as_colunas() -> None:
    # Discrimina remoção de coluna (Rich auto-estende, então o CABEÇALHO é o que some).
    # Largura folgada para os títulos não quebrarem em várias linhas.
    saida = _emitir_um_de_cada(largura=200)
    for coluna in ("NPC", "Tarefas", "Tempo", "XP", "Eventos", "Energia", "Humor", "Bio"):
        assert coluna in saida, f"coluna '{coluna}' sumiu da tabela de stats"
    assert "craque da chapa" in saida  # a bio do NPC aparece
    assert "neutro" in saida  # o humor aparece

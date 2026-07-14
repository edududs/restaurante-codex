"""Apresentador Rich — a pele. Consome `SimEvent`, desenha bonito, não reimplementa lógica.

CODEX: Ports & Adapters + mechanism×policy (Parte III). Este é o ÚNICO arquivo do
    projeto que importa `rich`. O motor (`servicos/motor.py`) não sabe que existe
    terminal, cor ou tabela — ele só emite fatos (`SimEvent`). Este adapter decide como
    esses fatos viram pixels: blocos coloridos em stream durante o turno, e uma
    timeline/Gantt + tabela de stats ao final. Trocar a pele (log simples, JSON, TUI
    diferente) é trocar este arquivo — o domínio e o motor não mudam uma linha.

CODEX: Make Illegal States Unrepresentable, provado em runtime. `SimEvent` é uma união
    fechada (Parte IV); o `match` em `emitir` é exaustivo (o pyright cobra em tempo de
    tipo) e `tests/test_sim_rich.py` prova, em runtime, que os 6 casos são tratados sem
    exceção.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from restaurante.dominio.beats import TipoBeat
from restaurante.dominio.pessoas import Humor
from restaurante.portas.apresentador import (
    BeatOcorreu,
    PedidoPronto,
    PedidoRecebido,
    ResumoNPC,
    SimEvent,
    TarefaConcluida,
    TarefaIniciada,
    TurnoResumo,
)

# Cor por tipo de beat — a "temperatura emocional" de cada micro-evento (SSoT de estilo).
_COR_BEAT: dict[TipoBeat, str] = {
    TipoBeat.CONCENTRADO: "white",
    TipoBeat.INSPIRADO: "green",
    TipoBeat.ATRAPALHOU: "red",
    TipoBeat.DISTRAIU: "dim",
    TipoBeat.INTERAGIU: "cyan",
    TipoBeat.EVENTO: "bold magenta",
}

_COR_HUMOR: dict[Humor, str] = {
    Humor.INSPIRADO: "green",
    Humor.NEUTRO: "white",
    Humor.CANSADO: "yellow",
    Humor.ESTRESSADO: "red",
}

# Paleta cíclica para diferenciar itens na timeline (cosmético — não é fonte de dado).
_PALETA_GANTT = ("cyan", "magenta", "green", "yellow", "blue", "bright_red")

_LARGURA_GANTT = 40
_LARGURA_BARRA_ENERGIA = 10


def _cor_item(item: str) -> str:
    """Escolhe uma cor estável para o item, só para diferenciar barras na timeline."""
    indice = sum(ord(c) for c in item) % len(_PALETA_GANTT)
    return _PALETA_GANTT[indice]


def _barra_energia(energia: int) -> Text:
    """Desenha a energia final como uma mini-barra de blocos coloridos por faixa."""
    preenchidos = round(energia / 100 * _LARGURA_BARRA_ENERGIA)
    cor = "green" if energia >= 60 else "yellow" if energia >= 30 else "red"  # noqa: PLR2004
    texto = Text()
    texto.append("█" * preenchidos, style=cor)
    texto.append("░" * (_LARGURA_BARRA_ENERGIA - preenchidos), style="dim")
    texto.append(f" {energia}", style=cor)
    return texto


def _humor_texto(humor: Humor) -> Text:
    """Renderiza o humor com a cor correspondente."""
    return Text(humor.value, style=_COR_HUMOR[humor])


@dataclass(frozen=True, slots=True)
class _TarefaNaLinha:
    """Bookkeeping interno: uma tarefa já concluída, para desenhar a timeline final."""

    item: str
    inicio: float
    fim: float


class ApresentadorRich:
    """Implementa a porta `Apresentador`: stream de blocos + timeline/stats ao final."""

    def __init__(self, bios: dict[str, str] | None = None, console: Console | None = None) -> None:
        """Recebe as bios dos NPCs (para o painel final) e, opcionalmente, um Console."""
        self._console = console if console is not None else Console()
        self._bios = bios if bios is not None else {}
        self._inicio_atual: dict[str, tuple[str, float]] = {}
        self._timeline: dict[str, list[_TarefaNaLinha]] = defaultdict(list)

    def emitir(self, evento: SimEvent) -> None:
        """Despacha o evento para o desenho certo — o `match` cobre a união inteira."""
        match evento:
            case PedidoRecebido():
                self._pedido_recebido(evento)
            case TarefaIniciada():
                self._tarefa_iniciada(evento)
            case BeatOcorreu():
                self._beat_ocorreu(evento)
            case TarefaConcluida():
                self._tarefa_concluida(evento)
            case PedidoPronto():
                self._pedido_pronto(evento)
            case TurnoResumo():
                self._turno_resumo(evento)

    # ── Durante: stream de blocos ────────────────────────────────────────────
    def _pedido_recebido(self, evento: PedidoRecebido) -> None:
        self._console.rule(
            f"[bold blue]Pedido {evento.pedido_id}[/] recebido — {evento.descricao}",
            style="blue",
        )

    def _tarefa_iniciada(self, evento: TarefaIniciada) -> None:
        self._inicio_atual[evento.pessoa] = (evento.item, evento.t)
        self._console.print(
            f"  [bold]{evento.pessoa}[/] assume [italic]{evento.item}[/] na {evento.estacao.value}"
        )

    def _beat_ocorreu(self, evento: BeatOcorreu) -> None:
        cor = _COR_BEAT[evento.beat.tipo]
        delta = f"{evento.beat.delta_s:+.1f}s"
        self._console.print(f"    [{cor}]· {evento.beat.texto} ({delta})[/{cor}]")

    def _tarefa_concluida(self, evento: TarefaConcluida) -> None:
        item, inicio = self._inicio_atual.pop(evento.pessoa, (evento.item, evento.t))
        self._timeline[evento.pessoa].append(_TarefaNaLinha(item=item, inicio=inicio, fim=evento.t))
        d = evento.duracao
        self._console.print(
            f"  [bold green]✔ {evento.pessoa} concluiu {evento.item}[/] em {d.total:.1f}s "
            f"[dim](skill×{d.mult_skill:.2f} fadiga×{d.mult_fadiga:.2f} "
            f"xp×{d.mult_xp:.2f} beats{d.soma_beats:+.1f}s)[/dim]"
        )

    def _pedido_pronto(self, evento: PedidoPronto) -> None:
        self._console.print(
            f"[bold green]✅ pedido {evento.pedido_id} pronto em {evento.total_s:.1f}s[/]\n"
        )

    # ── Ao final: timeline/Gantt + stats ─────────────────────────────────────
    def _turno_resumo(self, evento: TurnoResumo) -> None:
        self._console.rule("[bold yellow]Fim de turno[/]", style="yellow")
        self._renderizar_timeline(evento.t)
        self._renderizar_stats(evento.npcs)

    def _renderizar_timeline(self, fim_turno: float) -> None:
        tabela = Table(title="Timeline do turno", box=box.SIMPLE, show_header=False)
        tabela.add_column("npc", style="bold")
        tabela.add_column("linha")
        for nome in sorted(self._timeline):
            tabela.add_row(nome, self._barra_timeline(self._timeline[nome], fim_turno))
        self._console.print(tabela)

    def _barra_timeline(self, tarefas: list[_TarefaNaLinha], fim_turno: float) -> Text:
        linha = Text()
        cursor = 0
        for tarefa in tarefas:
            col_inicio = self._coluna(tarefa.inicio, fim_turno)
            col_fim = max(col_inicio + 1, self._coluna(tarefa.fim, fim_turno))
            if col_inicio > cursor:
                linha.append(" " * (col_inicio - cursor))
            linha.append("█" * (col_fim - col_inicio), style=_cor_item(tarefa.item))
            cursor = col_fim
        if cursor < _LARGURA_GANTT:
            linha.append(" " * (_LARGURA_GANTT - cursor))
        return linha

    def _coluna(self, t: float, fim_turno: float) -> int:
        if fim_turno <= 0:
            return 0
        return min(_LARGURA_GANTT, int(t / fim_turno * _LARGURA_GANTT))

    def _renderizar_stats(self, npcs: tuple[ResumoNPC, ...]) -> None:
        tabela = Table(title="Stats do turno", box=box.ROUNDED)
        tabela.add_column("NPC", style="bold")
        tabela.add_column("Tarefas", justify="right")
        tabela.add_column("Tempo (s)", justify="right")
        tabela.add_column("XP", justify="right")
        tabela.add_column("Eventos", justify="right")
        tabela.add_column("Energia")
        tabela.add_column("Humor")
        tabela.add_column("Bio")
        for resumo in npcs:
            tabela.add_row(
                resumo.nome,
                str(resumo.tarefas),
                f"{resumo.tempo_trabalhado:.1f}",
                str(resumo.xp_ganho),
                str(resumo.eventos_sofridos),
                _barra_energia(resumo.energia_final),
                _humor_texto(resumo.humor_final),
                self._bios.get(resumo.nome, "—"),
            )
        self._console.print(tabela)

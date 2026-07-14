"""Apresentador Textual — a pele em dashboard ao vivo. Consome `SimEvent`, pinta widgets.

CODEX: Ports & Adapters + mechanism×policy (Parte III). Este é o ÚNICO arquivo do
    projeto que importa `textual`. O motor (`servicos/motor.py`) não sabe que existe
    tela, layout ou widget — ele só emite fatos (`SimEvent`). Este adapter decide como
    esses fatos viram uma TUI ao vivo: painel de equipe, painel de estações, feed
    rolante e painel de pedidos. É a MESMA porta `Apresentador` que `apresentador_rich.py`
    implementa — trocar a pele é trocar o adapter, o motor e o domínio não mudam uma
    linha (compare com `apresentador_rich.py`, que resolve os mesmos 6 eventos em Rich
    puro, sem Live/tela cheia).

CODEX: Make Illegal States Unrepresentable, provado em runtime. `SimEvent` é uma união
    fechada (Parte IV); o `match` em `emitir` é exaustivo (o pyright cobra em tempo de
    tipo) e `tests/test_sim_tui.py` prova, em runtime headless, que o dashboard populam
    os widgets sem crashar.

CODEX: DRY/SSoT — a frase de cada beat não é reinventada aqui; vem de
    `adaptadores/narracao.py`, a mesma fonte que `apresentador_rich.py` usa.
"""

from __future__ import annotations

from dataclasses import dataclass

from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, RichLog, Static

from restaurante.adaptadores.narracao import frase_beat
from restaurante.dominio.cardapio import Estacao
from restaurante.dominio.pessoas import Humor, Pessoa
from restaurante.portas.apresentador import (
    BeatOcorreu,
    PedidoPronto,
    PedidoRecebido,
    SimEvent,
    TarefaConcluida,
    TarefaIniciada,
    TurnoResumo,
)
from restaurante.portas.relogio import Relogio
from restaurante.servicos.motor import PlanoTurno, reproduzir

_COR_HUMOR: dict[Humor, str] = {
    Humor.INSPIRADO: "green",
    Humor.NEUTRO: "white",
    Humor.CANSADO: "yellow",
    Humor.ESTRESSADO: "red",
}

# Paleta cíclica de emoji por item — cosmético, escolhido por hash do nome (a mesma
# técnica de `_cor_item` em apresentador_rich.py), assim novos itens do cardápio nunca
# exigem manutenção aqui.
_PALETA_EMOJI_ITEM = ("🍔", "🍟", "🥗", "🍹", "🍗", "🥤")

_OCIOSO = "💤 ocioso"
_LARGURA_BARRA_ENERGIA = 10
_SEGUNDOS_ATE_SAIR = 3


def _emoji_item(item: str) -> str:
    """Escolhe um emoji estável para o item, só para dar cor à ação do NPC."""
    indice = sum(ord(c) for c in item) % len(_PALETA_EMOJI_ITEM)
    return _PALETA_EMOJI_ITEM[indice]


def _barra_energia(energia: int) -> Text:
    """Desenha a energia atual como uma mini-barra de blocos coloridos por faixa."""
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


@dataclass(slots=True)
class _PedidoLinha:
    """Bookkeeping interno: o estado atual de um pedido, para redesenhar o painel."""

    descricao: str
    estado: str


class SimuladorApp(App[None]):
    """Implementa a porta `Apresentador` como um dashboard Textual ao vivo.

    Recebe o plano já computado (puro, determinístico) e um relógio; ao montar, dispara
    um worker que reproduz o turno chamando `self.emitir` a cada `SimEvent` — como o
    worker roda no event loop da própria App, atualizar widgets dentro de `emitir` é
    seguro (sem thread, sem `call_from_thread`).
    """

    CSS = """
    #coluna-status {
        width: 42%;
        height: 1fr;
    }
    .painel {
        border: round $accent;
        height: auto;
        padding: 0 1;
    }
    #feed {
        width: 1fr;
        border: round $accent;
    }
    """

    def __init__(
        self,
        plano: PlanoTurno,
        relogio: Relogio,
        bios: dict[str, str],
        roster: dict[str, Pessoa],
    ) -> None:
        """Recebe o plano do turno, o relógio de ritmo, as bios e o elenco inicial."""
        super().__init__()
        self._plano = plano
        self._relogio = relogio
        self._bios = bios
        self._pedidos: dict[str, _PedidoLinha] = {}
        self._acao: dict[str, str] = {pessoa.nome: _OCIOSO for pessoa in roster.values()}
        self._energia: dict[str, int] = {pessoa.nome: pessoa.energia for pessoa in roster.values()}
        self._humor: dict[str, Humor] = {pessoa.nome: pessoa.humor for pessoa in roster.values()}
        self._estacao_de: dict[str, Estacao] = {}
        self._ocupante: dict[Estacao, str | None] = dict.fromkeys(Estacao)

    def compose(self) -> ComposeResult:
        """Monta o layout: coluna de status (equipe/estações/pedidos) + feed ao vivo."""
        yield Header(show_clock=False)
        with Horizontal():
            with Vertical(id="coluna-status"):
                yield Static(id="painel-equipe", classes="painel")
                yield Static(id="painel-estacoes", classes="painel")
                yield Static(id="painel-pedidos", classes="painel")
            yield RichLog(id="feed", classes="painel", wrap=True, markup=False)
        yield Footer()

    def on_mount(self) -> None:
        """Rotula os painéis, desenha o estado inicial e dispara o worker do turno."""
        self.title = "Restaurante — turno ao vivo"
        self.sub_title = "⏱ 0.0s"
        self.query_one("#painel-equipe", Static).border_title = "Equipe"
        self.query_one("#painel-estacoes", Static).border_title = "Estações"
        self.query_one("#painel-pedidos", Static).border_title = "Pedidos"
        self.query_one("#feed", RichLog).border_title = "Acontecendo agora"
        self._renderizar_equipe()
        self._renderizar_estacoes()
        self._renderizar_pedidos()
        self.run_worker(self._rodar_turno(), exclusive=True)

    async def _rodar_turno(self) -> None:
        """Reproduz o plano no ritmo do relógio, emitindo cada evento a esta App."""
        await reproduzir(self._plano, self._relogio, self)

    def emitir(self, evento: SimEvent) -> None:
        """Despacha o evento para o widget certo — o `match` cobre a união inteira."""
        self.sub_title = f"⏱ {evento.t:.1f}s"
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

    # ── Handlers por tipo de evento ──────────────────────────────────────────
    def _pedido_recebido(self, evento: PedidoRecebido) -> None:
        self._pedidos[evento.pedido_id] = _PedidoLinha(
            descricao=evento.descricao, estado="preparando"
        )
        self._renderizar_pedidos()
        self._feed().write(
            Text(f"📥 Pedido {evento.pedido_id} recebido — {evento.descricao}", style="bold blue")
        )

    def _tarefa_iniciada(self, evento: TarefaIniciada) -> None:
        self._acao[evento.pessoa] = f"{_emoji_item(evento.item)} {evento.item}"
        self._estacao_de[evento.pessoa] = evento.estacao
        self._ocupante[evento.estacao] = evento.pessoa
        self._renderizar_equipe()
        self._renderizar_estacoes()
        self._feed().write(f"{evento.pessoa} assume {evento.item} na {evento.estacao.value}")

    def _beat_ocorreu(self, evento: BeatOcorreu) -> None:
        narrado = frase_beat(evento.pessoa, evento.beat)
        if narrado is None:  # beat neutro (CONCENTRADO): não polui o feed
            return
        estilo, texto = narrado
        self._feed().write(Text(f"  {texto}", style=estilo))

    def _tarefa_concluida(self, evento: TarefaConcluida) -> None:
        self._acao[evento.pessoa] = _OCIOSO
        self._energia[evento.pessoa] = evento.energia
        self._humor[evento.pessoa] = evento.humor
        estacao = self._estacao_de.pop(evento.pessoa, None)
        if estacao is not None and self._ocupante.get(estacao) == evento.pessoa:
            self._ocupante[estacao] = None
        self._renderizar_equipe()
        self._renderizar_estacoes()
        self._feed().write(
            Text(
                f"✔ {evento.pessoa} concluiu {evento.item} em {evento.duracao.total:.1f}s",
                style="bold green",
            )
        )

    def _pedido_pronto(self, evento: PedidoPronto) -> None:
        linha = self._pedidos.get(evento.pedido_id)
        if linha is not None:
            linha.estado = f"pronto ({evento.total_s:.1f}s)"
        self._renderizar_pedidos()
        self._feed().write(
            Text(
                f"✅ pedido {evento.pedido_id} pronto em {evento.total_s:.1f}s", style="bold green"
            )
        )

    def _turno_resumo(self, evento: TurnoResumo) -> None:
        self.title = "Fim de turno"
        if evento.npcs:
            destaque = max(evento.npcs, key=lambda resumo: resumo.tempo_trabalhado)
            self._feed().write(
                Text(
                    f"🏆 {destaque.nome} foi quem mais trabalhou "
                    f"({destaque.tempo_trabalhado:.1f}s, {destaque.tarefas} tarefas)",
                    style="bold yellow",
                )
            )
        self._feed().write(Text("Fim de turno.", style="bold yellow"))
        self.set_timer(_SEGUNDOS_ATE_SAIR, self.exit)

    # ── Renderização dos painéis (redesenha o estado inteiro — elenco é pequeno) ────
    def _feed(self) -> RichLog:
        return self.query_one("#feed", RichLog)

    def _renderizar_equipe(self) -> None:
        tabela = Table.grid(padding=(0, 1))
        tabela.add_column()
        tabela.add_column()
        tabela.add_column()
        tabela.add_column()
        for nome, acao in self._acao.items():
            tabela.add_row(
                Text(nome, style="bold"),
                Text(acao),
                _barra_energia(self._energia[nome]),
                _humor_texto(self._humor[nome]),
            )
        self.query_one("#painel-equipe", Static).update(tabela)

    def _renderizar_estacoes(self) -> None:
        linhas = Text()
        for estacao in Estacao:
            ocupante = self._ocupante[estacao]
            if ocupante is not None:
                linhas.append(f"● {estacao.value} — {ocupante}\n", style="cyan")
            else:
                linhas.append(f"○ {estacao.value} — livre\n", style="dim")
        self.query_one("#painel-estacoes", Static).update(linhas)

    def _renderizar_pedidos(self) -> None:
        if not self._pedidos:
            self.query_one("#painel-pedidos", Static).update(
                Text("(nenhum pedido ainda)", style="dim")
            )
            return
        tabela = Table.grid(padding=(0, 1))
        tabela.add_column()
        tabela.add_column()
        tabela.add_column()
        for pedido_id, linha in self._pedidos.items():
            cor = "green" if linha.estado.startswith("pronto") else "yellow"
            tabela.add_row(
                Text(pedido_id, style="bold"), Text(linha.descricao), Text(linha.estado, style=cor)
            )
        self.query_one("#painel-pedidos", Static).update(tabela)


__all__ = ["SimuladorApp"]

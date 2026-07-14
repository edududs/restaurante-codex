"""Elenco — a fonte única de verdade dos NPCs e times deste restaurante.

CODEX: SSoT (Parte I). Quem trabalha aqui, com quais skills e personalidade, existe UMA
    vez. `demo_sim.py` e qualquer teste que queira um elenco de exemplo chamam
    `criar_elenco()` em vez de reconstruir Pessoas espalhadas pelo código.

CODEX: id == nome, de propósito. Os `SimEvent`s do motor carregam `pessoa.nome` (o que
    aparece pro público), não o id. Para `BIOS` — indexada por id, como pede o contrato —
    casar com o que o apresentador recebe sem uma tabela de tradução extra, o id de cada
    NPC é o próprio nome. Menos uma peça móvel (KISS): nenhum SSoT novo para mapear
    id -> nome.
"""

from __future__ import annotations

from restaurante.dominio.cardapio import Estacao
from restaurante.dominio.pessoas import Personalidade, Pessoa
from restaurante.dominio.times import ModoExecucao, Time

BIOS: dict[str, str] = {
    "Ana": "Craque da chapa: 12 anos de casa, não erra o ponto de um hambúrguer nem dormindo.",
    "Bruno": "O bar é o palco dele — sociável, puxa conversa com todo mundo enquanto tira o chopp.",
    "Caio": "Disciplinado até demais; a fritadeira nunca teve um cliente tão dedicado quanto ele.",
    "Duda": "Criativa e um pouco distraída — a salada dela sempre tem um toque a mais.",
    "Eli": "Novata versátil, ainda decidindo se o coração é da chapa ou da fritadeira.",
    "Fefa": "Segunda no bar, focada e discreta, cobre o Bruno nos dias de rush.",
}
"""Uma frase de história/personalidade por NPC — o toque 'Sims' do painel de stats."""


def criar_elenco() -> tuple[dict[str, Pessoa], list[Time]]:
    """Monta o elenco fixo do restaurante: 6 NPCs em 2 times cobrindo as 4 estações."""
    ana = Pessoa(
        id="Ana",
        nome="Ana",
        personalidade=Personalidade(foco=85, sociavel=40, disciplina=80, criatividade=45),
        skills={Estacao.CHAPA: 92, Estacao.FRITADEIRA: 55, Estacao.SALADAS: 30},
    )
    bruno = Pessoa(
        id="Bruno",
        nome="Bruno",
        personalidade=Personalidade(foco=55, sociavel=90, disciplina=60, criatividade=50),
        skills={Estacao.BAR: 90, Estacao.SALADAS: 35},
    )
    caio = Pessoa(
        id="Caio",
        nome="Caio",
        personalidade=Personalidade(foco=70, sociavel=35, disciplina=88, criatividade=30),
        skills={Estacao.FRITADEIRA: 88, Estacao.CHAPA: 50},
    )
    duda = Pessoa(
        id="Duda",
        nome="Duda",
        personalidade=Personalidade(foco=50, sociavel=60, disciplina=45, criatividade=90),
        skills={Estacao.SALADAS: 90, Estacao.FRITADEIRA: 40},
    )
    eli = Pessoa(
        id="Eli",
        nome="Eli",
        personalidade=Personalidade(foco=45, sociavel=55, disciplina=40, criatividade=55),
        skills={Estacao.CHAPA: 45, Estacao.FRITADEIRA: 45, Estacao.SALADAS: 45},
    )
    fefa = Pessoa(
        id="Fefa",
        nome="Fefa",
        personalidade=Personalidade(foco=75, sociavel=65, disciplina=75, criatividade=40),
        skills={Estacao.BAR: 65, Estacao.SALADAS: 30},
    )

    roster = {pessoa.id: pessoa for pessoa in (ana, bruno, caio, duda, eli, fefa)}

    cozinha = Time(
        nome="Cozinha",
        membros=("Ana", "Caio", "Duda", "Eli"),
        responsabilidades=frozenset({Estacao.CHAPA, Estacao.FRITADEIRA, Estacao.SALADAS}),
        modo=ModoExecucao.MULTITAREFA,
    )
    bar = Time(
        nome="Bar",
        membros=("Bruno", "Fefa"),
        responsabilidades=frozenset({Estacao.BAR}),
        modo=ModoExecucao.FOCADO,
    )

    return roster, [cozinha, bar]

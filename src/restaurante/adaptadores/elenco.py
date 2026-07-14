"""Elenco — a fachada que expõe o elenco fixo do restaurante, agora vindo do config.

CODEX: SSoT (Parte I). Quem trabalha aqui, com quais skills e personalidade, existe UMA
    vez — em `config/elenco.json`, validado por `config/modelos.py::ElencoCfg` e
    carregado por `config/carregador.py::carregar_elenco()`. `demo_sim.py` e qualquer
    teste que queira um elenco de exemplo continuam chamando `criar_elenco()` — a
    MESMA API pública de sempre — só que o dado agora é editável sem tocar em Python.

CODEX: id == nome, de propósito. Os `SimEvent`s do motor carregam `pessoa.nome` (o que
    aparece pro público), não o id. Para `BIOS` — indexada por id, como pede o contrato —
    casar com o que o apresentador recebe sem uma tabela de tradução extra, o id de cada
    NPC é o próprio nome (ver `config/elenco.json`). Menos uma peça móvel (KISS): nenhum
    SSoT novo para mapear id -> nome.
"""

from __future__ import annotations

from restaurante.config.carregador import carregar_elenco
from restaurante.dominio.pessoas import Pessoa
from restaurante.dominio.times import Time

_ROSTER_CFG, _TIMES_CFG, BIOS = carregar_elenco()
"""`BIOS`: uma frase de história/personalidade por NPC — o toque 'Sims' do painel de stats."""


def criar_elenco() -> tuple[dict[str, Pessoa], list[Time]]:
    """Monta o elenco fixo do restaurante: 6 NPCs em 2 times cobrindo as 4 estações.

    Devolve cópias rasas do roster/times carregados (cacheados) de `config/elenco.json`
    — o mesmo contrato de sempre: cada chamada devolve containers independentes, mas as
    `Pessoa`/`Time` em si são imutáveis, então compartilhá-las entre chamadas é seguro.
    """
    return dict(_ROSTER_CFG), list(_TIMES_CFG)

"""Boundary de configuração — o ÚNICO lugar do projeto que importa Pydantic.

CODEX: Ports & Adapters aplicado a config. `dominio/*` e `servicos/*` nunca importam
    nada deste pacote diretamente por baixo dos panos de validação — quem consome é
    `adaptadores/*`, `demo_sim.py`/`demo_tui.py` e os testes, sempre através das
    funções `carregar_*` (`carregador.py`) ou da fachada `Cardapio` (`catalogo.py`).
"""

from __future__ import annotations

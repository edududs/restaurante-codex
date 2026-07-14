"""Narração — a SSoT da frase descritiva de um beat, compartilhada pelas peles.

CODEX: DRY/SSoT. O modo log (Rich) e o dashboard (Textual) descrevem o mesmo evento;
    a frase mora aqui, num lugar só. Mudar como um beat é narrado propaga para as duas
    peles. Funções puras (sem I/O) — a pele só decide onde/como pintar o texto.

CODEX: PARSE, DON'T VALIDATE — a marca visual (emoji + cor) de cada `TipoBeat` não é
    mais um dict hardcoded aqui: vem de `config/tema.json`, validado e carregado por
    `config/carregador.py::carregar_tema()`. Trocar o tema (outro emoji, outra cor) é
    editar o JSON — este módulo continua puro, sem pydantic e sem I/O direto.
"""

from __future__ import annotations

from restaurante.config.carregador import carregar_tema
from restaurante.dominio.beats import Beat, TipoBeat


def frase_beat(pessoa: str, beat: Beat) -> tuple[str, str] | None:
    """Devolve (estilo, frase) descritiva do beat — com o NOME de quem viveu — ou None.

    Retorna None para CONCENTRADO (ritmo normal, sem graça de narrar), o que evita a
    linha redundante "assume a estação" que o TarefaIniciada já cobre.
    """
    if beat.tipo is TipoBeat.CONCENTRADO:
        return None
    emoji, estilo = carregar_tema()[beat.tipo]
    return estilo, f"{emoji} {pessoa} {beat.texto} ({beat.delta_s:+.1f}s)"

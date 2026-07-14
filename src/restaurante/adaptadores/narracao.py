"""Narração — a SSoT da frase descritiva de um beat, compartilhada pelas peles.

CODEX: DRY/SSoT. O modo log (Rich) e o dashboard (Textual) descrevem o mesmo evento;
    a frase mora aqui, num lugar só. Mudar como um beat é narrado propaga para as duas
    peles. Funções puras (sem I/O) — a pele só decide onde/como pintar o texto.
"""

from __future__ import annotations

from restaurante.dominio.beats import Beat, TipoBeat

# Marca visual (emoji + estilo Rich) por tipo de beat. CONCENTRADO é neutro: não narra.
_MARCA: dict[TipoBeat, tuple[str, str]] = {
    TipoBeat.INSPIRADO: ("🟢", "green"),
    TipoBeat.ATRAPALHOU: ("🔴", "red"),
    TipoBeat.DISTRAIU: ("💭", "dim"),
    TipoBeat.INTERAGIU: ("💬", "cyan"),
    TipoBeat.EVENTO: ("🔥", "magenta"),
}


def frase_beat(pessoa: str, beat: Beat) -> tuple[str, str] | None:
    """Devolve (estilo, frase) descritiva do beat — com o NOME de quem viveu — ou None.

    Retorna None para CONCENTRADO (ritmo normal, sem graça de narrar), o que evita a
    linha redundante "assume a estação" que o TarefaIniciada já cobre.
    """
    if beat.tipo is TipoBeat.CONCENTRADO:
        return None
    emoji, estilo = _MARCA[beat.tipo]
    return estilo, f"{emoji} {pessoa} {beat.texto} ({beat.delta_s:+.1f}s)"

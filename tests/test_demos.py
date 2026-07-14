"""Smoke tests dos demos — os entry points também são cobertos.

Os `demo*.py` são a porta de entrada de quem clona o repo; se um deles quebra (import ou
runtime), o gate tem que pegar. Antes, `pytest` testava só a biblioteca — um import
quebrado num demo passava batido. Estes testes fecham esse buraco:
- `demo.py` e `demo_sim.py` rodam de ponta a ponta (subprocess, exit 0);
- `demo_tui.py` (TUI, não roda em subprocess sem terminal) tem a fiação exercitada por
  `montar_app()`; o runtime do app em si está coberto por `test_sim_tui.py`.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import subprocess
import sys
import types

_RAIZ = pathlib.Path(__file__).resolve().parent.parent
_TIMEOUT = 120


def _rodar(
    script: str, env_extra: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # noqa: S603 — roda nossos próprios demos com sys.executable (confiável)
        [sys.executable, script],
        cwd=_RAIZ,
        capture_output=True,
        timeout=_TIMEOUT,
        env={**os.environ, **(env_extra or {})},
        check=False,
    )


def _importar(nome: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(nome, _RAIZ / f"{nome}.py")
    assert spec is not None
    assert spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_demo_roda_ate_o_fim() -> None:
    resultado = _rodar("demo.py")
    assert resultado.returncode == 0, resultado.stderr.decode("utf-8", "replace")


def test_demo_sim_roda_ate_o_fim() -> None:
    # RESTAURANTE_ESCALA=0.001 (env > json, via pydantic-settings) deixa instantâneo.
    resultado = _rodar("demo_sim.py", {"RESTAURANTE_ESCALA": "0.001"})
    assert resultado.returncode == 0, resultado.stderr.decode("utf-8", "replace")


def test_demo_tui_monta_o_app_a_partir_do_cenario() -> None:
    # Importar não abre TUI (sem side-effect); `montar_app` exercita config→domínio→app.
    demo_tui = _importar("demo_tui")
    app = demo_tui.montar_app()
    assert type(app).__name__ == "SimuladorApp"

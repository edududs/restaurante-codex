# Validation — Fase 3 (Pele Rich)

**Data:** 2026-07-13
**Verificador:** independente (autor ≠ verificador), re-derivado do zero.
**Escopo:** `apresentador_rich.py`, `elenco.py`, `demo_sim.py`, `tests/test_sim_rich.py`, `docs/07-simulacao-sims.md`.
**Veredito:** **PASS ✅** (com 1 gap de força-de-teste registrado — não bloqueante).

---

## Tarefa 1 — Gate

| Check | Comando | Resultado |
|-------|---------|-----------|
| ruff | `uv run ruff check .` | **All checks passed!** |
| pyright | `uv run pyright` | **0 errors, 0 warnings, 0 informations** |
| pytest | `uv run pytest -q` | **44 passed** (1.81s) |
| demo | `uv run python demo_sim.py` | **exit 0** |

Gate verde em todas as frentes.

## Tarefa 2 — Isolamento do rich

`grep -rn "import rich\|from rich" src/` retorna **apenas** `apresentador_rich.py` (linhas 21–24: `box`, `Console`, `Table`, `Text`).

| Camada | Importa rich? |
|--------|---------------|
| `servicos/motor.py` | Não |
| `dominio/*` | Não |
| `portas/*` | Não |
| `adaptadores/apresentador_rich.py` | **Sim (único)** |
| `demo_sim.py` (raiz) | Não (consome `ApresentadorRich`, não rich direto) |

Nota: `tests/test_sim_rich.py:7` importa `rich.console.Console` — é injeção de Console no teste (side de teste, não `src/`); não viola o confinamento.

**Isolamento: OK — rich só no adapter.**

## Tarefa 3 — Sensor de discriminação (mutação → observação → revert imediato)

| # | Mutação | Esperado | Observado | Veredito |
|---|---------|----------|-----------|----------|
| 1 | Comentar `case TurnoResumo():` no `match` de `emitir` | pyright `reportMatchNotExhaustive` **ou** pytest falha | **pyright ERRO** em `apresentador_rich.py:106` — "Cases within match statement do not exhaustively handle all values / Unhandled type: TurnoResumo (reportMatchNotExhaustive)". pytest passou (1 passed). | **KILLED** (por pyright) |
| 2 | Remover `tabela.add_column("Eventos")` em `_renderizar_stats` (7 cols, 8 valores no add_row) | Rich levanta em runtime → pytest falha | **Rich NÃO levanta**: auto-estende as colunas (confirmado em repro: `add_row` com mais células que colunas → nº de colunas cresce, sem exceção). pytest passou (1 passed). | **SURVIVED** |

**Resumo sensor: 2 injetadas, 1 killed, 1 survived.**

- `git diff --stat` verificado **limpo** após cada revert e ao final.
- Nunca usei `git stash`.

### Por que mut#2 sobreviveu (finding real)

A premissa do teste ("o Rich levanta em runtime com add_row > colunas") é **falsa**: o Rich tolera células extras estendendo as colunas silenciosamente. `tests/test_sim_rich.py` é um **smoke test** — emite 1 evento de cada tipo e só assere `saida != ""`. Não valida a estrutura da tabela de stats (nº de colunas, cabeçalhos, alinhamento). Logo, uma regressão real na montagem da tabela (coluna faltando, valor no lugar errado) **não seria pega**. Código enviado está correto; o gap é de força/discriminação do teste, não de defeito funcional.

## Tarefa 4 — Aderência ao Codex

| Claim | Evidência | Status |
|-------|-----------|--------|
| `match` exaustivo sobre `SimEvent` | `apresentador_rich.py:106-118` cobre os 6 casos (`PedidoRecebido`, `TarefaIniciada`, `BeatOcorreu`, `TarefaConcluida`, `PedidoPronto`, `TurnoResumo`). Exaustividade **provada em tipo** por pyright (mut#1 → reportMatchNotExhaustive) e **em runtime** por `tests/test_sim_rich.py:50-64` (emite 1 de cada tipo, sem exceção). | ✅ |
| Elenco como SSoT cobrindo todas as estações | `elenco.py:31` `criar_elenco()`. Time Cozinha (`:72-77`) responsabilidades `{CHAPA, FRITADEIRA, SALADAS}`; Time Bar (`:78-83`) `{BAR}`. União = **CHAPA/FRITADEIRA/SALADAS/BAR** = 4/4 estações. `demo_sim.py` e testes consomem `criar_elenco()` (sem reconstruir Pessoas). | ✅ |
| rich confinado ao adapter | Ver Tarefa 2 — único importador em `src/`. | ✅ |
| motor/domínio/portas intactos nesta fase | `git diff --stat HEAD~2 -- src/restaurante/servicos src/restaurante/dominio src/restaurante/portas` → **vazio** (nenhuma linha alterada em servicos/motor.py, dominio/, portas/ na Fase 3). | ✅ |

**Aderência: 4/4.**

## Veredito final

**PASS ✅** — Gate 100% verde (ruff/pyright/pytest 44/pytest demo exit 0); rich isolado no adapter; motor/domínio/portas intactos; match exaustivo e elenco-SSoT provados. A exhaustiveness (claim central) é defendida pelo pyright no próprio gate.

### Gaps ranqueados

1. **(médio — força de teste)** `tests/test_sim_rich.py` é smoke test (`assert saida != ""`); não assere a estrutura da tabela de stats. Mutação #2 (coluna removida) sobreviveu. Recomendação: assertar cabeçalhos/nº de colunas na saída renderizada, ou snapshot da tabela de stats.
2. **(baixo — nota factual)** A hipótese de que Rich levanta com `add_row` > colunas é falsa (auto-estende). Documentar para não induzir futuras mutações/testes ao erro.

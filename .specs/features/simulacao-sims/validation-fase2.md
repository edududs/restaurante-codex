# Validation — Fase 2 (Times & motor async)

**Data:** 2026-07-13
**Verificador:** independente (autor ≠ verificador), re-derivação completa
**Escopo:** `dominio/times.py`, `portas/relogio.py`, `portas/apresentador.py`,
`adaptadores/relogio_real.py`, `adaptadores/relogio_fake.py`,
`adaptadores/apresentador_coletor.py`, `servicos/motor.py`, `tests/test_sim_motor.py`

## Veredito: PASS ✅

---

## Tarefa 1 — Gate

| Comando | Resultado | Exit |
|---|---|---|
| `ruff check .` | All checks passed! | 0 ✅ |
| `pyright` | 0 errors, 0 warnings, 0 informations | 0 ✅ |
| `pytest -q` | 43 passed in 1.76s | 0 ✅ |

Gate verde.

## Tarefa 2 — Sensor de discriminação (3 mutações em `servicos/motor.py`)

Cada mutação injetada → teste-alvo rodado → revertida na hora. `git diff` limpo ao final.

| # | Mutação | Teste-alvo | Resultado |
|---|---|---|---|
| 1 | `inicio = max(cursor_estacao[…], cursor_pessoa[pid])` → `inicio = cursor_pessoa[pid]` (remove serialização por estação) | `test_mesma_estacao_serializa` | **KILLED** — `AssertionError: 0.0 >= 6.74` (2ª tarefa CHAPA iniciou em t=0) |
| 2 | `if dt > 0:` → `if dt < 0:` (para de pagar o tempo) | `test_replay_emite_tudo_em_ordem_e_paga_o_tempo` | **KILLED** — `total_dormido=0.0` ≠ `t_final=5.26` |
| 3 | `estado[pid] = aplicar_conclusao(…)` → `pass` (NPC não evolui) | `test_npcs_evoluem_no_turno` | **KILLED** — `KeyError: Estacao.CHAPA` (XP nunca registrado) |

**Sensor: 3 injetadas, 3 killed, 0 survived.** Suíte discrimina serialização, ritmo e evolução.

## Tarefa 3 — Determinismo (propriedade central)

- `planejar_turno` é puro: `rng = Random(seed)` local (motor.py:92); toda decisão de beat
  flui pelo `rng` semeado passado a `gerador.gerar(pessoa, item, rng)` (motor.py:109).
- `adaptadores/situacoes_sims.py` usa **exclusivamente** o `rng` recebido
  (`rng.random`, `rng.uniform`, `rng.choice`) — sem `random` global.
- Motor **não** usa: `random` global, `time.perf_counter`, `time.time`, `datetime`,
  nem `asyncio.sleep` direto. `servicos/motor.py` sequer importa `asyncio`.
- `reproduzir` pausa **só** via `relogio.dormir(dt)` (motor.py:171). Nenhuma outra fonte de espera.
- Prova executável: `test_planejamento_e_deterministico` (mesma seed → `a.eventos == b.eventos`) — passa.

**Determinismo: OK.** Nenhuma fonte de não-determinismo no conteúdo do plano.

## Tarefa 4 — Aderência ao Codex (evidência-ou-zero)

| Princípio | Evidência (arquivo:linha) | Teste | Status |
|---|---|---|---|
| SoC determinismo×ritmo | `planejar_turno` puro (motor.py:84–162) vs `reproduzir` async mínima (motor.py:165–173) | `test_planejamento_e_deterministico`, `test_replay_emite_tudo_em_ordem_e_paga_o_tempo` | ✅ |
| DIP (portas) | motor importa só `Relogio`, `Apresentador`, `GeradorDeSituacoes` (Protocols); não importa Rich nem `asyncio` | `test_replay_*` c/ `RelogioFake`+`ApresentadorColetor` injetados | ✅ |
| Tipo-soma `SimEvent` | união fechada apresentador.py:91–93; 6 casos frozen | `test_turno_produz_os_eventos_esperados` | ✅ |
| Fail-fast `SemResponsavel` | `_escolher_npc` levanta quando sem candidatos (motor.py:73) | `test_sem_time_responsavel_falha` | ✅ |
| Função pura (não muta roster) | `estado = dict(roster)` copia (motor.py:93); `Pessoa` frozen, evolução reatribui `estado[pid]` sem tocar o dict de entrada | `test_npcs_evoluem_no_turno` lê `roster["ana"].energia` original pós-planejamento e confirma intacto | ✅ |

**Aderência: 5/5, sem gaps.**

Nota (não-gap): o `match` exaustivo sobre `SimEvent` só é exercido na pele Rich (Fase 3);
na Fase 2 o `ApresentadorColetor` só acumula. A exaustividade já é cobrada estaticamente
pelo pyright na união fechada. Recomendação para Fase 3: teste de renderer com `match` exaustivo.

## Restrições

- Read-only exceto este `validation-fase2.md` e as 3 mutações revertidas na hora.
- Nenhum commit, nenhum push, nenhum `git stash`.
- `git diff --stat` final: limpo nos arquivos rastreados (só arquivos de validação não rastreados).

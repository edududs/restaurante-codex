# Validation — Fases 4 e 5 (Verificador independente)

**Data:** 2026-07-14
**Escopo:** Fase 4 (Textual + narração descritiva + ritmo) e Fase 5 (config JSON validado por Pydantic v2 no boundary, domínio StrEnum, assert_never, smoke test dos demos).
**Método:** autor ≠ verificador; tudo re-derivado a partir dos arquivos reais. Read-only exceto este relatório e mutações injetadas/revertidas na hora.
**Veredito:** **PASS ✅**

---

## 1. Gate (exit != 0 = FAIL)

| Comando | Resultado | Exit |
|---|---|---|
| `uv run ruff check .` | All checks passed! | 0 ✅ |
| `uv run pyright` | 0 errors, 0 warnings, 0 informations | 0 ✅ |
| `uv run pytest -q` | 61 passed in ~9.8s | 0 ✅ |

Gate **verde**.

---

## 2. Pureza do domínio + isolamento de pele/config

| Regra | Verificação (grep) | Resultado |
|---|---|---|
| `dominio/` não importa pydantic | única ocorrência é comentário em `cardapio.py:8` (nenhum `import`) | OK ✅ |
| `dominio/` não importa `restaurante.config` | nenhuma ocorrência | OK ✅ |
| `dominio/` não importa rich | nenhuma ocorrência | OK ✅ |
| `dominio/` não importa textual | nenhuma ocorrência | OK ✅ |
| rich só na pele | `apresentador_rich.py` e `apresentador_textual.py` (ambos adapters de pele) | OK ✅ |
| textual só em `apresentador_textual` | única ocorrência | OK ✅ |
| pydantic só em `src/restaurante/config/` | `config/modelos.py` e `config/carregador.py` | OK ✅ |

**Nota (não-gap):** `apresentador_textual.py` importa rich além de textual. Isso é legítimo — Textual é construído sobre Rich e o adapter é da camada de pele; nenhum vazamento para domínio/serviços/portas. Claim de isolamento **confirmado**.

---

## 3. Fidelidade SOTA (a–h) — 8/8

| # | Item | Local (arquivo:linha) | Status |
|---|---|---|---|
| a | Discriminated union `ConsumoCfg` com `Field(discriminator="tipo")` | `modelos.py:168` | OK ✅ |
| b | `TypeAdapter(list[ItemCfg])` | `modelos.py:64` (`CARDAPIO_ADAPTER`) | OK ✅ |
| c | DOIS `model_validator(mode="after")` no `ElencoCfg` | `modelos.py:112` (`_membros_existem`) e `modelos.py:122` (`_cobre_todas_as_estacoes`) | OK ✅ |
| d | `AfterValidator` na escala | `modelos.py:220` (`_escala_positiva`) | OK ✅ |
| e | pydantic-settings `settings_customise_sources`, precedência env>json>default | `modelos.py:223-233` → `(env_settings, JsonConfigSettingsSource, init_settings)` | OK ✅ |
| f | `ConfigDict(extra="forbid")` | `modelos.py:50` (`_Base`) + `SettingsConfigDict(extra="forbid")` em `CenarioCfg:216` | OK ✅ |
| g | `StrEnum` no domínio | `beats.TipoBeat`, `cardapio.Estacao`, `cardapio.Categoria`, `pessoas.Humor`, `times.ModoExecucao` | OK ✅ |
| h | `assert_never` nos match fechados | `apresentador_rich.py:111`, `apresentador_textual.py:183`, `motor._descreve_consumo:62`, `carregador._consumo_do_dominio:59` | OK ✅ |

**SOTA: 8/8.** Observação em (g): `dominio/pedido.py:53` `EstadoPedido` é `Enum` puro (não StrEnum) — correto, pois é estado interno de máquina, não serializado como string na config; não é regressão.

---

## 4. Sensor de discriminação (mutação → revert na hora; sem git stash; diff limpo)

| # | Mutação | Teste alvo | Esperado | Resultado |
|---|---|---|---|---|
| 1 | Remove `extra="forbid"` do `_Base` | `test_chave_desconhecida_falha_com_extra_forbid` | FAIL | **killed** ✅ (DID NOT RAISE ValidationError) |
| 2 | Ordem `(Json, env, init)` (json antes de env) | `test_env_var_sobrepoe_o_json` | FAIL | **killed** ✅ (assert 42 == 999) |
| 3 | `_cobre_todas_as_estacoes` sem `raise` | `test_elenco_que_nao_cobre_uma_estacao_falha` | FAIL | **killed** ✅ (DID NOT RAISE ValidationError) |
| 4 | `montar_app` retorna `None` | `test_demo_tui_monta_o_app_a_partir_do_cenario` | FAIL | **killed** ✅ (SimuladorApp vs NoneType) |

**Sensor: 4 injetadas, 4 killed, 0 survived.** Todas revertidas; `git diff --stat` vazio após reverts (confirmado antes do relatório).

---

## 5. Determinismo preservado (Enum → StrEnum)

| Verificação | Resultado |
|---|---|
| `test_planejamento_e_deterministico` | 1 passed ✅ |
| `uv run python demo.py` | exit 0 ✅ |
| `RESTAURANTE_ESCALA=0.001 uv run python demo_sim.py` | exit 0 ✅ (env>json via pydantic-settings) |

A migração Enum→StrEnum **não quebrou** o replay por seed.

---

## 6. Veredito

**PASS ✅** — Gate verde (ruff/pyright/pytest 61), pureza do domínio e isolamento de pele/config confirmados por grep, SOTA 8/8, sensor 4/4 killed, determinismo preservado.

Nenhum gap grave. Observações menores (não bloqueiam):
1. `apresentador_textual` importa rich além de textual — legítimo (Textual roda sobre Rich; ambos ficam na pele). Sem vazamento para o domínio.
2. `EstadoPedido` permanece `Enum` puro — coerente (estado interno, não serializado como string na config).

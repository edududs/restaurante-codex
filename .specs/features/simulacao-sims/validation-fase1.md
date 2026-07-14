# Validation — Fase 1 (Núcleo Sims)

**Data:** 2026-07-13
**Verificador:** independente (autor ≠ verificador). Tudo re-derivado; nada assumido do autor.
**Escopo:** `dominio/beats.py`, `dominio/pessoas.py`, `portas/situacoes.py`,
`servicos/modelo_tempo.py`, `adaptadores/situacoes_sims.py`, `tests/test_sim_nucleo.py`.
**Comandos:** via `uv --directory "D:/Projects/restaurante-codex" run ...` (git-bash, sem `cd`).

## Veredito: **PASS ✅**

Gate verde, sensor de discriminação 3/3 killed, determinismo confirmado por leitura + execução,
aderência ao Codex com evidência (arquivo:linha + teste) em 4/4 pontos. Nenhum gap bloqueante.

---

## Tarefa 1 — Gate

| Passo | Comando | Resultado | Exit |
|---|---|---|---|
| Lint | `ruff check .` | `All checks passed!` | 0 ✅ |
| Types | `pyright` | `0 errors, 0 warnings, 0 informations` | 0 ✅ |
| Testes | `pytest -q` | `35 passed in 1.89s` | 0 ✅ |

`test_sim_nucleo.py` contribui 13 testes; os 35 são a suíte completa (Fase 1 + domínio reusado). Todos verdes.

## Tarefa 2 — Sensor de discriminação (mutation testing)

Cada mutação injetada no código NOVO da Fase 1, teste-alvo rodado, **revertida na hora**.
`git status --porcelain` limpo antes e depois de cada mutação.

| # | Arquivo | Mutação | Teste-alvo | Resultado |
|---|---|---|---|---|
| 1 | `modelo_tempo.py:40` | `_mult_skill` → `1.3 + 0.6*(skill/100)` (skill atrasa) | `test_skill_mais_alto_reduz_o_tempo` | **KILLED ✅** (`11.04 < 8.52` falha) |
| 2 | `modelo_tempo.py:59` | `soma_beats = sum(...)` → `soma_beats = 0` | `test_beats_somam_no_total` | **KILLED ✅** (`Δ 6.0-6.0 ≠ 1.0`) |
| 3 | `pessoas.py:112` | remove incremento de XP em `aplicar_conclusao` | `test_conclusao_gasta_energia_e_ganha_xp_sem_mutar_original` | **KILLED ✅** (`KeyError CHAPA`) |

**3 injetadas · 3 killed · 0 survived.** Os testes discriminam de fato as 3 propriedades centrais
(skill acelera, beats somam, XP evolui). Tree limpo confirmado ao final.

## Tarefa 3 — Determinismo

Propriedade central: `SituacoesSims.gerar` é função só do estado + `rng` injetado.

| Verificação | Evidência | Status |
|---|---|---|
| Prova por execução | `test_situacoes_sao_deterministicas_por_seed` (mesma seed → mesma história) + `test_seeds_diferentes_podem_divergir` | 2 passed ✅ |
| `rng` injetado, não global | `portas/situacoes.py:22` e `adaptadores/situacoes_sims.py:41` recebem `rng: Random`; todos os sorteios via `rng.random/uniform/choice` (linhas 51,59,66,71,80) | OK ✅ |
| Sem `random` global | grep no núcleo: nenhum `random.random/seed/choice` de módulo, nenhum `Random()` sem seed | OK ✅ |
| Sem `time` / `datetime` | grep no núcleo: nenhuma importação/uso | OK ✅ |
| NPCs com id estável | `Pessoa.id: str` explícito (pessoas.py:66), não uuid | OK ✅ |

**Fonte de não-determinismo no núcleo: nenhuma.** Observação fora de escopo: `dominio/pedido.py:91`
e `adaptadores/pagamento_fake.py:23` usam `uuid4` — código pré-existente **reusado**, não Fase 1;
não afeta o núcleo Sims (Pessoa/Beat/duração são determinísticos por seed). Sem gap.

## Tarefa 4 — Aderência ao Codex (evidência-ou-zero)

| Princípio | Evidência (arquivo:linha) | Teste | Status |
|---|---|---|---|
| Estado ilegal irrepresentável (stats 0–100 validados) | `pessoas.py:37-39` `_validar` → `AtributoInvalido`; `Personalidade.__post_init__` :57-59; `Pessoa.__post_init__` :74-77; tipos-soma `TipoBeat`/`Humor` (`beats.py:16`, `pessoas.py:28`) | `test_atributo_fora_do_intervalo_falha` (:91-97) | ✅ |
| Mechanism × policy (situações como porta) | Porta `GeradorDeSituacoes` Protocol `situacoes.py:19-24`; adapter `SituacoesSims` `situacoes_sims.py:38`; `modelo_tempo.duracao_tarefa` recebe `beats` prontos e só soma (:53-69) — não decide quais | `test_situacoes_sao_deterministicas_por_seed` (exercita via adapter) | ✅ |
| Função pura (não muta entrada) | `duracao_tarefa` retorna `DuracaoTarefa` frozen, lê `pessoa/item/beats` sem mutar (`modelo_tempo.py:53-69`); `aplicar_conclusao` usa `replace()` + `dict(...)` cópia (`pessoas.py:111-118`) | `test_conclusao_..._sem_mutar_original` asserta `ana.energia==100`, `ana.experiencia=={}` (:105-111) | ✅ |
| Fail-fast | `_validar` levanta na construção (`__post_init__`), estado inválido não nasce (`pessoas.py:37-39,57-59,74-77`) | `test_atributo_fora_do_intervalo_falha` (:91-97) | ✅ |

**Aderência: 4/4, sem gaps.** Reforço estrutural: `Beat`, `Pessoa`, `Personalidade`, `DuracaoTarefa`
todos `frozen=True, slots=True` (imutabilidade real).

---

## Gaps ranqueados

Nenhum gap bloqueante para a Fase 1. Observações menores (não impedem PASS):

1. **(informativo, fora de escopo)** `pedido.py:91` / `pagamento_fake.py:23` usam `uuid4` —
   não-determinístico, mas é domínio pré-existente reusado, fora do núcleo Sims. Se a Fase 2
   (motor) exigir replays byte-a-byte de pedidos inteiros, considerar injetar id via factory semeada.
2. **(nit)** `duracao_tarefa` recebe `beats: list[Beat]` (mutável) enquanto o resto do núcleo usa
   tipos frozen; poderia aceitar `Sequence[Beat]` para reforçar leitura-só. Cosmético, sem impacto.

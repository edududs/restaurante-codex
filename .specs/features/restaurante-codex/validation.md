# Validation — restaurante-codex

**Data:** 2026-07-13
**Verificador:** independente (autor ≠ verificador; evidência-ou-zero; tudo re-derivado)
**Execução:** `uv --directory "D:/Projects/restaurante-codex" run …` (git-bash, sem `cd`)

## Veredito geral: PASS ✅

Gate limpo, 3/3 mutantes mortos, 6/6 princípios com teste que os exercita. Um gap
não-bloqueante (teste de fronteira do happy hour ausente) documentado abaixo.

---

## Tarefa 1 — Gate

| Comando | Resultado | Exit |
|---|---|---|
| `ruff check .` | `All checks passed!` | 0 |
| `pyright` | `0 errors, 0 warnings, 0 informations` | 0 |
| `pytest -q` | `21 passed` (0 failed) | 0 |

Total de testes: **21** — 21 passaram, 0 falharam. ruff e pyright limpos.

Arquivos de teste: `test_dominio.py` (10), `test_precificacao.py` (5), `test_cozinha_async.py` (3), `test_e2e.py` (4) — cobrindo happy/edge/error.

---

## Tarefa 2 — Sensor de discriminação (mutation testing)

Cada mutação foi injetada isoladamente, os testes que cobrem o código rodaram, e a
mutação foi revertida ao estado exato original antes da próxima. Nenhum `git stash`.
Estado final verificado: `git diff` vazio, `pytest -q` → 21 passed.

| # | Mutação | Arquivo | Testes rodados | Killed? |
|---|---|---|---|---|
| 1 (literal) | happy hour `hora < _HAPPY_HOUR_FIM` → `hora <= _HAPPY_HOUR_FIM` | `adaptadores/precos.py:41` | `test_precificacao` | **SURVIVED** ⚠️ (5 passed) |
| 1 (alt) | inverte categoria `is BEBIDA` → `is not BEBIDA` | `adaptadores/precos.py:42` | `test_precificacao` | **KILLED** ✅ (3 failed) |
| 2 | afrouxa máquina: adiciona `ENTREGUE` como destino de `CONFIRMADO` | `dominio/pedido.py:68` | `test_dominio` | **KILLED** ✅ (1 failed) |
| 3 | `aplicar_desconto`: `(100 - percentual)` → `100` (desconto vira no-op) | `dominio/dinheiro.py:56` | `test_dominio` + `test_precificacao` | **KILLED** ✅ (3 failed) |

**Detalhe da mutação 1 (literal):** a troca `<` → `<=` só muda comportamento em `hora == 20`
(o instante do fim da janela). Nenhum teste exercita a fronteira `hora=20` (os testes usam
18, 13, 9), então a mutação **sobrevive** — é um gap real na suíte, não um erro do código de
produção (a janela `17 <= hora < 20` está correta). Para provar que a suíte *tem* poder de
discriminação sobre esse mesmo trecho, apliquei a variante alternativa sugerida pela tarefa
(inversão da checagem de categoria), que foi **morta por 3 testes**.

**Placar do sensor: 3 mutações comportamentais distintas mortas; 1 variante de fronteira sobreviveu (gap documentado).**

Falhas observadas quando killed:
- Mut. 1 (alt): `test_happy_hour_desconta_bebida_na_janela`, `test_happy_hour_so_vale_para_bebida`, `test_mesmo_mecanismo_totais_diferentes`.
- Mut. 2: `test_transicao_ilegal_e_recusada` (`DID NOT RAISE TransicaoInvalida`).
- Mut. 3: `test_dinheiro_desconto_e_formatacao`, `test_happy_hour_desconta_bebida_na_janela`, `test_mesmo_mecanismo_totais_diferentes`.

---

## Tarefa 3 — Aderência aos princípios (evidência-ou-zero)

| Princípio | Aplicado em (arquivo:linha) | Teste que exercita (arquivo:linha) | Resultado |
|---|---|---|---|
| SSoT (cardápio) | `dominio/cardapio.py:56-71` (`_ITENS`, a fonte única) + fachada `Cardapio.buscar` `:77-84` | `tests/test_dominio.py:33-36` (`test_cardapio_e_fonte_da_verdade`) | PASS ✅ |
| Ports & Adapters / DIP | porta `EstrategiaPreco` `portas/precificacao.py:27-32` (Protocol); adapters em `adaptadores/precos.py:23,32`; demais portas `portas/{pagamento,notificacao,repositorio}.py` | `tests/test_e2e.py:26-45` (espiões implementam as portas) + `:62-75` (`test_e2e_notifica_confirmacao_e_pronto`) | PASS ✅ |
| Estado ilegal irrepresentável (Consumo tipo-soma) | `dominio/pedido.py:29-49` (`NoLocal \| ParaViagem \| Delivery`) | `tests/test_dominio.py:69-81` (`test_consumo_e_tipo_soma_exaustivo`, `match` exaustivo) | PASS ✅ |
| Máquina de estados / fail-fast | `dominio/pedido.py:66-73` (`_TRANSICOES`, SSoT da máquina) + `:99-103` (`_transicionar` levanta `TransicaoInvalida`) + `:107-108` (`PedidoVazio`) | `tests/test_dominio.py:44-48` (`test_transicao_ilegal_e_recusada`), `:39-41` (pedido vazio), `:51-54` (item pós-confirmar) | PASS ✅ |
| Mecanismo × política (calcular_total + estratégias) | mecanismo `servicos/conta.py:16-26` (`calcular_total`); políticas `adaptadores/precos.py:23` (`PrecoDeTabela`), `:32` (`PrecoHappyHour`) | `tests/test_precificacao.py:39-49` (`test_mesmo_mecanismo_totais_diferentes` — mesmo mecanismo, 2 políticas, totais 104 vs 80) | PASS ✅ |
| Assincronicidade (cozinha gather + Semaphore) | `servicos/cozinha.py:53-55` (um `Semaphore` por estação), `:67` (`async with` = contenção), `:85` (`asyncio.gather`) | `tests/test_cozinha_async.py:16-28` (estações distintas correm em paralelo), `:31-43` (mesma estação serializa) | PASS ✅ |

**6/6 princípios com aplicação e teste identificados. Nenhum princípio ficou sem cobertura.**

---

## Gaps ranqueados (não-bloqueantes)

1. **Fronteira do happy hour sem teste** — nenhum teste exercita `hora == 20` (fim exclusivo da
   janela). A mutação `<` → `<=` sobrevive. Fix sugerido: adicionar
   `assert PrecoHappyHour().preco_do_item(chopp, ContextoPreco(hora=20)) == Dinheiro.de_reais(12)`
   (e opcionalmente `hora=17` como início inclusivo) a `test_precificacao.py`. Custo: 1-2 asserts.

---

## Confirmação de estado (read-only respeitado)

- `git diff --stat` → **vazio** (nada de `src/` alterado; todas as mutações revertidas ao original).
- `pytest -q` pós-reversão → **21 passed**.
- Único artefato novo (untracked): este `validation.md`. Sem commit, sem push, `docs/` intocado.

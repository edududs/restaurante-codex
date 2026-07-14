# Simulação "Sims": beats, os 4 fatores, e o turno que emerge

## O conceito

A simulação de restaurante tinha tarefas de duração fixa ("hambúrguer demora 6s,
ponto"). A fase Sims troca isso por tempo **emergente**: cada tarefa é vivida como uma
sequência de *beats* — micro-eventos que acontecem enquanto o NPC trabalha (fluiu,
se atrapalhou, se distraiu, trocou ideia com um colega, sofreu um evento externo). O
tempo final não é um número escolhido; é a soma de:

- **base** — o `segundos_preparo` do item, do cardápio (a mesma fonte de sempre);
- **4 fatores multiplicativos** — skill (0–100 → 1.3×…0.7×), fadiga (energia baixa
  encarece até 1.5×), experiência (nível acumulado acelera, com piso de 0.8×) e a soma
  dos deltas dos beats (Σ `beat.delta_s`);
- tudo com piso de 0.3s, para nenhuma tarefa "sumir".

O NPC (`Pessoa`) não é um número estático: cada tarefa concluída o deixa mais cansado
(energia cai) e mais experiente (XP sobe), e o humor deriva da energia + se houve
evento — que por sua vez realimenta os *próximos* beats (mau humor puxa mais
`ATRAPALHOU`/`DISTRAIU`). É a "vida interior" do Sims, mas 100% determinística: dado
o mesmo `seed`, o mesmo turno acontece byte-a-byte, sempre.

## Onde ver no código

- **O átomo**: `src/restaurante/dominio/beats.py` — `Beat(tipo, texto, delta_s)` e o
  enum `TipoBeat` (`CONCENTRADO`, `INSPIRADO`, `ATRAPALHOU`, `DISTRAIU`, `INTERAGIU`,
  `EVENTO`).
- **O NPC**: `src/restaurante/dominio/pessoas.py` — `Pessoa` (frozen), `Personalidade`
  (foco/sociável/disciplina/criatividade), `Humor`, e a evolução pura
  `aplicar_conclusao(pessoa, estacao, houve_evento) -> Pessoa` (gasta energia, ganha
  XP, recalcula humor — sem mutar a `Pessoa` original).
- **Os 4 fatores**: `src/restaurante/servicos/modelo_tempo.py`, função
  `duracao_tarefa(pessoa, item, beats) -> DuracaoTarefa` — função pura, devolve o
  breakdown inteiro (`mult_skill`, `mult_fadiga`, `mult_xp`, `soma_beats`, `total`) para
  qualquer apresentador mostrar o "porquê" do número.
- **A política (quais beats acontecem)**: porta `src/restaurante/portas/situacoes.py`
  (`GeradorDeSituacoes.gerar`) + adapter concreto
  `src/restaurante/adaptadores/situacoes_sims.py` (`SituacoesSims`) — usa `personalidade`,
  `humor`, `skill` e um `random.Random(seed)` injetado para sortear a história de cada
  tarefa. É *mechanism×policy*: o motor nunca decide isso.
- **O motor**: `src/restaurante/servicos/motor.py` — `planejar_turno(...)` é **puro**
  (dado seed + roster + times + pedidos, computa o turno inteiro, sem I/O nem espera);
  `reproduzir(plano, relogio, apresentador)` é a casca **async** fina que só dá o
  ritmo (dorme via a porta `Relogio` entre eventos) e emite cada `SimEvent` em ordem.
- **O elenco (SSoT)**: `src/restaurante/adaptadores/elenco.py` —
  `criar_elenco() -> (roster, times)` e `BIOS` (a "ficha Sims" de cada NPC).
- **A pele**: `src/restaurante/adaptadores/apresentador_rich.py` — `ApresentadorRich`,
  o único arquivo do projeto que importa `rich`. Durante o turno, imprime blocos em
  stream (pedido recebido, tarefa iniciada, cada beat colorido por tipo, tarefa
  concluída com o mini-breakdown, pedido pronto). Ao fim (`TurnoResumo`), desenha uma
  timeline/Gantt por NPC e uma tabela de stats (tarefas, tempo, XP, eventos, energia,
  humor, bio).
- **Rodando**: `uv run python demo_sim.py` (usa `RelogioReal(escala=0.25)` para caber em
  segundos). Testes: `tests/test_sim_nucleo.py` (beats/pessoas/modelo de tempo),
  `tests/test_sim_motor.py` (planejamento + replay), `tests/test_sim_rich.py` (o
  renderer, com um `Console` injetado escrevendo num `io.StringIO`).

## Quando aplicar

Quando o "quanto tempo isso leva" não é um fato fixo do domínio, mas o resultado de
**quem** faz, **como** essa pessoa está, e **o que aconteceu** no caminho — e você quer
que essa variação seja visível, testável e determinística (mesma seed → mesmo turno),
não um `random.uniform()` solto sem rastro. O padrão (fatores multiplicativos + soma de
eventos discretos, tudo com breakdown exposto) serve para qualquer simulação que precise
"mostrar o porquê" de um número, não só entregá-lo.

## Quando NÃO — o freio

Não modele beats para tarefas onde a variação não importa ou não deve ser visível ao
usuário — é cerimônia sem ganho (YAGNI). O próprio repo tem o contraste ao lado:
`servicos/cozinha.py` (fase pré-Sims) ainda usa `segundos_preparo` fixo para o fluxo de
pedidos "de produção" (`demo.py`) — ali o interesse é mostrar `asyncio.gather`/
`Semaphore`, não vida interior de NPC, e duração fixa é a escolha mais simples que
resolve. Beats também não substituem aleatoriedade genuína de teste de estresse: eles
são uma **política determinística** (`seed` fixa a história), não uma forma de gerar
carga realista não-determinística — se você precisa disso, é outra ferramenta.

## Experimento

Abra `src/restaurante/adaptadores/elenco.py` e mude a skill de chapa da Ana:
`{Estacao.CHAPA: 92, ...}` para, digamos, `{Estacao.CHAPA: 20, ...}` — uma novata em vez
de craque. Rode `uv run python demo_sim.py` de novo com a mesma `SEED`: o
`mult_skill` de cada hambúrguer que a Ana prepara sobe (perto de 1.3× em vez de perto de
0.7×), a tarefa demora visivelmente mais na timeline final, e o breakdown impresso em
cada `TarefaConcluida` mostra o número mudando. Troque só a `SEED` em `demo_sim.py` (com
as skills originais) e repare que a *história* dos beats muda — outros NPCs se atrapalham,
outros fluem — mas a fórmula e o formato do turno continuam os mesmos: é a política
(`SituacoesSims`) mudando, não o mecanismo (`duracao_tarefa`).

# Spec — Simulação "Sims" do Restaurante

**Data:** 2026-07-13
**Status:** aprovado (brainstorming) → em execução
**Orquestração:** Aegis 0.4 (projeto `simulacao-sims`) + gate maker≠checker
**Régua transversal:** skill `codex-engenharia` em todo maker.

## Objetivo

Transformar a simulação atual (tarefa = duração fixa) numa simulação **à la The Sims**:
cada NPC tem ritmo, história e status próprios, e o tempo de cada tarefa **emerge** de
micro-eventos (*beats*) que a pessoa vive enquanto executa — se atrapalhou, se inspirou,
se distraiu, conversou com um colega, sofreu um evento. Apresentação bonita com **Rich**
(híbrido: blocos em stream durante + timeline/Gantt e stats ao final).

Aditivo: **reusa** o domínio existente (`Dinheiro`, `Cardapio`, `Pedido`, ports & adapters,
`Cozinha`). Nada de rewrite.

## Não-objetivos (YAGNI)

- Sem persistência em banco, sem rede, sem input interativo em tempo real.
- Sem IA/LLM em runtime — as "situações" são política determinística semeada por `seed`.
- Sem engine de jogo genérica; modelamos só o que este restaurante precisa.

## O coração: modelo de *beats*

Uma tarefa é uma **sequência de beats**. O tempo final = fórmula-base modulada pelos
4 fatores + a soma dos deltas dos beats. Determinístico dado um `seed` (mesma seed →
mesma "história"), o que torna tudo testável.

### Beat (dominio/beats.py)
`Beat(tipo: TipoBeat, texto: str, delta_s: float)` — frozen. `TipoBeat` (enum):
`CONCENTRADO` (Δ0), `INSPIRADO` (Δ−), `ATRAPALHOU` (Δ+), `DISTRAIU` (Δ+ pequeno),
`INTERAGIU` (Δ+ pequeno; interação entre NPCs), `EVENTO` (Δ variável: queimou/refazer,
equipamento falhou, rush). `texto` é a fala/descrição para o Rich ("pensou na ex 💭").

## Domínio: a Pessoa (NPC) — dominio/pessoas.py

`Pessoa` frozen (snapshot imutável; evolui via funções puras que devolvem nova Pessoa):
- `id: str`, `nome: str`
- `personalidade: Personalidade` — frozen: `foco`, `sociavel`, `disciplina`,
  `criatividade` (0–100). Enviesa a distribuição de beats.
- `skills: Mapping[Estacao, int]` (0–100) — proficiência por estação.
- `energia: int` (0–100) — stamina; cai com o trabalho (fadiga).
- `experiencia: Mapping[Estacao, int]` — XP por estação; evolui.
- `humor: Humor` (enum: `INSPIRADO`, `NEUTRO`, `CANSADO`, `ESTRESSADO`) — derivado de
  energia + eventos; realimenta a geração de beats.

Funções puras: `aplicar_conclusao(pessoa, estacao, houve_evento) -> Pessoa` (gasta energia,
ganha XP, atualiza humor). `nivel(xp) -> int`. Estado ilegal irrepresentável: energia/skill
fora de 0–100 falham na construção (fail-fast).

## Os 4 fatores (como o tempo emerge)

`modelo_tempo.duracao_tarefa(pessoa, item, beats) -> DuracaoTarefa` — **função pura**:
- `base = item.segundos_preparo`
- `mult_skill = 1.3 - 0.6 * skill/100` (skill 0 → 1.3×; 100 → 0.7×)
- `mult_fadiga = 1 + (100 - energia)/100 * 0.5` (cansado → até 1.5×)
- `mult_xp = max(0.8, 1 - nivel*0.03)` (experiência acelera, piso 0.8×)
- `soma_beats = Σ beat.delta_s`
- `total = max(0.3, base * mult_skill * mult_fadiga * mult_xp + soma_beats)`
`DuracaoTarefa` carrega o breakdown (cada fator + beats) para o Rich mostrar o "porquê".

## Situações (a política Sims) — porta + adapter

- **Porta** `portas/situacoes.py`: `GeradorDeSituacoes.gerar(pessoa, item, rng) -> list[Beat]`.
- **Adapter** `adaptadores/situacoes_sims.py`: a política concreta. Usa `rng` (semeado),
  `personalidade`, `humor`, `skill`, `energia` para decidir quais beats acontecem e sua
  intensidade. Ex.: baixa `disciplina` + `CANSADO` → mais `DISTRAIU`/`ATRAPALHOU`; alta
  `criatividade` na salada → `INSPIRADO`; alta `sociavel` → `INTERAGIU`. Eventos raros
  (`EVENTO`) por probabilidade. É mechanism×policy: o motor não conhece esta lógica.

## Times — dominio/times.py

`Time` frozen: `nome`, `membros: tuple[str,...]` (ids), `responsabilidades: frozenset[Estacao]`,
`modo: ModoExecucao` (`FOCADO`|`MULTITAREFA`). A responsabilidade decide quais NPCs pegam
quais estações; o modo enviesa levemente o desempenho (freio: manter simples).

## Motor — servicos/motor.py (async)

Orquestra: recebe pedidos + roster (SSoT de pessoas) + times + gerador + modelo_tempo +
relógio + apresentador + `seed`. Para cada item do pedido: escolhe NPC apto (time
responsável pela estação, disponível), respeita a capacidade da estação (`asyncio.Semaphore`,
reusa a mecânica da `Cozinha`), gera beats, emite `SimEvent`s, dorme via **porta Relógio**
(escala/real), calcula duração, evolui a Pessoa, registra a **timeline** (início/fim por
tarefa/NPC). Determinístico via `random.Random(seed)`.

### Portas de saída/tempo
- `portas/relogio.py`: `Relogio.dormir(segundos)` async. Adapters: `relogio_real` (asyncio.sleep
  escalado) e `relogio_fake` (avança relógio lógico instantâneo; testes sem espera real).
- `portas/apresentador.py`: `SimEvent` (união: `PedidoRecebido`, `TarefaIniciada`,
  `BeatOcorreu`, `TarefaConcluida`, `PedidoPronto`, `TurnoResumo`) + `Apresentador.emitir(evento)`.

## Pele Rich — adaptadores/apresentador_rich.py

Consome `SimEvent`. **Híbrido**:
- **Durante:** `rich.live.Live` com blocos em stream por pedido/estação, mostrando cada beat
  (texto + Δ) e um painel de status (NPCs: barra de energia, humor, skill; estações ocupadas).
- **Ao final:** timeline/Gantt (quem fez o quê e quando) + tabela de stats por NPC (tarefas,
  tempo total, XP ganho, eventos sofridos) e por time. `rich` entra como dependência, isolada
  neste adapter. O motor **não importa** rich. Teste usa `ApresentadorColetor` (coleta eventos).

## Determinismo & testes

Todo caminho de decisão passa por `rng = random.Random(seed)`. Testes-chave:
- **Determinismo:** mesma seed → mesma lista de beats e mesma duração (byte-a-byte).
- **Fatores:** skill↑ reduz tempo; energia↓ aumenta; xp↑ reduz; beats somam.
- **Evolução:** após N tarefas, energia cai e XP sobe monotonicamente.
- **Motor e2e:** com `relogio_fake` + coletor, um turno de pedidos produz eventos coerentes;
  estações da mesma capacidade serializam; timeline consistente.
- **Apresentador:** coletor recebe início+fim de cada tarefa e um `TurnoResumo`.

## Aderência ao Codex (checagem de review)

SSoT (roster/skills/cardápio) · SoC/4 camadas · DIP (situações/relógio/apresentador por porta) ·
mechanism×policy (motor×situações, modelo_tempo×fatores) · estado ilegal irrepresentável
(Beat/SimEvent como tipos-soma; stats 0–100 validados) · fail-fast · KISS/YAGNI (não-objetivos).

## Fases (task graph Aegis, cada uma com gate maker≠checker)

- **Fase 1 — Núcleo Sims (puro, determinístico):** `pessoas`, `beats`, `situacoes`(porta+adapter),
  `modelo_tempo` + testes deterministas. Gate: ruff/pyright/pytest verde + determinismo provado.
- **Fase 2 — Times & motor async:** `times`, `relogio`(porta+2 adapters), `apresentador`(porta),
  `motor` + testes e2e com relógio fake. Gate idem + concorrência/estação provada.
- **Fase 3 — Pele Rich:** `apresentador_rich` (blocos+timeline+stats), wiring em `app.py`,
  `demo_sim.py`, `docs/07-simulacao-sims.md`, README + novo GIF. Gate idem + demo roda.

Cada task: maker (sub-agente Sonnet) implementa sob o Codex; Verifier independente (checker)
roda gate + discrimination sensor e grava `gate_result` no Aegis. Push só no fim, com aval do Eduardo.

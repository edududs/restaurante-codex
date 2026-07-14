# Config validado: Pydantic v2 no boundary

> Como externalizamos nomes, personagens, cores e cenário para `config/*.json` e os
> validamos na borda com Pydantic v2 — mantendo o domínio puro. O ensino é este doc + os
> comentários `CODEX:` em `src/restaurante/config/`; a config em si é funcional (dirige a
> simulação), não um enfeite.

## O que é Pydantic v2

Uma biblioteca de *parsing* e validação orientada a tipos: você declara a FORMA que um
dado deveria ter (um `BaseModel`, ou qualquer tipo via `TypeAdapter`) e o Pydantic
transforma dado cru (`dict`/JSON, digitado como `Any`) nesse tipo — ou recusa, com um
`ValidationError` que aponta o path exato do campo que falhou. Não é um verificador que
roda "por cima" de dados já em uso (isso seria `assert`/`if` espalhado); é o PASSO que
produz o dado, e só devolve algo se ele já for válido.

### Como funciona por dentro (v2)

Vale saber, porque explica o "SOTA":

- **Núcleo em Rust (`pydantic-core`).** No v2, a validação não roda em Python interpretado
  — cada modelo é compilado num *validador* (um `SchemaValidator`) executado por uma engine
  em Rust. É por isso que o v2 é ~5–50× mais rápido que o v1 e por que validar na borda
  "de graça" é viável mesmo em volume. Seu `BaseModel` em Python é a *declaração*; o
  trabalho acontece no core compilado.
- **O pipeline de um campo.** Para cada campo o core roda, em ordem: *before-validators*
  (recebem o dado CRU, podem coagir/normalizar) → a **validação do tipo** (é `int`? bate a
  `Field(ge=0)`?) → *after-validators* (recebem o dado JÁ no tipo certo, refinam regras).
  Usamos os dois extremos: nenhum before aqui, e um **`AfterValidator`** em
  `CenarioCfg.escala` (`_escala_positiva`) — recebe o `float` já parseado e recusa `<= 0`.
  (Há ainda `WrapValidator`, que embrulha o passo inteiro e decide se chama o core ou não —
  não precisamos dele.)
- **`model_validator` roda depois dos campos.** Enquanto um `field_validator`/`AfterValidator`
  vê um campo, o `@model_validator(mode="after")` roda com o objeto INTEIRO já montado — o
  lugar de regras cross-field (ver `ElencoCfg`, adiante).
- **Strict vs lax.** Por padrão o v2 é *lax*: coage quando faz sentido (a string `"7"` de um
  env var vira `int 7`; `"0.001"` vira `float`). Isso é o que faz `RESTAURANTE_ESCALA=0.001`
  (sempre string no ambiente) funcionar. Em modo *strict* ele recusaria a coerção. Escolha
  consciente: lax na borda (o mundo externo manda string), tipos exatos por dentro.
- **`ValidationError` estruturado.** O erro não é uma string solta: é uma lista de erros com
  `loc` (o path até o campo), `type` (o código do erro) e `msg`. É o que dá o fail-fast
  preciso — "`escala` — Value error, escala deve ser > 0" aponta o campo, não o arquivo todo.

## "Parse, don't validate"

O princípio-guia da Fase 5. A diferença entre as duas palavras do título:

- **Validate**: espalhar checagens ("isso está certo?") pelo código, toda vez que o
  dado é usado. O tipo continua "genérico" (`dict`, `str`) depois da checagem — nada
  impede alguém de usá-lo sem checar de novo, ou de esquecer uma checagem numa rota
  nova.
- **Parse**: fazer a checagem UMA VEZ, na borda (o *boundary* — onde o dado cru entra
  no sistema), produzindo um tipo NOVO que só existe se já for válido. Todo o resto do
  programa não precisa (e não pode) desconfiar do dado de novo — o tipo já prova.

Nesta fase, o boundary é a leitura dos arquivos `config/*.json`. Antes de existir
`src/restaurante/config/`, o "cardápio" era um dict Python hardcoded direto no domínio
— sempre válido por construção, porque só o programador editava. Agora que o dado vem
de fora (um arquivo editável por qualquer um, sem type checker olhando), o parse no
boundary é o que garante a mesma invariante.

## Por que validar no boundary (não no domínio)

Duas razões, ambas já princípios deste repo antes da Fase 5:

- **Fail-fast** (`docs/03-estado-ilegal-e-fail-fast.md`): um erro deve aparecer o mais
  perto possível da causa. Se `config/elenco.json` citar um NPC que não existe, o erro
  certo é `ValidationError: time 'Bar' cita npc(s) inexistente(s): [...]` na hora de
  carregar — não um `KeyError` sem contexto três camadas depois, dentro de
  `servicos/motor.py`, quando o turno já está rodando.
- **Make Illegal States Unrepresentable**: depois do `carregar_*`, o resto do programa
  trabalha só com `dominio/*` — dataclasses puras que a Fase 4 (e antes) já provou
  imutáveis, tipadas e auto-validadas (`Dinheiro` recusa negativo, `Pessoa` recusa
  atributo fora de 0–100). O boundary Pydantic é a MESMA filosofia aplicada uma camada
  antes: o estado ilegal (JSON incompleto/incoerente) nem chega a virar um objeto de
  domínio.

O domínio (`dominio/*`) continua sem importar Pydantic — zero acoplamento. Só
`src/restaurante/config/` (o boundary) conhece a biblioteca; `config/carregador.py` é a
ÚNICA ponte que faz `ModeloValidado -> tipo de domínio`.

## As features SOTA usadas (e onde)

- **`ConfigDict(extra="forbid", frozen=True)`** — `src/restaurante/config/modelos.py::_Base`,
  a base comum de todo modelo de config. Chave desconhecida no JSON (um typo tipo
  `"esatcao"`) vira erro na hora, em vez de ser silenciosamente ignorada; `frozen=True`
  mantém o objeto validado imutável, o mesmo espírito do domínio.
- **`Annotated[...]` + `type` (PEP 695) para tipos reutilizáveis** —
  `src/restaurante/config/modelos.py::Atributo` (`type Atributo = Annotated[int,
  Field(ge=0, le=100)]`), usado em `PersonalidadeCfg` e `NpcCfg.skills`. Uma faixa
  (0–100) declarada uma vez, reutilizada em vários campos — SSoT da constraint.
- **Discriminated unions** — `src/restaurante/config/modelos.py::ConsumoCfg`
  (`Annotated[MesaCfg | ViagemCfg | DeliveryCfg, Field(discriminator="tipo")]`),
  mapeado para o domínio em `src/restaurante/config/carregador.py::_consumo_do_dominio`.
  O campo `"tipo"` no JSON escolhe o variant certo direto — espelha o tipo-soma
  `dominio/pedido.py::Consumo` (`NoLocal | ParaViagem | Delivery`) uma camada antes.
- **`TypeAdapter`** — `src/restaurante/config/modelos.py::CARDAPIO_ADAPTER`
  (`TypeAdapter(list[ItemCfg])`), usado em
  `src/restaurante/config/carregador.py::carregar_cardapio`. Valida o array JSON
  top-level do cardápio sem precisar embrulhar numa `BaseModel` só para isso — o jeito
  Pydantic v2 de validar QUALQUER tipo, não só classes.
- **`model_validator(mode="after")`** — `src/restaurante/config/modelos.py::ElencoCfg`,
  dois validators: `_membros_existem` (todo `membro` de um time é um `id` de NPC
  declarado) e `_cobre_todas_as_estacoes` (a união das responsabilidades dos times
  cobre as 4 `Estacao`). Regra cross-field — atravessa múltiplos campos/itens da
  lista — que um `Field(...)` isolado não consegue expressar.
- **`AfterValidator`** — `src/restaurante/config/modelos.py::_escala_positiva`, plugado
  em `CenarioCfg.escala: Annotated[float, AfterValidator(_escala_positiva)]`: a escala
  do relógio tem que ser > 0 (senão o tempo da reprodução para ou anda pra trás).
- **`pydantic-settings` com precedência env > json > default** —
  `src/restaurante/config/modelos.py::CenarioCfg` + `settings_customise_sources`
  (retorna `(env_settings, JsonConfigSettingsSource(settings_cls), init_settings)`).
  Permite `RESTAURANTE_SEED=7 uv run python demo_sim.py` sem editar
  `config/cenario.json` — a mesma "cascata de config" 12-factor, com cada camada já
  validada pelo mesmo modelo.
- **`StrEnum`** — `dominio/cardapio.py::Estacao`/`Categoria`,
  `dominio/pessoas.py::Humor`, `dominio/times.py::ModoExecucao`,
  `dominio/beats.py::TipoBeat`. Faz o `.value` (que já era string) virar o próprio
  round-trip JSON: o Pydantic valida `"chapa"` direto para `Estacao.CHAPA` sem
  conversão manual, e a serialização de volta também é direta.
- **`typing.assert_never`** — guarda de exaustividade nos três `match` fechados do
  projeto: `adaptadores/apresentador_rich.py::ApresentadorRich.emitir`,
  `adaptadores/apresentador_textual.py::SimuladorApp.emitir` (ambos sobre `SimEvent`) e
  `servicos/motor.py::_descreve_consumo` (sobre `Consumo`) — e o novo
  `config/carregador.py::_consumo_do_dominio` (sobre `ConsumoCfg`). Não muda o
  comportamento (o `match` já era exaustivo, o type checker já cobrava em tempo de
  tipo); torna a exaustividade uma garantia explícita em RUNTIME também — se a união
  ganhar um caso novo e algum `match` esquecer de tratá-lo, o programa falha alto ali,
  em vez de silenciosamente cair no `case _` errado.

## Onde ver no código

- **Os modelos (a validação em si)**: `src/restaurante/config/modelos.py`.
- **O parse → domínio (a ponte)**: `src/restaurante/config/carregador.py` — quatro
  `carregar_*` cacheados (`@functools.cache`), cada um lendo um `config/*.json` e
  devolvendo tipos 100% `dominio/*`.
- **A fachada do cardápio**: `src/restaurante/config/catalogo.py::Cardapio` — mesma API
  de sempre (`buscar`/`todos`), agora backed pelo JSON em vez de um dict hardcoded.
- **Os dados default, editáveis sem tocar em Python**: `config/cardapio.json`,
  `config/elenco.json`, `config/tema.json`, `config/cenario.json` (raiz do repo).
- **Quem consome**: `adaptadores/elenco.py::criar_elenco`/`BIOS`,
  `adaptadores/narracao.py::frase_beat`, `demo_sim.py`, `demo_tui.py` — nenhum deles
  importa Pydantic; todos passam por `config/carregador.py`.
- **Os testes**: `tests/test_config.py` — caminho feliz, `extra="forbid"`,
  discriminated union, os dois `model_validator` cross-field, e a precedência
  env > json > default do `CenarioCfg`.

## Quando aplicar

Quando um dado que hoje é hardcoded no código precisa virar editável por fora (design,
game design, ajuste fino sem deploy) — e esse dado tem uma FORMA com invariantes reais
(faixas, união fechada, regra cross-field), não só um `dict` solto. O boundary Pydantic
vale a pena quando "o que pode dar errado no JSON" já é uma lista concreta (typo de
chave, faixa inválida, referência cruzada quebrada), não uma preocupação hipotética.

## Quando NÃO — o freio

Não é para todo dado que virou "config". Se o dado não tem invariante nenhuma além do
próprio tipo primitivo (uma string livre, um número sem faixa), um `dict`/`TypedDict`
lido direto é KISS suficiente — criar um `BaseModel` com `Field(...)` vazio é
cerimônia sem ganho. E o domínio (`dominio/*`) continua com a regra de sempre: zero
Pydantic ali. Se um dia uma validação de domínio "vazar" para dentro de
`dominio/pessoas.py` importando `pydantic`, é o mesmo cheiro de política vazando pro
mecanismo (`docs/04-mecanismo-e-politica.md`) — só que na direção config → domínio.

## Experimento

Abra `config/elenco.json` e apague a estação `"bar"` da lista de `responsabilidades`
do time `"Bar"` (deixando só `["saladas"]`, por exemplo). Rode `uv run python
demo_sim.py`: em vez do turno rodar e falhar tarde — ou pior, silenciosamente never
escalar ninguém pro bar — o programa recusa a config na hora de carregar, com uma
`ValidationError` de `ElencoCfg._cobre_todas_as_estacoes` apontando exatamente que
`bar` ficou sem responsável. Desfaça a edição e repita trocando um `"id"` de NPC em
`membros` por um nome que não existe: o erro agora vem de `_membros_existem`. As duas
falhas acontecem na leitura do arquivo, bem antes de qualquer `Pedido` ser criado.

# Mechanism, not Policy (Strategy)

## O conceito

Separe o **mecanismo** (o "como", genérico e estável) da **política** (o "qual regra
usar agora", variável e plugável). O mecanismo recebe a política de fora e a consulta
— nunca decide sozinho qual regra aplicar. É o Strategy Pattern com outro nome.

## Onde ver no código

- **O mecanismo**: `calcular_total` em `servicos/conta.py`. Ele sabe *percorrer* as
  linhas do pedido, multiplicar por quantidade e somar — mas não sabe se hoje é happy
  hour. Ele recebe uma `EstrategiaPreco` (porta em `portas/precificacao.py`) e um
  `ContextoPreco` (hoje, só carrega `hora: int`) como parâmetros.
- **As políticas**: `adaptadores/precos.py`. `PrecoDeTabela.preco_do_item` ignora o
  contexto e devolve o `preco_base` do cardápio. `PrecoHappyHour.preco_do_item` aplica
  50% de desconto (`_DESCONTO_HAPPY_HOUR`) em itens de `Categoria.BEBIDA` quando a hora
  cai entre `_HAPPY_HOUR_INICIO` (17) e `_HAPPY_HOUR_FIM` (20).
- **A escolha da política mora fora do mecanismo**: em `app.py`,
  `montar_restaurante(happy_hour=...)` decide qual `EstrategiaPreco` instanciar
  (`PrecoHappyHour()` ou `PrecoDeTabela()`) e injeta em `ServicoBalcao`. `conta.py`
  nunca é editado para adicionar uma política nova.
- **O anti-padrão evitado**, nomeado explicitamente no `# CODEX:` de
  `portas/precificacao.py`: um `if hora < 19` enterrado direto no cálculo do caixa —
  isso seria política vazando pro mecanismo, misturando "como somar" com "qual regra
  vale agora".
- `demo.py::cena_politica_de_preco` mostra as duas políticas lado a lado consumindo o
  *mesmo* `calcular_total`.

## Quando aplicar

Quando uma regra de negócio varia por contexto (hora, categoria de cliente, campanha)
e essa variação já é real — não hipotética. O sinal de que vale a pena: você consegue
nomear hoje pelo menos duas implementações concretas da política (aqui,
`PrecoDeTabela` e `PrecoHappyHour` já existem as duas).

## Quando NÃO — o freio

Rule of Three / AHA, citado no próprio `# CODEX:` de `adaptadores/precos.py`: o repo
**não** criou uma "mega-engine de regras configurável" (desconto por %, por item, por
cupom, por hora...) — só as duas políticas que já são necessárias de verdade. A
terceira variação só ganha abstração quando aparecer com evidência, não por
adivinhação de requisito futuro. Se sua "política" só tem uma implementação e nenhum
plano concreto de ganhar uma segunda, um `if` simples dentro da própria função ainda é
KISS — criar `EstrategiaPreco` prematuramente é o custo 10x da abstração errada.

## Experimento

Em `servicos/conta.py`, dentro de `calcular_total`, adicione um desvio direto: se
`linha.item.nome == "Chopp"`, force `preco_unitario = Dinheiro.de_reais(0)` — ignorando
a `estrategia` recebida. Rode `uv run pytest tests/test_precificacao.py`: o teste
`test_mesmo_mecanismo_totais_diferentes` (que espera `Dinheiro.de_reais(104)` com
`PrecoDeTabela` e `Dinheiro.de_reais(80)` com `PrecoHappyHour`) vai falhar, porque
agora o "mecanismo" decidiu uma política por conta própria em vez de delegar — o
sintoma exato de política vazando pro mecanismo.

# Estado ilegal irrepresentável e fail-fast

## O conceito

Make Illegal States Unrepresentable: modele os dados de forma que um estado inválido
não caiba no tipo — o compilador/type checker rejeita antes de rodar. Fail-fast: quando
o tipo não dá conta sozinho, valide no boundary (na construção) e falhe alto, não três
camadas depois.

## Onde ver no código

- **O tipo-soma `Consumo`**, em `dominio/pedido.py`: `NoLocal` (exige `mesa: int`),
  `ParaViagem` (não carrega nada) e `Delivery` (exige `endereco: str`), unidos como
  `Consumo = NoLocal | ParaViagem | Delivery`. Compare com a alternativa ingênua de
  três campos opcionais (`mesa: int | None`, `endereco: str | None`...) — essa
  permitiria os dois estados ilegais que o tipo-soma proíbe por construção: nenhum
  preenchido, ou mais de um preenchido. O `match` exaustivo em
  `tests/test_dominio.py::test_consumo_e_tipo_soma_exaustivo` mostra o type checker
  cobrando os três casos.
- **A máquina de estados**: `_TRANSICOES` em `dominio/pedido.py`, um único
  `dict[EstadoPedido, frozenset[EstadoPedido]]` — a SSoT de "quem pode virar o quê".
  `Pedido._transicionar` consulta esse mapa e levanta `TransicaoInvalida`
  (`dominio/erros.py`) se a transição não está lá.
- **Fail-fast no boundary**: `Pedido.confirmar()` recusa pedido sem linhas
  (`PedidoVazio`) antes de tentar transicionar; `Pedido.com_item()` recusa adicionar
  item fora do estado `RASCUNHO`.
- **`Dinheiro`** (`dominio/dinheiro.py`): `__post_init__` recusa centavos negativos na
  construção — não deixa um valor inválido nascer para explodir depois no caixa.
  Internamente é `int` (centavos), nunca `float` — evita o bug clássico de
  `0.1 + 0.2 != 0.3` em ponto flutuante, e é mais simples que `Decimal` (Least Power).

## Quando aplicar

Sempre que existir uma decisão de "só um destes casos é válido por vez" (tipo-soma) ou
um fluxo com sequência rígida de estados (máquina de estados). E sempre que um valor
tiver uma invariante simples e barata de checar na criação (dinheiro não-negativo,
percentual entre 0 e 100 em `Dinheiro.aplicar_desconto`).

## Quando NÃO — o freio

Não valide o impossível. `Pedido` não checa, por exemplo, se `mesa` é um número que
existe fisicamente no restaurante — isso seria validação em excesso, empurrando lógica
de infraestrutura pro domínio. E nem toda variação vira tipo-soma: se amanhã surgisse
uma quarta forma de consumo *hipotética* e improvável, não se cria o caso "por via das
dúvidas" — isso é o mesmo YAGNI que rege quando criar uma porta nova. O fail-fast
também tem limite: falhar alto é bom na fronteira (construção, transição); não é
desculpa para exceções genéricas — cada erro é nomeado (`ValorMonetarioInvalido`,
`TransicaoInvalida`, `PedidoVazio`) para quem lê o `except` saber exatamente o que
quebrou.

## Experimento

Em `dominio/pedido.py`, no dicionário `_TRANSICOES`, adicione
`EstadoPedido.CONFIRMADO` ao conjunto de `EstadoPedido.PRONTO` (ou seja, permita pular
`EM_PREPARO`). Rode `uv run pytest tests/test_dominio.py`: nada quebra imediatamente,
porque nenhum teste cobre esse salto especificamente — o que já é um sinal de gap de
cobertura. Agora inverta o experimento: em `test_transicao_ilegal_e_recusada`, troque
`confirmado.entregar()` por `confirmado.iniciar_preparo()` (uma transição que *é*
legal). O teste vai falhar porque `pytest.raises(TransicaoInvalida)` não vê exceção
nenhuma — prova de que o freio (fail-fast) está de fato ativo para o caso ilegal
original.

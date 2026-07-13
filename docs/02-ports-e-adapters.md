# Ports & Adapters (DIP, DI, ISP)

## O conceito

Dependency Inversion Principle: serviços dependem de **interfaces** (`Protocol`), não
de bibliotecas concretas. Dependency Injection: as implementações concretas entram
"de fora" via construtor, num único lugar (o composition root). Interface Segregation
Principle: em vez de uma porta gorda, há 4 portas pequenas e focadas.

## Onde ver no código

- **As 4 portas**, cada uma um `Protocol` com 1–3 métodos: `portas/notificacao.py`
  (`Notificador.notificar`), `portas/pagamento.py` (`Pagamento.cobrar`),
  `portas/repositorio.py` (`RepositorioPedidos.salvar/buscar/listar`) e
  `portas/precificacao.py` (`EstrategiaPreco.preco_do_item`). Nenhuma tenta fazer as
  quatro coisas — é o ISP em ação.
- **Os adapters**, cada um implementando uma porta sem herdar nada explicitamente
  (`Protocol` é structural typing): `adaptadores/notificador_console.py`
  (`NotificadorConsole`), `adaptadores/pagamento_fake.py` (`PagamentoFake`),
  `adaptadores/repositorio_memoria.py` (`RepositorioMemoria`),
  `adaptadores/precos.py` (`PrecoDeTabela`, `PrecoHappyHour`).
- **A injeção**: `servicos/balcao.py`, `ServicoBalcao.__init__` recebe
  `repositorio: RepositorioPedidos`, `pagamento: Pagamento`, `notificador: Notificador`,
  `estrategia_preco: EstrategiaPreco` — quatro parâmetros tipados pelas portas, zero
  tipo concreto.
- **O composition root**: `app.py`, `montar_restaurante()` — o único módulo do sistema
  que importa `RepositorioMemoria`, `PagamentoFake`, `NotificadorConsole` e as
  estratégias de preço, e monta `ServicoBalcao` com elas.

## Quando aplicar

Toda dependência externa de verdade — algo que fala com rede, disco, ou que tem mais
de uma implementação plausível (gateway de pagamento, canal de notificação, storage,
regra de preço que varia). O teste da porta: "isso pode ter uma segunda implementação
um dia?" Se sim, ela merece uma interface.

## Quando NÃO — o freio

YAGNI: não crie uma porta para algo que nunca vai trocar. Se o sistema só vai ter *um*
jeito de calcular imposto pra sempre, uma função comum resolve — criar
`portas/imposto.py` com um único adapter é abstração especulativa (o freio do Codex:
"a abstração errada custa 10x"). Note que este repo também não criou porta pra
`Cardapio` (ele é a SSoT lida direto) nem pra `Cozinha` (é injetada como classe
concreta em `ServicoBalcao`, não como protocolo) — só ganham porta as dependências que
o próprio projeto já demonstra trocar (fake vs. real, tabela vs. happy hour).

## Experimento

Crie um `PagamentoQueRecusaTudo` em qualquer lugar (ex.: dentro do próprio teste) que
implementa `cobrar` levantando uma exceção, e injete-o em `montar_restaurante`
manualmente (chame `ServicoBalcao(..., pagamento=PagamentoQueRecusaTudo(), ...)` no
lugar de `PagamentoFake()`) num teste novo em `tests/`. Rode `uv run pytest`: o teste
deve passar mostrando que `ServicoBalcao` nunca percebeu a troca — nenhuma linha de
`servicos/balcao.py` mudou. Se em vez disso você tentasse importar `PagamentoFake`
direto dentro de `dominio/pedido.py`, o `uv run pyright`/`ruff` do pipeline reclamaria
da camada errada importando um adapter — é o freio funcionando ao contrário.

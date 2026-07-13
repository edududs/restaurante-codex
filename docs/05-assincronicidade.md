# Assincronicidade: `gather` e `Semaphore`

## O conceito

`await` significa "solto a CPU enquanto isso está esperando I/O; me acorde quando
terminar" — não é uma chamada bloqueante disfarçada. Um cozinheiro, enquanto o
hambúrguer frita sozinho na chapa, não fica parado olhando: vai montar a salada.
Dois mecanismos fazem o trabalho pesado deste repo: `asyncio.gather` (dispara várias
tarefas e espera todas — paralelismo lógico) e `asyncio.Semaphore` (um contador de
"vagas livres" que serializa quem disputa o mesmo recurso).

## Onde ver no código

Tudo mora em `servicos/cozinha.py`, classe `Cozinha`.

- **O recurso limitado**: no `__init__`, `self._bocas: dict[Estacao, asyncio.Semaphore]`
  — um semáforo por estação, inicializado com `capacidade` (padrão: 1 boca por
  estação, via `dict.fromkeys(Estacao, 1)`). Uma boca de chapa é literalmente isso: a
  chapa física só frita N coisas ao mesmo tempo.
- **A espera de I/O simulada**: `_preparar_linha` faz
  `async with self._bocas[estacao]:` (pega a boca, ou espera uma vaga liberar) e então
  `await asyncio.sleep(segundos * self._escala)` — o `sleep` representa "o prato está
  cozinhando sozinho"; durante esse tempo o event loop pode rodar outra tarefa.
- **O paralelismo lógico**: `preparar()` monta uma lista de corrotinas (uma por linha
  do pedido) e as dispara todas de uma vez com `await asyncio.gather(*tarefas)`. É por
  isso que um pedido com 3 pratos de estações diferentes não demora a *soma* dos
  tempos de preparo — demora o tempo do prato mais lento (o `max`, não a soma).
- **A prova em teste**: `tests/test_cozinha_async.py`.
  `test_estacoes_diferentes_correm_em_paralelo` prepara Chopp (BAR, 1s) + Batata
  (FRITADEIRA, 4s) e afirma que o tempo total fica perto de 0.4s, não 0.5s — provando
  que rodaram em paralelo. `test_mesma_estacao_serializa` prepara Hambúrguer (CHAPA)
  + Filé (CHAPA) com 1 boca só e afirma que o tempo total é *maior* que o item mais
  lento sozinho — provando que a mesma estação enfileira, não paraleliza.
- **Visível a olho nu**: `demo.py::cena_concorrencia` dispara 3 pedidos com
  `asyncio.gather` no nível do balcão e imprime timestamps reais — rode
  `uv run python demo.py` e compare os carimbos de tempo de cada `narrar(...)`.

## Quando aplicar

Trabalho **I/O-bound** e concorrente: várias operações que passam a maior parte do
tempo *esperando* algo externo (rede, disco, ou aqui, o "tempo de cozinhar" simulado),
onde você quer que a espera de uma não bloqueie o progresso das outras. `gather` quando
as tarefas são independentes e você quer todas rodando "ao mesmo tempo"; `Semaphore`
quando existe um recurso físico ou lógico com capacidade finita disputado por várias
tarefas.

## Quando NÃO — o freio

Não use `async` para trabalho **CPU-bound** puro (cálculo pesado, parsing grande,
compressão). Nesse caso não existe espera de I/O para "soltar a CPU" durante — a
thread fica ocupada calculando, e `async`/`await` não paraleliza cálculo (o Python tem
GIL; `asyncio` é concorrência cooperativa numa única thread). `calcular_total`, em
`servicos/conta.py`, é a prova por ausência no próprio repo: é uma função **síncrona**
(`def`, não `async def`) porque somar linhas de um pedido é CPU puro, instantâneo —
colocar `async` ali seria cerimônia sem ganho (mais um caso de KISS). Para CPU-bound de
verdade, a ferramenta certa é multiprocessing ou paralelismo real, não `asyncio`.

## Experimento

Em `servicos/cozinha.py`, no `__init__` de `Cozinha`, troque
`cap = capacidade or dict.fromkeys(Estacao, 1)` por um valor fixo de 5 bocas para toda
estação (`dict.fromkeys(Estacao, 5)`), ignorando o parâmetro `capacidade` recebido.
Rode `uv run pytest tests/test_cozinha_async.py`: `test_mesma_estacao_serializa`
constrói `Cozinha(capacidade=dict.fromkeys(Estacao, 1), ...)` esperando que Hambúrguer
e Filé (mesma estação, CHAPA) disputem 1 boca só e portanto serializem
(`assert decorrido > 0.55`). Com 5 bocas fixas os dois pratos cozinham em paralelo, o
tempo cai bem abaixo de 0.55s, e o teste falha — a contenção real de recurso que o
`Semaphore` modela deixou de existir.

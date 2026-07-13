# Camadas e direção das dependências

## O conceito

Separation of Concerns (SoC) em 4 camadas — esqueleto (`dominio/`, `portas/`), órgãos
(`servicos/`), sistema nervoso (`adaptadores/`) e a tomada (`app.py`). A regra que
mantém tudo desacoplado: **dependências apontam pra dentro**. O domínio não importa
nada de fora; quem depende dele são os órgãos e os adapters — nunca o contrário.

## Onde ver no código

A prova está nos `import`s de cada arquivo, não numa figura:

- `src/restaurante/dominio/pedido.py` importa só `dominio.cardapio` e `dominio.erros`
  — outro módulo do próprio esqueleto. Zero `asyncio`, zero adapter, zero I/O.
- `src/restaurante/servicos/balcao.py` (`ServicoBalcao`) importa `dominio.pedido` e as
  4 portas (`portas/notificacao.py`, `pagamento.py`, `precificacao.py`,
  `repositorio.py`) — nunca um adapter concreto.
- `src/restaurante/adaptadores/repositorio_memoria.py` (`RepositorioMemoria`) importa
  `dominio.pedido` (pra saber o tipo que guarda) e implementa a porta — a seta aponta
  do adapter pro domínio, nunca o inverso.
- `src/restaurante/app.py` (`montar_restaurante`) é o único arquivo do sistema que
  importa `RepositorioMemoria`, `PagamentoFake`, `PrecoDeTabela`/`PrecoHappyHour` e
  `NotificadorConsole` ao mesmo tempo — a "tomada" onde tudo se conecta.

## Quando aplicar

Sempre que a regra de negócio (o domínio) puder ser testada e entendida sem saber que
banco, gateway de pagamento ou terminal existem por trás. Se você consegue ler
`dominio/pedido.py` sem nunca ver a palavra `asyncio.sleep` de um adapter, a separação
está funcionando.

## Quando NÃO — o freio

Nem todo projeto precisa de 4 camadas nomeadas. Um script de 50 linhas que nunca vai
trocar de banco, nunca vai ganhar um segundo adapter, não precisa de `portas/`
separado — é cerimônia sem benefício (KISS). A separação paga a conta quando existe
pelo menos uma dependência externa real (I/O, vendor, storage) que algum dia pode
trocar. Aqui ela existe: pagamento, notificação, persistência e precificação são todos
plugáveis de propósito.

## Experimento

Em `src/restaurante/dominio/pedido.py`, adicione um `import asyncio` no topo e troque
uma linha de `_transicionar` para usar `await asyncio.sleep(0)` (isso obriga a função a
virar `async def`). Rode `uv run pytest tests/test_dominio.py`: os testes chamam
`.confirmar()`, `.iniciar_preparo()` etc. de forma síncrona — eles vão quebrar, porque
agora devolvem uma corrotina não-aguardada em vez de um `Pedido`. É o sinal de que
I/O (mesmo simulado) vazou pro esqueleto, que deveria ser puro.

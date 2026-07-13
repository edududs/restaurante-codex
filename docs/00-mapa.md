# Mapa de estudo

Índice curto. Cada linha aponta pro doc didático e pro arquivo real onde o conceito
vive. Leia na ordem — cada um pressupõe o anterior.

| # | Conceito | Doc | Arquivo no código |
| --- | --- | --- | --- |
| 1 | SoC, camadas, direção das dependências | [`01-camadas-e-dependencias.md`](01-camadas-e-dependencias.md) | estrutura de `src/restaurante/` |
| 2 | DIP, DI, ISP, composition root | [`02-ports-e-adapters.md`](02-ports-e-adapters.md) | `portas/`, `adaptadores/`, `app.py` |
| 3 | Estado ilegal irrepresentável, fail-fast, `Dinheiro` | [`03-estado-ilegal-e-fail-fast.md`](03-estado-ilegal-e-fail-fast.md) | `dominio/pedido.py`, `dominio/dinheiro.py` |
| 4 | Mechanism × Policy, Strategy | [`04-mecanismo-e-politica.md`](04-mecanismo-e-politica.md) | `servicos/conta.py`, `adaptadores/precos.py` |
| 5 | Assincronicidade: `gather` e `Semaphore` | [`05-assincronicidade.md`](05-assincronicidade.md) | `servicos/cozinha.py` |

Para cada conceito: **o que é**, **onde ver**, **quando aplicar**, **quando NÃO** (o
freio) e um **experimento** — uma mudança de uma linha que você faz de propósito pra
`uv run pytest` te pegar no ato.

Ponto de partida sempre é o mesmo:

```bash
uv run python demo.py      # veja funcionando, com timestamps
uv run pytest               # depois quebre algo e rode de novo
```

Veja também a tabela-resumo no [`README.md`](../README.md#mapa-conceito--onde-no-código--quando-usar).

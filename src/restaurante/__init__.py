"""Restaurante-Codex: um sistema de restaurante que ensina engenharia na prática.

As camadas (ordem de dependência — de dentro pra fora):
    dominio/      → contratos puros e regras. Zero I/O, zero vendor. (esqueleto)
    portas/       → interfaces (Protocols) para tudo que é externo.   (esqueleto)
    servicos/     → orquestração headless, inclusive a cozinha async. (órgãos)
    adaptadores/  → implementações concretas das portas.              (sistema nervoso)
    app.py        → composition root: monta tudo via injeção.
"""

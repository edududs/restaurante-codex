"""Serviços — a lógica headless que orquestra o domínio (os "órgãos").

Zero UI, zero `print` (a única exceção é a cozinha *chamar* um sink de narração que
lhe é injetado — ela não decide imprimir, quem decide é quem passou o sink). Estes
módulos são reutilizáveis e testáveis sem tocar em adapter concreto.
"""

"""Dinheiro — um value object que torna o bug clássico impossível.

CODEX: Make Illegal States Unrepresentable + Fail Fast (Parte IV) e KISS (Parte V).

    Dois estados ilegais que este tipo *proíbe por construção*:
      1. Dinheiro como `float`. `0.1 + 0.2 != 0.3` em ponto flutuante — modelar
         dinheiro como float é um bug esperando pra acontecer. Guardamos **centavos
         como int**: exato, e mais simples que trazer `Decimal` (o freio KISS
         escolhendo a peça menos poderosa que resolve — Least Power).
      2. Valor negativo. O construtor recusa (fail-fast) em vez de deixar um preço
         negativo contaminar o caixa lá na frente.

    `frozen=True`: imutável. Somar dois `Dinheiro` devolve um novo — nunca muta o
    original (evita aliasing surpresa; casa com POLA).
"""

from __future__ import annotations

from dataclasses import dataclass

from restaurante.dominio.erros import ValorMonetarioInvalido


@dataclass(frozen=True, slots=True)
class Dinheiro:
    """Uma quantia em reais, representada internamente em centavos inteiros."""

    centavos: int

    def __post_init__(self) -> None:
        # CODEX: Fail Fast — valida no boundary (a construção), não depois.
        if self.centavos < 0:
            raise ValorMonetarioInvalido(
                f"Dinheiro não pode ser negativo: {self.centavos} centavos."
            )

    @classmethod
    def de_reais(cls, reais: int, centavos: int = 0) -> Dinheiro:
        """Constrói a partir de reais + centavos (ex.: `Dinheiro.de_reais(12, 90)`)."""
        if centavos < 0 or reais < 0:
            raise ValorMonetarioInvalido(f"Valor inválido: {reais}.{centavos:02d}")
        return cls(reais * 100 + centavos)

    def __add__(self, outro: Dinheiro) -> Dinheiro:
        return Dinheiro(self.centavos + outro.centavos)

    def __mul__(self, quantidade: int) -> Dinheiro:
        if quantidade < 0:
            raise ValorMonetarioInvalido(f"Quantidade não pode ser negativa: {quantidade}")
        return Dinheiro(self.centavos * quantidade)

    def aplicar_desconto(self, percentual: int) -> Dinheiro:
        """Devolve um novo `Dinheiro` com `percentual`% de desconto (0–100)."""
        if not 0 <= percentual <= 100:  # noqa: PLR2004 (0 e 100 são os limites do conceito)
            raise ValorMonetarioInvalido(f"Percentual fora de 0–100: {percentual}")
        return Dinheiro(self.centavos * (100 - percentual) // 100)

    def __str__(self) -> str:
        return f"R$ {self.centavos // 100},{self.centavos % 100:02d}"


ZERO = Dinheiro(0)

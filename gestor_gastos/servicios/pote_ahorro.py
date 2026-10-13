"""Pote de ahorros: parte de una Billetera (composición)."""

from __future__ import annotations

from decimal import Decimal

from gestor_gastos.excepciones import AhorroInsuficienteError


class PoteDeAhorro:
    """Lleva el ahorro acumulado. Solo cambia con depositar() y retirar()."""

    def __init__(self) -> None:
        self.__saldo = Decimal("0.00")

    @property
    def saldo(self) -> Decimal:
        return self.__saldo

    def depositar(self, monto: Decimal) -> None:
        self.__saldo += monto

    def retirar(self, monto: Decimal) -> None:
        if monto > self.__saldo:
            raise AhorroInsuficienteError(monto, self.__saldo)
        self.__saldo -= monto

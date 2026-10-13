"""Datos de ejemplo basados en el uso real de la app de gastos."""

from __future__ import annotations

from datetime import date

from gestor_gastos.interfaces import Notificador, Repositorio
from gestor_gastos.modelos import (
    Ahorro,
    Categoria,
    Gasto,
    GastoRecurrente,
    Ingreso,
    Retiro,
    Usuario,
)
from gestor_gastos.servicios.billetera import Billetera


def crear_billetera_demo(repositorio: Repositorio, notificador: Notificador) -> Billetera:
    """Crea 2 usuarios, 6 categorías y 11 movimientos de octubre de 2026."""
    billetera = Billetera("Gastos de la casa", repositorio, notificador)

    edwin, novia = Usuario(1, "Edwin"), Usuario(2, "Novia")
    billetera.agregar_usuarios(edwin, novia)

    comida = Categoria("Comida", "🍔", ["Gasto"], limite_mensual=150)
    transporte = Categoria("Transporte", "🚗", ["Gasto"])
    casa = Categoria("Casa", "🏠", ["Gasto"])
    juegos = Categoria("Juegos", "🎮", ["Gasto"])
    trabajo = Categoria("Trabajo", "💼", ["Gasto", "Ingreso"])
    fondo = Categoria("Fondo de emergencia", "🏦", ["Ahorro", "Retiro"])
    billetera.agregar_categorias(comida, transporte, casa, juegos, trabajo, fondo)

    billetera.registrar(
        Ingreso(1, "600", edwin, trabajo, "Quincena", date(2026, 10, 15),
                periodo_pago="1-15 oct"),
        Ingreso(2, "450", novia, trabajo, "Quincena", date(2026, 10, 15),
                periodo_pago="1-15 oct"),
        Gasto(3, "250", edwin, casa, "Alquiler", date(2026, 10, 1), "Transferencia"),
        Gasto(4, "12.50", novia, comida, "Pizza", date(2026, 10, 3), "Tarjeta"),
        Gasto(5, "3.25", edwin, transporte, "Bus", date(2026, 10, 6)),
        Gasto(6, "86.40", novia, comida, "Supermercado", date(2026, 10, 8), "Tarjeta"),
        GastoRecurrente(7, "9.99", edwin, juegos, "Netflix", date(2026, 10, 5),
                        "Tarjeta", dia_cobro=5),
        GastoRecurrente(8, "25", novia, casa, "Internet", date(2026, 10, 10),
                        "Transferencia", dia_cobro=10),
        Ahorro(9, "100", edwin, fondo, "Ahorro de quincena", date(2026, 10, 15),
               "Transferencia"),
        Ahorro(10, "80", novia, fondo, "Ahorro de quincena", date(2026, 10, 15),
               "Transferencia"),
        Retiro(11, "30", novia, fondo, "Medicina", date(2026, 10, 18)),
    )
    return billetera

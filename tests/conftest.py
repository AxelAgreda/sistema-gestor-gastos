"""Objetos compartidos por las pruebas."""

from datetime import date

import pytest

from gestor_gastos.modelos import Categoria, Usuario
from gestor_gastos.notificadores import NotificadorMemoria
from gestor_gastos.persistencia.repositorio_json import RepositorioMemoria
from gestor_gastos.servicios.billetera import Billetera

FECHA = date(2026, 10, 15)


@pytest.fixture
def edwin():
    return Usuario(1, "Edwin")


@pytest.fixture
def novia():
    return Usuario(2, "Novia")


@pytest.fixture
def comida():
    return Categoria("Comida", "🍔", ["Gasto"], limite_mensual=100)


@pytest.fixture
def trabajo():
    return Categoria("Trabajo", "💼", ["Gasto", "Ingreso"])


@pytest.fixture
def fondo():
    return Categoria("Fondo de emergencia", "🏦", ["Ahorro", "Retiro"])


@pytest.fixture
def notificador():
    return NotificadorMemoria()


@pytest.fixture
def billetera(edwin, novia, comida, trabajo, fondo, notificador):
    billetera = Billetera("Prueba", RepositorioMemoria(), notificador)
    billetera.agregar_usuarios(edwin, novia)
    billetera.agregar_categorias(comida, trabajo, fondo)
    return billetera

"""Pruebas del gestor: reglas de negocio, filtros y balance."""

from datetime import date
from decimal import Decimal

import pytest
from conftest import FECHA

from gestor_gastos.excepciones import (
    AhorroInsuficienteError,
    DatoInvalidoError,
    PresupuestoExcedidoError,
    UsuarioInactivoError,
)
from gestor_gastos.modelos import Ahorro, Gasto, Ingreso, Retiro
from gestor_gastos.valores import Periodo


def test_registrar_varios_y_notificar(billetera, edwin, comida, trabajo, notificador):
    billetera.registrar(Ingreso(1, "600", edwin, trabajo, fecha=FECHA),
                        Gasto(2, "20", edwin, comida, fecha=FECHA))
    assert len(billetera) == 2
    assert len(notificador.mensajes) == 2


def test_registrar_sin_argumentos(billetera):
    with pytest.raises(TypeError):
        billetera.registrar()


def test_balance_con_la_formula_de_la_app(billetera, edwin, comida, trabajo, fondo):
    billetera.registrar(
        Ingreso(1, "600", edwin, trabajo, fecha=FECHA),
        Gasto(2, "12.50", edwin, comida, fecha=FECHA),
        Ahorro(3, "100", edwin, fondo, fecha=FECHA),
        Retiro(4, "30", edwin, fondo, fecha=FECHA),
    )
    assert billetera.balance(Periodo(2026, 10)) == Decimal("517.50")
    assert billetera.ahorro_acumulado == Decimal("70.00")


def test_ahorro_insuficiente_no_registra(billetera, edwin, fondo):
    billetera.registrar(Ahorro(1, "50", edwin, fondo, fecha=FECHA))
    with pytest.raises(AhorroInsuficienteError):
        billetera.registrar(Retiro(2, "80", edwin, fondo, fecha=FECHA))
    assert len(billetera) == 1 and billetera.ahorro_acumulado == Decimal("50.00")


def test_presupuesto_excedido(billetera, edwin, comida):
    billetera.registrar(Gasto(1, "90", edwin, comida, fecha=FECHA))
    with pytest.raises(PresupuestoExcedidoError) as info:
        billetera.registrar(Gasto(2, "15", edwin, comida, fecha=FECHA))
    assert info.value.total == Decimal("105.00")


def test_presupuesto_es_por_mes(billetera, edwin, comida):
    billetera.registrar(Gasto(1, "90", edwin, comida, fecha=date(2026, 9, 30)),
                        Gasto(2, "90", edwin, comida, fecha=date(2026, 10, 1)))
    assert len(billetera) == 2


def test_usuario_inactivo(billetera, novia, comida):
    novia.desactivar()
    with pytest.raises(UsuarioInactivoError):
        billetera.registrar(Gasto(1, "5", novia, comida, fecha=FECHA))


def test_id_duplicado(billetera, edwin, comida):
    billetera.registrar(Gasto(1, "5", edwin, comida, fecha=FECHA))
    with pytest.raises(DatoInvalidoError):
        billetera.registrar(Gasto(1, "7", edwin, comida, fecha=FECHA))


def test_filtrar_con_sobrecarga_simulada(billetera, edwin, novia, comida, trabajo):
    billetera.registrar(
        Gasto(1, "5", edwin, comida, fecha=FECHA, metodo_pago="Tarjeta"),
        Gasto(2, "7", novia, comida, fecha=FECHA),
        Ingreso(3, "100", edwin, trabajo, fecha=date(2026, 9, 15)),
    )
    assert len(billetera.filtrar()) == 3
    assert len(billetera.filtrar(Gasto)) == 2
    assert len(billetera.filtrar(Gasto, usuario="edwin")) == 1
    assert len(billetera.filtrar(periodo="2026-09")) == 1
    with pytest.raises(TypeError):
        billetera.filtrar(color="rojo")


def test_eliminar_ahorro_ya_retirado_se_revierte(billetera, edwin, fondo):
    billetera.registrar(Ahorro(1, "50", edwin, fondo, fecha=FECHA),
                        Retiro(2, "50", edwin, fondo, fecha=FECHA))
    with pytest.raises(AhorroInsuficienteError):
        billetera.eliminar(1)
    assert len(billetera) == 2  # el borrado se deshizo


def test_categorias_para_tipo(billetera):
    nombres = {c.nombre for c in billetera.categorias_para("Ahorro")}
    assert nombres == {"Fondo de emergencia"}

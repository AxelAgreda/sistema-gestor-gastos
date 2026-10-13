"""Pruebas de las entidades: pilares, identidad, igualdad y validaciones."""

from datetime import date
from decimal import Decimal

import pytest
from conftest import FECHA

from gestor_gastos.excepciones import (
    CategoriaNoPermitidaError,
    DatoInvalidoError,
    GestorGastosError,
    MontoInvalidoError,
)
from gestor_gastos.modelos import Ahorro, Gasto, GastoRecurrente, Ingreso, Movimiento, Retiro
from gestor_gastos.valores import Periodo, a_monto


def test_movimiento_es_abstracto(edwin, comida):
    with pytest.raises(TypeError):
        Movimiento(1, "10", edwin, comida)


@pytest.mark.parametrize("clase, esperado", [
    (Gasto, Decimal("-10.00")), (Ingreso, Decimal("10.00")),
    (Ahorro, Decimal("-10.00")), (Retiro, Decimal("10.00")),
])
def test_polimorfismo_efecto_en_balance(clase, esperado, edwin):
    from gestor_gastos.modelos import Categoria
    todas = Categoria("Varios", tipos=["Gasto", "Ingreso", "Ahorro", "Retiro"])
    assert clase(1, "10", edwin, todas, fecha=FECHA).efecto_en_balance() == esperado


def test_igualdad_por_id_e_identidad_distinta(edwin, comida):
    uno = Gasto(7, "5", edwin, comida, "Café", FECHA)
    otro = Gasto(7, "5", edwin, comida, "Café", FECHA)
    assert uno == otro
    assert uno is not otro
    assert len({uno, otro}) == 1  # __hash__ coherente con __eq__


def test_montos_exactos_con_decimal():
    total = sum((a_monto(0.10) for _ in range(10)), Decimal("0"))
    assert total == Decimal("1.00")


@pytest.mark.parametrize("valor", ["-5", "0", "4.999", "abc", True])
def test_montos_invalidos(valor):
    with pytest.raises(MontoInvalidoError):
        a_monto(valor)


def test_categoria_no_permitida(edwin, fondo):
    with pytest.raises(CategoriaNoPermitidaError) as info:
        Gasto(1, "8", edwin, fondo, "Café")
    assert isinstance(info.value, GestorGastosError)


def test_metodo_de_pago_invalido(edwin, comida):
    with pytest.raises(DatoInvalidoError):
        Gasto(1, "8", edwin, comida, metodo_pago="Bitcoin")


def test_ingreso_usa_super_y_extiende_resumen(edwin, trabajo):
    quincena = Ingreso(1, "600", edwin, trabajo, "Quincena", FECHA, periodo_pago="1-15 oct")
    assert quincena.metodo_pago == "Transferencia"  # valor por defecto propio
    assert quincena.resumen().endswith("(1-15 oct)")


def test_herencia_multiple_y_mro(edwin, comida):
    netflix = GastoRecurrente(1, "9.99", edwin, comida, "Netflix", FECHA, "Tarjeta",
                              dia_cobro=5)
    nombres = [c.__name__ for c in GastoRecurrente.__mro__]
    assert nombres.index("RecurrenteMixin") < nombres.index("Gasto")
    assert netflix.efecto_en_balance() == Decimal("-9.99")  # heredado de Gasto
    assert netflix.proxima_fecha(date(2026, 10, 20)) == date(2026, 11, 5)
    assert "[cada mes, día 5]" in netflix.resumen()


def test_dia_de_cobro_fuera_de_rango(edwin, comida):
    with pytest.raises(DatoInvalidoError):
        GastoRecurrente(1, "9.99", edwin, comida, dia_cobro=31)


def test_periodo_dataclass_inmutable():
    periodo = Periodo.desde_texto("2026-10")
    assert str(periodo) == "2026-10" and periodo.contiene(FECHA)
    with pytest.raises(AttributeError):
        periodo.mes = 11
    with pytest.raises(DatoInvalidoError):
        Periodo(2026, 13)


def test_serializacion_ida_y_vuelta(edwin, comida):
    netflix = GastoRecurrente(1, "9.99", edwin, comida, "Netflix", FECHA, "Tarjeta",
                              dia_cobro=5)
    datos = netflix.a_dict()
    copia = Movimiento.desde_dict(datos, lambda _id: edwin, lambda _nombre: comida)
    assert type(copia) is GastoRecurrente
    assert copia == netflix and copia.dia_cobro == 5 and copia.monto == Decimal("9.99")

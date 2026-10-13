"""Pruebas de archivos: JSON, CSV y errores de lectura."""

import csv
from decimal import Decimal

import pytest
from conftest import FECHA

from gestor_gastos.excepciones import PersistenciaError
from gestor_gastos.modelos import Ahorro, Gasto, GastoRecurrente, Ingreso
from gestor_gastos.notificadores import NotificadorArchivo, NotificadorMemoria
from gestor_gastos.persistencia.exportador_csv import exportar_csv
from gestor_gastos.persistencia.repositorio_json import RepositorioJSON
from gestor_gastos.servicios.billetera import Billetera


def llenar(billetera, edwin, comida, trabajo, fondo):
    billetera.registrar(
        Ingreso(1, "600", edwin, trabajo, fecha=FECHA, periodo_pago="1-15 oct"),
        GastoRecurrente(2, "9.99", edwin, comida, "Netflix", FECHA, dia_cobro=5),
        Ahorro(3, "100", edwin, fondo, fecha=FECHA),
        Gasto(4, "20", edwin, comida, fecha=FECHA),
    )


def test_guardar_y_cargar_json(tmp_path, edwin, novia, comida, trabajo, fondo):
    repositorio = RepositorioJSON(tmp_path / "datos.json")
    original = Billetera("Casa", repositorio, NotificadorMemoria())
    original.agregar_usuarios(edwin, novia)
    original.agregar_categorias(comida, trabajo, fondo)
    llenar(original, edwin, comida, trabajo, fondo)
    original.guardar()

    copia = Billetera("Casa", repositorio, NotificadorMemoria())
    assert copia.cargar() == 4
    assert copia.balance() == original.balance()
    assert copia.ahorro_acumulado == Decimal("100.00")
    assert [type(m) for m in copia.movimientos] == [type(m) for m in original.movimientos]
    assert copia.movimientos[0] == original.movimientos[0]
    assert copia.movimientos[0] is not original.movimientos[0]


def test_archivo_inexistente_devuelve_vacio(tmp_path):
    assert RepositorioJSON(tmp_path / "no_existe.json").cargar() == {}


def test_archivo_danado(tmp_path):
    ruta = tmp_path / "datos.json"
    ruta.write_text("{ esto no es json", encoding="utf-8")
    with pytest.raises(PersistenciaError):
        RepositorioJSON(ruta).cargar()


def test_guardado_atomico_no_deja_temporales(tmp_path):
    repositorio = RepositorioJSON(tmp_path / "datos.json")
    repositorio.guardar({"a": 1})
    with pytest.raises(PersistenciaError):
        repositorio.guardar({"no_serializable": object()})
    assert repositorio.cargar() == {"a": 1}  # el archivo anterior sigue intacto
    assert not list(tmp_path.glob("*.tmp"))


def test_exportar_csv(tmp_path, billetera, edwin, comida, trabajo, fondo):
    llenar(billetera, edwin, comida, trabajo, fondo)
    ruta = tmp_path / "salida.csv"
    assert exportar_csv(billetera.movimientos, ruta) == 4
    with ruta.open(encoding="utf-8-sig") as archivo:
        filas = list(csv.DictReader(archivo))
    assert filas[1]["Tipo"] == "Gasto" and filas[1]["Monto"] == "9.99"


def test_notificador_archivo(tmp_path):
    notificador = NotificadorArchivo(tmp_path / "avisos.log")
    notificador.enviar("Edwin", "hola")
    assert "Edwin | hola" in (tmp_path / "avisos.log").read_text(encoding="utf-8")

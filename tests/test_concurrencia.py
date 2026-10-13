"""Pruebas de los hilos: reportes, respaldo y registro concurrente."""

import threading
import time
from decimal import Decimal

from conftest import FECHA

from gestor_gastos.modelos import Gasto, Ingreso
from gestor_gastos.servicios.reportes import GeneradorReportes
from gestor_gastos.servicios.respaldo import RespaldoAutomatico
from gestor_gastos.valores import Periodo


def test_reportes_en_varios_hilos(tmp_path, billetera, edwin, novia, comida, trabajo):
    billetera.registrar(Ingreso(1, "600", edwin, trabajo, fecha=FECHA),
                        Gasto(2, "10", novia, comida, fecha=FECHA))
    resultados = GeneradorReportes(billetera, tmp_path).generar(Periodo(2026, 10))
    assert {usuario for usuario, _, _ in resultados} == {"Edwin", "Novia"}
    assert all(archivo.exists() for _, archivo, _ in resultados)
    assert all(hilo.startswith("reporte") for _, _, hilo in resultados)


def test_respaldo_automatico(tmp_path, billetera, edwin, trabajo):
    billetera.registrar(Ingreso(1, "600", edwin, trabajo, fecha=FECHA))
    with RespaldoAutomatico(billetera, tmp_path, intervalo=0.05, maximo=3) as respaldo:
        time.sleep(0.3)
    assert not respaldo.is_alive()
    assert len(respaldo.respaldos) >= 2
    assert len(list(tmp_path.glob("respaldo_*.json"))) <= 3  # se limpian los viejos


def test_registro_desde_varios_hilos(billetera, edwin, trabajo):
    def registrar_lote(inicio):
        for numero in range(inicio, inicio + 50):
            billetera.registrar(Ingreso(numero, "1", edwin, trabajo, fecha=FECHA))

    hilos = [threading.Thread(target=registrar_lote, args=(i * 100,)) for i in range(4)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()
    assert len(billetera) == 200
    assert billetera.balance() == Decimal("200.00")

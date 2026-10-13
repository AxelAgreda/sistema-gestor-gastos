"""Punto de entrada del sistema.

    python main.py           abre el menú (los datos se guardan en datos/)
    python main.py --demo    ejecuta la demostración guiada de todos los requisitos
"""

from __future__ import annotations

import argparse
from pathlib import Path

from gestor_gastos.consola.menu import MenuConsola
from gestor_gastos.datos_demo import crear_billetera_demo
from gestor_gastos.demo import ejecutar_demo
from gestor_gastos.excepciones import PersistenciaError
from gestor_gastos.notificadores import NotificadorConsola
from gestor_gastos.persistencia.repositorio_json import RepositorioJSON
from gestor_gastos.servicios.billetera import Billetera
from gestor_gastos.servicios.respaldo import RespaldoAutomatico


def main() -> None:
    parser = argparse.ArgumentParser(description="Gestor de gastos compartidos")
    parser.add_argument("--demo", action="store_true", help="ejecuta la demostración")
    parser.add_argument("--datos", default="datos", help="carpeta de datos")
    argumentos = parser.parse_args()

    if argumentos.demo:
        ejecutar_demo()
        return

    carpeta = Path(argumentos.datos)
    repositorio = RepositorioJSON(carpeta / "gestor.json")
    notificador = NotificadorConsola()
    billetera = Billetera("Gastos de la casa", repositorio, notificador)
    try:
        if billetera.cargar() == 0:
            print("No hay datos guardados: se cargan los datos de ejemplo.")
            billetera = crear_billetera_demo(repositorio, notificador)
    except PersistenciaError as error:
        print(f"⚠ {error}. Se empieza con los datos de ejemplo.")
        billetera = crear_billetera_demo(repositorio, notificador)

    with RespaldoAutomatico(billetera, carpeta / "respaldos", intervalo=120):
        try:
            MenuConsola(billetera, carpeta / "salidas").ejecutar()
        finally:
            billetera.guardar()  # se guarda aunque el menú termine con un error
            print("Datos guardados en", repositorio.ruta)


if __name__ == "__main__":
    main()

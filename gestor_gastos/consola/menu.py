"""Menú de texto del sistema."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path

from gestor_gastos.excepciones import DatoInvalidoError, GestorGastosError
from gestor_gastos.modelos import (
    METODOS_PAGO,
    Ahorro,
    Gasto,
    GastoRecurrente,
    Ingreso,
    Retiro,
)
from gestor_gastos.persistencia.exportador_csv import exportar_csv
from gestor_gastos.servicios.billetera import Billetera
from gestor_gastos.servicios.reportes import GeneradorReportes
from gestor_gastos.valores import Periodo

TIPOS = {"1": Gasto, "2": Ingreso, "3": Ahorro, "4": Retiro, "5": GastoRecurrente}
OPCIONES = """
========== GESTOR DE GASTOS ==========
 1. Registrar movimiento
 2. Ver movimientos del mes
 3. Resumen del mes
 4. Ver ahorro acumulado
 5. Eliminar movimiento
 6. Exportar movimientos a CSV
 7. Generar reportes por usuario (hilos)
 8. Guardar
 0. Salir
======================================"""


class MenuConsola:
    """Interfaz de texto. Recibe la función de entrada para poder probarla."""

    def __init__(self, billetera: Billetera, carpeta_salida: str | Path = "salidas",
                 entrada: Callable[[str], str] = input) -> None:
        self.billetera = billetera
        self.carpeta = Path(carpeta_salida)
        self.entrada = entrada
        self.periodo = Periodo.de_fecha(date.today())
        self.acciones = {
            "1": self.registrar, "2": self.listar, "3": self.resumen,
            "4": self.ahorro, "5": self.eliminar, "6": self.exportar,
            "7": self.reportes, "8": self.guardar,
        }

    def ejecutar(self) -> None:
        while True:
            print(OPCIONES)
            opcion = self.entrada("Elige una opción: ").strip()
            if opcion == "0":
                print("Hasta luego.")
                return
            accion = self.acciones.get(opcion)
            if accion is None:
                print("Opción no válida.")
                continue
            try:
                accion()
            except GestorGastosError as error:  # errores esperados: se informan
                print(f"⚠ {type(error).__name__}: {error}")
            except ValueError:
                print("⚠ Escribe un número válido.")

    # ------------------------------------------------------------- ayudantes
    def _elegir(self, titulo: str, opciones: list[str]) -> int:
        for numero, texto in enumerate(opciones, start=1):
            print(f"  {numero}. {texto}")
        indice = int(self.entrada(f"{titulo}: ")) - 1
        if not 0 <= indice < len(opciones):
            raise DatoInvalidoError("Opción fuera de la lista")
        return indice

    def _pedir_periodo(self) -> Periodo:
        texto = self.entrada(f"Mes AAAA-MM [{self.periodo}]: ").strip()
        return Periodo.desde_texto(texto) if texto else self.periodo

    # --------------------------------------------------------------- acciones
    def registrar(self) -> None:
        print("Tipo: 1. Gasto  2. Ingreso  3. Ahorro  4. Retiro  5. Gasto recurrente")
        clase = TIPOS.get(self.entrada("Tipo: ").strip())
        if clase is None:
            raise DatoInvalidoError("Tipo de movimiento no válido")
        usuarios = [u for u in self.billetera.usuarios if u.activo]
        usuario = usuarios[self._elegir("Usuario", [u.nombre for u in usuarios])]
        categorias = self.billetera.categorias_para(clase.TIPO)
        categoria = categorias[self._elegir(
            "Categoría", [f"{c.emoji} {c.nombre}" for c in categorias])]
        monto = self.entrada("Monto: $")
        descripcion = self.entrada("Descripción: ")
        metodo = METODOS_PAGO[self._elegir("Método de pago", list(METODOS_PAGO))]
        texto_fecha = self.entrada("Fecha AAAA-MM-DD (Enter = hoy): ").strip()
        fecha = date.fromisoformat(texto_fecha) if texto_fecha else date.today()
        extras: dict[str, object] = {}
        if clase is Ingreso:
            extras["periodo_pago"] = self.entrada("Periodo que cubre (ej. 1-15 oct): ")
        if clase is GastoRecurrente:
            extras["dia_cobro"] = int(self.entrada("Día de cobro (1-28): "))
        movimiento = clase(self.billetera.siguiente_id(), monto, usuario, categoria,
                           descripcion, fecha, metodo, **extras)
        self.billetera.registrar(movimiento)
        print("✓ Guardado:", movimiento.resumen())

    def listar(self) -> None:
        periodo = self._pedir_periodo()
        movimientos = sorted(self.billetera.filtrar(periodo=periodo), key=lambda m: m.fecha)
        print(f"\nMovimientos de {periodo} ({len(movimientos)}):")
        for mov in movimientos:
            print(f"  #{mov.id:<3} {mov.resumen()}")

    def resumen(self) -> None:
        periodo = self._pedir_periodo()
        totales = self.billetera.totales_por_tipo(periodo)
        print(f"\nResumen de {periodo}")
        for tipo, total in totales.items():
            print(f"  {tipo:<8} ${total:>10,.2f}")
        print(f"  {'Balance':<8} ${self.billetera.balance(periodo):>10,.2f}")
        print("  Gastos por categoría:")
        for categoria, total in self.billetera.gastos_por_categoria(periodo).items():
            print(f"    {categoria:<24} ${total:>9,.2f}")

    def ahorro(self) -> None:
        print(f"Ahorro acumulado: ${self.billetera.ahorro_acumulado:,.2f}")

    def eliminar(self) -> None:
        movimiento = self.billetera.eliminar(int(self.entrada("ID del movimiento: ")))
        print("✓ Eliminado:", movimiento.resumen())

    def exportar(self) -> None:
        ruta = self.carpeta / "movimientos.csv"
        filas = exportar_csv(self.billetera.movimientos, ruta)
        print(f"✓ {filas} movimientos exportados a {ruta}")

    def reportes(self) -> None:
        generador = GeneradorReportes(self.billetera, self.carpeta / "reportes")
        for usuario, archivo, hilo in generador.generar(self._pedir_periodo()):
            print(f"✓ {usuario}: {archivo} (hilo {hilo})")

    def guardar(self) -> None:
        self.billetera.guardar()
        print("✓ Datos guardados.")


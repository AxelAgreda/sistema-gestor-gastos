"""Demostración guiada: muestra cada requisito del examen funcionando."""

from __future__ import annotations

import time
from datetime import date
from pathlib import Path

from gestor_gastos.datos_demo import crear_billetera_demo
from gestor_gastos.excepciones import (
    GestorGastosError,
    MontoInvalidoError,
    PersistenciaError,
)
from gestor_gastos.interfaces import Notificador, Repositorio
from gestor_gastos.modelos import Ahorro, Gasto, GastoRecurrente, Movimiento, Retiro
from gestor_gastos.notificadores import NotificadorArchivo, NotificadorConsola
from gestor_gastos.persistencia.exportador_csv import exportar_csv
from gestor_gastos.persistencia.repositorio_json import RepositorioJSON
from gestor_gastos.servicios.billetera import Billetera
from gestor_gastos.servicios.reportes import GeneradorReportes
from gestor_gastos.servicios.respaldo import RespaldoAutomatico
from gestor_gastos.valores import Periodo

OCTUBRE = Periodo(2026, 10)


def titulo(texto: str) -> None:
    print(f"\n=== {texto} ===")


def ejecutar_demo(carpeta: str | Path = "salidas_demo") -> None:
    carpeta = Path(carpeta)
    repositorio = RepositorioJSON(carpeta / "gestor.json")
    billetera = crear_billetera_demo(repositorio, NotificadorArchivo(carpeta / "avisos.log"))
    edwin, novia = billetera.usuarios
    comida, fondo = billetera.categoria("Comida"), billetera.categoria("Fondo de emergencia")

    titulo("1. Objetos creados")
    objetos = [*billetera.usuarios, *billetera.categorias, *billetera.movimientos]
    conteo: dict[str, int] = {}
    for objeto in objetos:
        conteo[type(objeto).__name__] = conteo.get(type(objeto).__name__, 0) + 1
    print(f"{len(objetos)} objetos:", ", ".join(f"{n} {c}" for c, n in conteo.items()))

    titulo("2. Polimorfismo: el mismo resumen() en cinco clases distintas")
    for movimiento in sorted(billetera.movimientos, key=lambda m: m.fecha):
        print(" ", movimiento.resumen())

    titulo("3. Clase abstracta y herencia múltiple")
    try:
        Movimiento(99, "10", edwin, comida)  # type: ignore[abstract]
    except TypeError as error:
        print("Movimiento(...) ->", error)
    print("MRO de GastoRecurrente:", " -> ".join(c.__name__ for c in GastoRecurrente.__mro__))
    netflix = billetera.filtrar(GastoRecurrente, usuario="Edwin")[0]
    print("Próximo cobro de Netflix desde el 20/10/2026:",
          netflix.proxima_fecha(date(2026, 10, 20)).strftime("%d/%m/%Y"))

    titulo("4. Reglas de negocio con excepciones propias")
    intentos = {
        "Retirar $500 del ahorro": lambda: billetera.registrar(
            Retiro(20, "500", edwin, fondo, "Viaje", date(2026, 10, 20))),
        "Gastar $60 más en Comida": lambda: billetera.registrar(
            Gasto(21, "60", edwin, comida, "Cena", date(2026, 10, 20))),
        "Gasto en Fondo de emergencia": lambda: Gasto(22, "8", edwin, fondo, "Café"),
        "Monto con tres decimales": lambda: Gasto(23, "4.999", edwin, comida),
    }
    for descripcion, intento in intentos.items():
        try:
            intento()
        except GestorGastosError as error:  # una sola cláusula atrapa toda la jerarquía
            print(f"  {descripcion:<30} -> {type(error).__name__}: {error}")
    novia.desactivar()
    try:
        billetera.registrar(Gasto(24, "5", novia, comida, "Café", date(2026, 10, 21)))
    except GestorGastosError as error:
        print(f"  {'Usuario desactivado registra':<30} -> {type(error).__name__}: {error}")
    print("¿MontoInvalidoError es un GestorGastosError?",
          issubclass(MontoInvalidoError, GestorGastosError))
    print(f"Movimientos después de los intentos: {len(billetera)} (ninguno se agregó)")

    titulo("5. Interfaces: dos notificadores sin relación de herencia")
    for notificador in (NotificadorConsola(), NotificadorArchivo(carpeta / "avisos.log")):
        print(f"  {type(notificador).__name__:<20} cumple Notificador:",
              isinstance(notificador, Notificador))
    print("  RepositorioJSON cumple Repositorio:", isinstance(repositorio, Repositorio))
    prueba = Billetera("Prueba", repositorio, NotificadorConsola())
    prueba.agregar_usuarios(edwin)
    prueba.agregar_categorias(fondo)
    prueba.registrar(Ahorro(1, "20", edwin, fondo, "Prueba de aviso"))

    titulo("6. Persistencia en archivos")
    billetera.guardar()
    print("Guardado en", repositorio.ruta)
    copia = Billetera("Copia", repositorio, NotificadorArchivo(carpeta / "avisos.log"))
    print("Movimientos leídos del archivo:", copia.cargar())
    original, leido = billetera.movimientos[0], copia.movimientos[0]
    print("Identidad e igualdad: original == leido ->", original == leido,
          "| original is leido ->", original is leido)
    print(f"Balance original ${billetera.balance(OCTUBRE):,.2f} | "
          f"balance leído ${copia.balance(OCTUBRE):,.2f}")
    dañado = carpeta / "dañado.json"
    dañado.write_text('{"usuarios": [', encoding="utf-8")
    try:
        RepositorioJSON(dañado).cargar()
    except PersistenciaError as error:
        print("Archivo dañado ->", error)
    else:
        print("El archivo se leyó sin problemas")
    finally:
        dañado.unlink()
        print("Archivo de prueba eliminado (bloque finally)")
    filas = exportar_csv(billetera.movimientos, carpeta / "movimientos.csv")
    print(f"CSV exportado: {filas} filas en {carpeta / 'movimientos.csv'}")

    titulo("7. Concurrencia")
    for usuario, archivo, hilo in GeneradorReportes(billetera, carpeta / "reportes").generar(
            OCTUBRE):
        print(f"  Reporte de {usuario:<6} -> {archivo.name} (generado en {hilo})")
    with RespaldoAutomatico(billetera, carpeta / "respaldos", intervalo=0.2) as respaldo:
        novia.reactivar()  # se reactiva para seguir la demostración
        for numero, monto in enumerate(("4.50", "7.25", "2.00"), start=30):
            billetera.registrar(Gasto(numero, monto, novia, billetera.categoria("Transporte"),
                                      "Uber", date(2026, 10, 22)))
            time.sleep(0.25)  # el hilo de respaldo trabaja mientras tanto
    print(f"  Respaldos hechos por el hilo '{respaldo.name}': {len(respaldo.respaldos)}")

    titulo("8. Resumen de octubre de 2026")
    for tipo, total in billetera.totales_por_tipo(OCTUBRE).items():
        print(f"  {tipo:<8} ${total:>9,.2f}")
    print(f"  {'Balance':<8} ${billetera.balance(OCTUBRE):>9,.2f}")
    print(f"  Ahorro acumulado: ${billetera.ahorro_acumulado:,.2f}")

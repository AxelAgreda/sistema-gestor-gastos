"""Exportación de movimientos a CSV para abrirlos en Excel o Google Sheets."""

from __future__ import annotations

import csv
from collections.abc import Iterable
from pathlib import Path

from gestor_gastos.excepciones import PersistenciaError
from gestor_gastos.modelos.movimientos import Movimiento

COLUMNAS = ["ID", "Fecha", "Tipo", "Usuario", "Categoría", "Descripción",
            "Método de pago", "Monto", "Efecto en balance"]


def exportar_csv(movimientos: Iterable[Movimiento], ruta: str | Path) -> int:
    """Escribe los movimientos en un CSV y devuelve cuántas filas escribió."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    filas = 0
    try:
        with ruta.open("w", newline="", encoding="utf-8-sig") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow(COLUMNAS)
            for mov in movimientos:
                escritor.writerow([mov.id, mov.fecha.isoformat(), mov.TIPO, mov.usuario.nombre,
                                   mov.categoria.nombre, mov.descripcion, mov.metodo_pago,
                                   mov.monto, mov.efecto_en_balance()])
                filas += 1
    except OSError as error:
        raise PersistenciaError(f"No se pudo exportar a {ruta}: {error}") from error
    return filas

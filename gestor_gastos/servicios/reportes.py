"""Generación de reportes mensuales por usuario usando varios hilos."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

from gestor_gastos.servicios.billetera import Billetera
from gestor_gastos.valores import Periodo


class GeneradorReportes:
    """Escribe un reporte de texto por usuario. Cada reporte va en su propio hilo.

    Escribir archivos es una operación de entrada y salida: mientras un hilo
    espera al disco, otro puede avanzar. Con muchos usuarios esto acorta el tiempo
    total sin bloquear el menú.
    """

    def __init__(self, billetera: Billetera, carpeta: str | Path, hilos: int = 4) -> None:
        self.billetera = billetera
        self.carpeta = Path(carpeta)
        self.hilos = hilos

    def generar(self, periodo: Periodo) -> list[tuple[str, Path, str]]:
        """Devuelve (usuario, archivo, hilo que lo generó) por cada reporte."""
        self.carpeta.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=self.hilos,
                                thread_name_prefix="reporte") as ejecutor:
            futuros = [ejecutor.submit(self._reporte_usuario, usuario.nombre, periodo)
                       for usuario in self.billetera.usuarios]
            return [futuro.result() for futuro in futuros]

    def _reporte_usuario(self, nombre: str, periodo: Periodo) -> tuple[str, Path, str]:
        movimientos = self.billetera.filtrar(periodo=periodo, usuario=nombre)
        totales: dict[str, Decimal] = {}
        for mov in movimientos:
            totales[mov.TIPO] = totales.get(mov.TIPO, Decimal("0.00")) + mov.monto
        lineas = [f"Reporte de {nombre} - {periodo}", "=" * 40]
        lineas += [mov.resumen() for mov in movimientos] or ["Sin movimientos"]
        lineas += ["-" * 40] + [f"{tipo:<8} ${total:>10,.2f}" for tipo, total in totales.items()]
        archivo = self.carpeta / f"reporte_{nombre.lower()}_{periodo}.txt"
        archivo.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        return nombre, archivo, threading.current_thread().name

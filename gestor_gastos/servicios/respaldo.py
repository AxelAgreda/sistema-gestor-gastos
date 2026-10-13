"""Respaldo automático en segundo plano con un hilo propio."""

from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path

from gestor_gastos.servicios.billetera import Billetera


class RespaldoAutomatico(threading.Thread):
    """Hilo que copia los datos de la billetera cada cierto tiempo.

    Hereda de threading.Thread y sobrescribe run(). Se usa como gestor de
    contexto: al entrar arranca y al salir se detiene y hace un último respaldo,
    incluso si hubo un error en el bloque with.
    """

    def __init__(self, billetera: Billetera, carpeta: str | Path,
                 intervalo: float = 120.0, maximo: int = 5) -> None:
        super().__init__(name="respaldo-automatico", daemon=True)
        self.billetera = billetera
        self.carpeta = Path(carpeta)
        self.intervalo = intervalo
        self.maximo = maximo
        self.respaldos: list[Path] = []
        self._detener = threading.Event()

    def run(self) -> None:
        # wait() devuelve True cuando alguien pide detener; si no, respalda
        while not self._detener.wait(self.intervalo):
            self.respaldar()

    def respaldar(self) -> Path:
        self.carpeta.mkdir(parents=True, exist_ok=True)
        archivo = self.carpeta / f"respaldo_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
        datos = self.billetera.a_dict()  # a_dict() usa el candado de la billetera
        archivo.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        self.respaldos.append(archivo)
        self._limpiar_antiguos()
        return archivo

    def _limpiar_antiguos(self) -> None:
        archivos = sorted(self.carpeta.glob("respaldo_*.json"))
        for viejo in archivos[:-self.maximo]:
            viejo.unlink(missing_ok=True)

    def detener(self) -> None:
        self._detener.set()
        if self.is_alive():
            self.join()

    def __enter__(self) -> RespaldoAutomatico:
        self.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.detener()
        self.respaldar()  # último respaldo al cerrar

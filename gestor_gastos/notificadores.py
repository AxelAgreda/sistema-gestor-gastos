"""Clases que cumplen la interfaz Notificador sin heredar de ella ni entre sí."""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path


class NotificadorConsola:
    """Muestra el aviso en pantalla, como el mensaje de éxito de la app."""

    def __init__(self, prefijo: str = "🔔") -> None:
        self.prefijo = prefijo

    def enviar(self, destinatario: str, mensaje: str) -> None:
        print(f"{self.prefijo} {destinatario}: {mensaje}")


class NotificadorArchivo:
    """Guarda cada aviso en un archivo de bitácora. Es seguro entre hilos."""

    def __init__(self, ruta: str | Path) -> None:
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        self._candado = threading.Lock()

    def enviar(self, destinatario: str, mensaje: str) -> None:
        linea = f"{datetime.now():%Y-%m-%d %H:%M:%S} | {destinatario} | {mensaje}\n"
        with self._candado, self.ruta.open("a", encoding="utf-8") as archivo:
            archivo.write(linea)


class NotificadorMemoria:
    """Guarda los avisos en una lista. Útil en las pruebas."""

    def __init__(self) -> None:
        self.mensajes: list[tuple[str, str]] = []

    def enviar(self, destinatario: str, mensaje: str) -> None:
        self.mensajes.append((destinatario, mensaje))

"""Persistencia en archivos JSON (implementa la interfaz Repositorio)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from gestor_gastos.excepciones import PersistenciaError


class RepositorioJSON:
    """Guarda todos los datos del gestor en un archivo JSON."""

    def __init__(self, ruta: str | Path) -> None:
        self.ruta = Path(ruta)

    def guardar(self, datos: dict) -> None:
        """Escritura atómica: primero a un archivo temporal y luego se reemplaza.

        Si algo falla a mitad de la escritura, el archivo anterior queda intacto.
        """
        temporal = self.ruta.with_suffix(".tmp")
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        try:
            with temporal.open("w", encoding="utf-8") as archivo:
                json.dump(datos, archivo, ensure_ascii=False, indent=2)
        except (OSError, TypeError) as error:
            raise PersistenciaError(f"No se pudo guardar en {self.ruta}: {error}") from error
        else:
            os.replace(temporal, self.ruta)  # solo si la escritura terminó bien
        finally:
            if temporal.exists():  # limpieza aunque haya habido error
                temporal.unlink()

    def cargar(self) -> dict:
        if not self.ruta.exists():
            return {}
        try:
            with self.ruta.open(encoding="utf-8") as archivo:
                return json.load(archivo)
        except json.JSONDecodeError as error:
            raise PersistenciaError(
                f"El archivo {self.ruta} está dañado (línea {error.lineno})") from error
        except OSError as error:
            raise PersistenciaError(f"No se pudo leer {self.ruta}: {error}") from error


class RepositorioMemoria:
    """Repositorio que no toca el disco. Cumple la misma interfaz; útil en pruebas."""

    def __init__(self) -> None:
        self._datos: dict = {}

    def guardar(self, datos: dict) -> None:
        self._datos = json.loads(json.dumps(datos))  # copia profunda, como el archivo

    def cargar(self) -> dict:
        return json.loads(json.dumps(self._datos))

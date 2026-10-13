"""Interfaces del sistema (tipo 4), definidas con typing.Protocol.

Las clases que las cumplen no heredan de ellas ni entre sí: basta con que
tengan los métodos. El gestor (Billetera) las recibe por el constructor, así
depende de la abstracción y no de una clase concreta (principio de inversión
de dependencias, la D de SOLID).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Notificador(Protocol):
    """Avisa a un usuario de algo que pasó en el gestor."""

    def enviar(self, destinatario: str, mensaje: str) -> None: ...


@runtime_checkable
class Repositorio(Protocol):
    """Guarda y recupera todos los datos del gestor."""

    def guardar(self, datos: dict) -> None: ...

    def cargar(self) -> dict: ...

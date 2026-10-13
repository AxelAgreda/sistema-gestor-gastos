"""Personas que comparten el gestor (en la app real: la hoja Usuarios)."""

from __future__ import annotations

from gestor_gastos.excepciones import DatoInvalidoError


class Usuario:
    """Usuario del gestor. El borrado es suave: se desactiva, no se elimina."""

    def __init__(self, id_usuario: int, nombre: str, activo: bool = True) -> None:
        nombre_limpio = " ".join(str(nombre).split())
        if not nombre_limpio:
            raise DatoInvalidoError("El usuario necesita un nombre")
        self.__id = id_usuario
        self.nombre = nombre_limpio
        self._activo = activo

    @property
    def id(self) -> int:
        return self.__id

    @property
    def activo(self) -> bool:
        return self._activo

    def desactivar(self) -> None:
        """Conserva el historial del usuario, pero ya no puede registrar."""
        self._activo = False

    def reactivar(self) -> None:
        self._activo = True

    # Igualdad por identificador de negocio, no por identidad en memoria
    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, Usuario):
            return NotImplemented
        return self.__id == otro.__id

    def __hash__(self) -> int:
        return hash(self.__id)

    def __repr__(self) -> str:
        return f"Usuario({self.__id}, {self.nombre!r})"

    def a_dict(self) -> dict:
        return {"id": self.__id, "nombre": self.nombre, "activo": self._activo}

    @classmethod
    def desde_dict(cls, datos: dict) -> Usuario:
        return cls(int(datos["id"]), datos["nombre"], bool(datos.get("activo", True)))

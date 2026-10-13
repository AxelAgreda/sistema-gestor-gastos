"""Categorías de movimiento (en la app real: la hoja Categorias)."""

from __future__ import annotations

from decimal import Decimal

from gestor_gastos.excepciones import DatoInvalidoError
from gestor_gastos.valores import a_monto

TIPOS_MOVIMIENTO = ("Gasto", "Ingreso", "Ahorro", "Retiro")


class Categoria:
    """Categoría con emoji, los tipos en los que aparece y un límite opcional."""

    def __init__(
        self,
        nombre: str,
        emoji: str = "💰",
        tipos: tuple[str, ...] | list[str] = TIPOS_MOVIMIENTO,
        limite_mensual: object | None = None,
    ) -> None:
        nombre_limpio = " ".join(str(nombre).split()).capitalize()
        if not nombre_limpio:
            raise DatoInvalidoError("La categoría necesita un nombre")
        tipos_validos = frozenset(tipo for tipo in tipos if tipo in TIPOS_MOVIMIENTO)
        if not tipos_validos:
            raise DatoInvalidoError("La categoría debe aplicar al menos a un tipo")
        self.nombre = nombre_limpio
        self.emoji = emoji
        self.tipos = tipos_validos
        self.limite_mensual: Decimal | None = (
            None if limite_mensual is None else a_monto(limite_mensual)
        )

    def permite(self, tipo: str) -> bool:
        return tipo in self.tipos

    def __eq__(self, otra: object) -> bool:
        if not isinstance(otra, Categoria):
            return NotImplemented
        return self.nombre == otra.nombre

    def __hash__(self) -> int:
        return hash(self.nombre)

    def __repr__(self) -> str:
        return f"Categoria({self.emoji} {self.nombre!r})"

    def a_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "emoji": self.emoji,
            "tipos": sorted(self.tipos),
            "limite_mensual": None if self.limite_mensual is None else str(self.limite_mensual),
        }

    @classmethod
    def desde_dict(cls, datos: dict) -> Categoria:
        return cls(datos["nombre"], datos.get("emoji", "💰"), datos["tipos"],
                   datos.get("limite_mensual"))

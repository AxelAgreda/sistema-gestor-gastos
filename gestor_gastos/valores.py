"""Objetos de valor (tipo 6, recomendado): dataclasses inmutables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from gestor_gastos.excepciones import DatoInvalidoError, MontoInvalidoError

CENTAVO = Decimal("0.01")


def a_monto(valor: object) -> Decimal:
    """Convierte int, float, str o Decimal a un monto exacto de dos decimales.

    Los float pasan por str() para que 0.1 se guarde como 0.10 y no como
    0.1000000000000000055...
    """
    if isinstance(valor, bool):
        raise MontoInvalidoError(valor)
    try:
        monto = Decimal(str(valor).replace("$", "").replace(",", "").strip())
    except InvalidOperation:
        raise MontoInvalidoError(valor) from None
    if not monto.is_finite() or monto <= 0 or monto != monto.quantize(CENTAVO):
        raise MontoInvalidoError(valor)
    return monto.quantize(CENTAVO)


@dataclass(frozen=True, order=True)
class Periodo:
    """Un mes concreto, como "2026-10". Sirve para filtrar y para el presupuesto."""

    anio: int
    mes: int

    def __post_init__(self) -> None:
        if not 1 <= self.mes <= 12:
            raise DatoInvalidoError(f"Mes fuera de rango: {self.mes}")
        if not 2000 <= self.anio <= 2100:
            raise DatoInvalidoError(f"Año fuera de rango: {self.anio}")

    @classmethod
    def de_fecha(cls, fecha: date) -> Periodo:
        return cls(fecha.year, fecha.month)

    @classmethod
    def desde_texto(cls, texto: str) -> Periodo:
        """Acepta "2026-10"."""
        try:
            anio, mes = (int(parte) for parte in texto.strip().split("-"))
        except ValueError:
            raise DatoInvalidoError(f"Periodo no válido: {texto!r}. Usa AAAA-MM") from None
        return cls(anio, mes)

    def contiene(self, fecha: date) -> bool:
        return fecha.year == self.anio and fecha.month == self.mes

    def __str__(self) -> str:
        return f"{self.anio}-{self.mes:02d}"

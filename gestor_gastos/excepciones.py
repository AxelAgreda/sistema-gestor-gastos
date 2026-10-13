"""Jerarquía de excepciones propias del sistema (tipo 5).

Todas heredan de GestorGastosError, así quien usa el sistema puede atrapar
cualquier error esperado con un solo ``except`` sin tapar los errores de
programación (AttributeError, KeyError...), que sí indican un bug.

    GestorGastosError
    ├── DatoInvalidoError
    │   └── MontoInvalidoError
    ├── ReglaNegocioError
    │   ├── CategoriaNoPermitidaError
    │   ├── AhorroInsuficienteError
    │   ├── PresupuestoExcedidoError
    │   └── UsuarioInactivoError
    └── PersistenciaError
"""

from decimal import Decimal


class GestorGastosError(Exception):
    """Raíz de todas las excepciones del sistema."""


# ---------------------------------------------------------------- datos
class DatoInvalidoError(GestorGastosError):
    """Un dato no tiene el formato o el rango esperado."""


class MontoInvalidoError(DatoInvalidoError):
    """El monto no es un número positivo con máximo dos decimales."""

    def __init__(self, valor: object) -> None:
        self.valor = valor
        super().__init__(f"Monto no válido: {valor!r}. Debe ser mayor que cero y "
                         "tener máximo dos decimales")


# ---------------------------------------------------- reglas de negocio
class ReglaNegocioError(GestorGastosError):
    """Una operación válida en forma rompe una regla del gestor."""


class CategoriaNoPermitidaError(ReglaNegocioError):
    """La categoría no está habilitada para ese tipo de movimiento."""

    def __init__(self, categoria: str, tipo: str) -> None:
        self.categoria = categoria
        self.tipo = tipo
        super().__init__(f"La categoría {categoria} no está habilitada para {tipo}")


class AhorroInsuficienteError(ReglaNegocioError):
    """Se intenta retirar del ahorro más de lo acumulado."""

    def __init__(self, solicitado: Decimal, disponible: Decimal) -> None:
        self.solicitado = solicitado
        self.disponible = disponible
        super().__init__(f"Quieres retirar ${solicitado:,.2f} y el ahorro acumulado "
                         f"es ${disponible:,.2f}")


class PresupuestoExcedidoError(ReglaNegocioError):
    """El gasto haría pasar a la categoría de su límite mensual."""

    def __init__(self, categoria: str, limite: Decimal, total: Decimal) -> None:
        self.categoria = categoria
        self.limite = limite
        self.total = total
        super().__init__(f"{categoria} llegaría a ${total:,.2f} este mes y su límite "
                         f"es ${limite:,.2f}")


class UsuarioInactivoError(ReglaNegocioError):
    """El usuario fue desactivado y ya no puede registrar movimientos."""

    def __init__(self, nombre: str) -> None:
        self.nombre = nombre
        super().__init__(f"El usuario {nombre} está inactivo")


# --------------------------------------------------------- persistencia
class PersistenciaError(GestorGastosError):
    """No se pudo leer o escribir el archivo de datos."""

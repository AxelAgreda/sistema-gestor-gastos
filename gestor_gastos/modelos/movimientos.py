"""Movimientos de dinero: clase abstracta (tipo 1) y sus subclases (tipo 2).

Jerarquía:

    SerializableMixin   ABC
            \\          /
             Movimiento            <- clase abstracta (herencia múltiple)
            /   |    |    \\
        Gasto Ingreso Ahorro Retiro <- clases concretas
          |
    GastoRecurrente(RecurrenteMixin, Gasto)  <- herencia múltiple con mixin
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from gestor_gastos.excepciones import CategoriaNoPermitidaError, DatoInvalidoError
from gestor_gastos.modelos.categoria import Categoria
from gestor_gastos.modelos.usuario import Usuario
from gestor_gastos.valores import Periodo, a_monto

if TYPE_CHECKING:  # solo para el verificador de tipos, evita importación circular
    from gestor_gastos.servicios.pote_ahorro import PoteDeAhorro

METODOS_PAGO = ("Efectivo", "Tarjeta", "Transferencia", "Otro")
FORMATO_FECHA = "%d/%m/%Y"


class SerializableMixin:
    """Mixin que convierte un movimiento en diccionario y lo reconstruye.

    Cada subclase concreta se registra sola gracias a __init_subclass__, así
    agregar un tipo nuevo no obliga a tocar el código que carga el archivo.
    """

    _registro: dict[str, type] = {}

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        SerializableMixin._registro[cls.__name__] = cls

    def a_dict(self) -> dict:
        datos = {"clase": type(self).__name__}
        datos.update(self._datos())
        return datos

    def _datos(self) -> dict:
        """Gancho que cada clase extiende con super() para agregar sus campos."""
        return {}

    @classmethod
    def clase_registrada(cls, nombre: str) -> type:
        try:
            return SerializableMixin._registro[nombre]
        except KeyError:
            raise DatoInvalidoError(f"Tipo de movimiento desconocido: {nombre}") from None


class Movimiento(SerializableMixin, ABC):
    """Lo que comparte cualquier movimiento de dinero. No se puede instanciar."""

    TIPO = ""  # cada subclase concreta pone el suyo

    def __init__(
        self,
        id_mov: int,
        monto: object,
        usuario: Usuario,
        categoria: Categoria,
        descripcion: str = "",
        fecha: date | None = None,
        metodo_pago: str = "Efectivo",
    ) -> None:
        if not isinstance(usuario, Usuario):
            raise TypeError("usuario debe ser un objeto Usuario")
        if not isinstance(categoria, Categoria):
            raise TypeError("categoria debe ser un objeto Categoria")
        if not categoria.permite(self.TIPO):
            raise CategoriaNoPermitidaError(categoria.nombre, self.TIPO)
        if metodo_pago not in METODOS_PAGO:
            raise DatoInvalidoError(f"Método de pago no válido: {metodo_pago}")
        self.__id = id_mov  # privado: __eq__ y __hash__ dependen de él
        self._monto = a_monto(monto)  # protegido: las subclases lo usan
        self.usuario = usuario
        self.categoria = categoria
        self.descripcion = " ".join(str(descripcion).split())
        self.fecha = fecha or date.today()
        self.metodo_pago = metodo_pago

    # ------------------------------------------------------ encapsulamiento
    @property
    def id(self) -> int:
        return self.__id

    @property
    def monto(self) -> Decimal:
        return self._monto

    @property
    def periodo(self) -> Periodo:
        return Periodo.de_fecha(self.fecha)

    # ----------------------------------------------------- métodos abstractos
    @abstractmethod
    def efecto_en_balance(self) -> Decimal:
        """Cuánto suma (positivo) o resta (negativo) al balance disponible."""

    @abstractmethod
    def icono(self) -> str:
        """Símbolo corto que identifica el tipo en los listados."""

    # ------------------------------------- método concreto que usa los abstractos
    def resumen(self) -> str:
        """Una línea para el historial; usa icono() y efecto_en_balance()."""
        texto = self.descripcion or self.categoria.nombre
        return (f"{self.icono()} {self.fecha.strftime(FORMATO_FECHA)}  {self.TIPO:<8}"
                f"{self.efecto_en_balance():>+10,.2f}  {self.categoria.emoji} {texto}"
                f" · {self.usuario.nombre}")

    # ------------------------------------------------ comportamiento polimórfico
    def aplicar_en(self, pote: PoteDeAhorro) -> None:
        """Por defecto un movimiento no toca el pote de ahorros."""

    def cuenta_para_presupuesto(self) -> bool:
        return False

    # ------------------------------------------------------------ igualdad
    def __eq__(self, otro: object) -> bool:
        if not isinstance(otro, Movimiento):
            return NotImplemented
        return self.__id == otro.__id

    def __hash__(self) -> int:
        return hash(self.__id)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.__id}, monto={self._monto})"

    # ------------------------------------------------------- serialización
    def _datos(self) -> dict:
        datos = super()._datos()
        datos.update({
            "id": self.__id,
            "monto": str(self._monto),
            "usuario": self.usuario.id,
            "categoria": self.categoria.nombre,
            "descripcion": self.descripcion,
            "fecha": self.fecha.isoformat(),
            "metodo_pago": self.metodo_pago,
        })
        return datos

    @staticmethod
    def desde_dict(
        datos: dict,
        buscar_usuario: Callable[[int], Usuario],
        buscar_categoria: Callable[[str], Categoria],
    ) -> Movimiento:
        """Reconstruye cualquier movimiento a partir del diccionario guardado."""
        clase = SerializableMixin.clase_registrada(datos["clase"])
        comunes = {
            "id_mov": int(datos["id"]),
            "monto": datos["monto"],
            "usuario": buscar_usuario(int(datos["usuario"])),
            "categoria": buscar_categoria(datos["categoria"]),
            "descripcion": datos.get("descripcion", ""),
            "fecha": date.fromisoformat(datos["fecha"]),
            "metodo_pago": datos.get("metodo_pago", "Efectivo"),
        }
        extras = {clave: datos[clave] for clave in clase.CAMPOS_EXTRA if clave in datos}
        return clase(**comunes, **extras)

    CAMPOS_EXTRA: tuple[str, ...] = ()


class Gasto(Movimiento):
    """Dinero que sale: resta al balance y cuenta para el presupuesto."""

    TIPO = "Gasto"

    def efecto_en_balance(self) -> Decimal:
        return -self._monto

    def icono(self) -> str:
        return "▼"

    def cuenta_para_presupuesto(self) -> bool:
        return True


class Ingreso(Movimiento):
    """Dinero que entra, con el periodo que cubre (por ejemplo "1-15 oct")."""

    TIPO = "Ingreso"
    CAMPOS_EXTRA = ("periodo_pago",)

    def __init__(self, id_mov: int, monto: object, usuario: Usuario,
                 categoria: Categoria, descripcion: str = "", fecha: date | None = None,
                 metodo_pago: str = "Transferencia", periodo_pago: str = "") -> None:
        super().__init__(id_mov, monto, usuario, categoria, descripcion, fecha,
                         metodo_pago)
        self.periodo_pago = " ".join(str(periodo_pago).split())

    def efecto_en_balance(self) -> Decimal:
        return self._monto

    def icono(self) -> str:
        return "▲"

    def resumen(self) -> str:
        texto = super().resumen()
        return f"{texto} ({self.periodo_pago})" if self.periodo_pago else texto

    def _datos(self) -> dict:
        datos = super()._datos()
        datos["periodo_pago"] = self.periodo_pago
        return datos


class Ahorro(Movimiento):
    """Dinero que pasa del balance disponible al pote de ahorros."""

    TIPO = "Ahorro"

    def efecto_en_balance(self) -> Decimal:
        return -self._monto

    def icono(self) -> str:
        return "◆"

    def aplicar_en(self, pote: PoteDeAhorro) -> None:
        pote.depositar(self._monto)


class Retiro(Movimiento):
    """Dinero que regresa del pote de ahorros al balance disponible."""

    TIPO = "Retiro"

    def efecto_en_balance(self) -> Decimal:
        return self._monto

    def icono(self) -> str:
        return "◇"

    def aplicar_en(self, pote: PoteDeAhorro) -> None:
        pote.retirar(self._monto)  # lanza AhorroInsuficienteError si no alcanza


class RecurrenteMixin:
    """Mixin para movimientos que se repiten cada mes en un día fijo.

    Es cooperativo: recibe dia_cobro y pasa el resto de argumentos al siguiente
    constructor en el MRO con super().
    """

    CAMPOS_EXTRA = ("dia_cobro",)

    def __init__(self, *args: object, dia_cobro: int = 1, **kwargs: object) -> None:
        if not 1 <= int(dia_cobro) <= 28:
            raise DatoInvalidoError("El día de cobro debe estar entre 1 y 28")
        super().__init__(*args, **kwargs)
        self.dia_cobro = int(dia_cobro)

    def proxima_fecha(self, desde: date | None = None) -> date:
        """Siguiente fecha de cobro a partir de hoy (o de la fecha indicada)."""
        hoy = desde or date.today()
        if hoy.day <= self.dia_cobro:
            return hoy.replace(day=self.dia_cobro)
        anio, mes = (hoy.year + 1, 1) if hoy.month == 12 else (hoy.year, hoy.month + 1)
        return date(anio, mes, self.dia_cobro)

    def resumen(self) -> str:
        return f"{super().resumen()} [cada mes, día {self.dia_cobro}]"

    def _datos(self) -> dict:
        datos = super()._datos()
        datos["dia_cobro"] = self.dia_cobro
        return datos


class GastoRecurrente(RecurrenteMixin, Gasto):
    """Gasto fijo mensual (Netflix, internet). MRO: mixin primero, luego Gasto."""

    def icono(self) -> str:
        return "↻"

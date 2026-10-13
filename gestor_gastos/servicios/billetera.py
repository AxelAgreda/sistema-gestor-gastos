"""Billetera: el gestor del sistema (tipo 3).

Agrupa usuarios, categorías y movimientos, contiene su propio pote de ahorros
(composición) y recibe por el constructor un Repositorio y un Notificador
(interfaces). Expone todas las operaciones que usa el menú.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from decimal import Decimal

from gestor_gastos.excepciones import (
    AhorroInsuficienteError,
    DatoInvalidoError,
    PresupuestoExcedidoError,
    UsuarioInactivoError,
)
from gestor_gastos.interfaces import Notificador, Repositorio
from gestor_gastos.modelos.categoria import TIPOS_MOVIMIENTO, Categoria
from gestor_gastos.modelos.movimientos import Movimiento
from gestor_gastos.modelos.usuario import Usuario
from gestor_gastos.servicios.pote_ahorro import PoteDeAhorro
from gestor_gastos.valores import Periodo

CERO = Decimal("0.00")
CRITERIOS_VALIDOS = {"periodo", "categoria", "usuario", "metodo_pago"}


class Billetera:
    """Billetera compartida entre varios usuarios."""

    def __init__(self, nombre: str, repositorio: Repositorio,
                 notificador: Notificador) -> None:
        self.nombre = nombre
        self._repositorio = repositorio
        self._notificador = notificador
        # Composición: estas colecciones y el pote nacen y mueren con la billetera
        self.__usuarios: dict[int, Usuario] = {}
        self.__categorias: dict[str, Categoria] = {}
        self.__movimientos: list[Movimiento] = []
        self.__pote = PoteDeAhorro()
        # RLock: el hilo de respaldo lee mientras el menú escribe
        self._candado = threading.RLock()

    # =============================================================== catálogos
    def agregar_usuarios(self, *usuarios: Usuario) -> None:
        with self._candado:
            for usuario in usuarios:
                self.__usuarios[usuario.id] = usuario

    def agregar_categorias(self, *categorias: Categoria) -> None:
        with self._candado:
            for categoria in categorias:
                self.__categorias[categoria.nombre] = categoria

    def usuario(self, id_usuario: int) -> Usuario:
        try:
            return self.__usuarios[id_usuario]
        except KeyError:
            raise DatoInvalidoError(f"No existe el usuario {id_usuario}") from None

    def categoria(self, nombre: str) -> Categoria:
        clave = " ".join(str(nombre).split()).capitalize()
        try:
            return self.__categorias[clave]
        except KeyError:
            raise DatoInvalidoError(f"No existe la categoría {nombre!r}") from None

    @property
    def usuarios(self) -> tuple[Usuario, ...]:
        return tuple(self.__usuarios.values())

    @property
    def categorias(self) -> tuple[Categoria, ...]:
        return tuple(self.__categorias.values())

    def categorias_para(self, tipo: str) -> list[Categoria]:
        """Como en la app: el formulario solo muestra las categorías del tipo."""
        return [c for c in self.__categorias.values() if c.permite(tipo)]

    def siguiente_id(self) -> int:
        with self._candado:
            return max((m.id for m in self.__movimientos), default=0) + 1

    # ============================================================ operaciones
    # Sobrecarga simulada: registrar(m) o registrar(m1, m2, m3)
    def registrar(self, *movimientos: Movimiento) -> None:
        """Valida y agrega uno o varios movimientos, en orden."""
        if not movimientos:
            raise TypeError("registrar() necesita al menos un movimiento")
        for movimiento in movimientos:
            with self._candado:
                self._validar(movimiento)
                movimiento.aplicar_en(self.__pote)  # polimorfismo: solo Ahorro/Retiro
                self.__movimientos.append(movimiento)
            self._notificador.enviar(
                movimiento.usuario.nombre,
                f"{movimiento.TIPO} registrado: ${movimiento.monto:,.2f} en "
                f"{movimiento.categoria.nombre}")

    def _validar(self, movimiento: Movimiento) -> None:
        if not isinstance(movimiento, Movimiento):
            raise TypeError("Solo se pueden registrar objetos Movimiento")
        if movimiento in self.__movimientos:  # usa __eq__: mismo id
            raise DatoInvalidoError(f"Ya existe un movimiento con id {movimiento.id}")
        usuario = self.usuario(movimiento.usuario.id)
        if not usuario.activo:
            raise UsuarioInactivoError(usuario.nombre)
        self.categoria(movimiento.categoria.nombre)  # debe estar registrada
        if movimiento.cuenta_para_presupuesto():
            self._validar_presupuesto(movimiento)

    def _validar_presupuesto(self, movimiento: Movimiento) -> None:
        limite = movimiento.categoria.limite_mensual
        if limite is None:
            return
        total = self.gastado_en(movimiento.categoria, movimiento.periodo) + movimiento.monto
        if total > limite:
            raise PresupuestoExcedidoError(movimiento.categoria.nombre, limite, total)

    def eliminar(self, id_mov: int) -> Movimiento:
        """Borra un movimiento mal registrado (en la app: el botón de la papelera).

        Un ahorro no se puede borrar si ese dinero ya se retiró del pote.
        """
        with self._candado:
            movimiento = next((m for m in self.__movimientos if m.id == id_mov), None)
            if movimiento is None:
                raise DatoInvalidoError(f"No existe el movimiento {id_mov}")
            posicion = self.__movimientos.index(movimiento)
            self.__movimientos.remove(movimiento)
            try:
                self._recalcular_pote()
            except AhorroInsuficienteError:
                self.__movimientos.insert(posicion, movimiento)  # se deshace el borrado
                raise
            return movimiento

    def _recalcular_pote(self) -> None:
        nuevo = PoteDeAhorro()
        for movimiento in self.__movimientos:
            movimiento.aplicar_en(nuevo)
        self.__pote = nuevo

    # ============================================================== consultas
    @property
    def movimientos(self) -> tuple[Movimiento, ...]:
        with self._candado:
            return tuple(self.__movimientos)

    @property
    def ahorro_acumulado(self) -> Decimal:
        return self.__pote.saldo

    def __len__(self) -> int:
        return len(self.__movimientos)

    def __iter__(self) -> Iterator[Movimiento]:
        return iter(self.movimientos)

    # Sobrecarga simulada: un solo método cubre muchas combinaciones de filtros
    def filtrar(self, tipo: type[Movimiento] | None = None,
                **criterios: object) -> list[Movimiento]:
        """filtrar(), filtrar(Gasto), filtrar(periodo="2026-10", usuario="Edwin")..."""
        desconocidos = set(criterios) - CRITERIOS_VALIDOS
        if desconocidos:
            raise TypeError(f"Criterio no válido: {', '.join(sorted(desconocidos))}")
        periodo = criterios.get("periodo")
        if isinstance(periodo, str):
            periodo = Periodo.desde_texto(periodo)
        resultado = []
        for mov in self.movimientos:
            if tipo is not None and not isinstance(mov, tipo):
                continue
            if periodo is not None and not periodo.contiene(mov.fecha):
                continue
            if not _coincide(mov.categoria.nombre, criterios.get("categoria")):
                continue
            if not _coincide(mov.usuario.nombre, criterios.get("usuario")):
                continue
            if not _coincide(mov.metodo_pago, criterios.get("metodo_pago")):
                continue
            resultado.append(mov)
        return resultado

    def gastado_en(self, categoria: Categoria, periodo: Periodo) -> Decimal:
        return sum((m.monto for m in self.movimientos
                    if m.cuenta_para_presupuesto() and m.categoria == categoria
                    and periodo.contiene(m.fecha)), CERO)

    def balance(self, periodo: Periodo | None = None) -> Decimal:
        """Ingresos - Gastos - (Ahorros - Retiros): la misma fórmula de la app."""
        movimientos = self.filtrar(periodo=periodo) if periodo else self.movimientos
        return sum((m.efecto_en_balance() for m in movimientos), CERO)

    def totales_por_tipo(self, periodo: Periodo | None = None) -> dict[str, Decimal]:
        totales = dict.fromkeys(TIPOS_MOVIMIENTO, CERO)
        movimientos = self.filtrar(periodo=periodo) if periodo else self.movimientos
        for mov in movimientos:
            totales[mov.TIPO] += mov.monto
        return totales

    def gastos_por_categoria(self, periodo: Periodo) -> dict[str, Decimal]:
        resultado: dict[str, Decimal] = {}
        for mov in self.filtrar(periodo=periodo):
            if mov.cuenta_para_presupuesto():
                nombre = f"{mov.categoria.emoji} {mov.categoria.nombre}"
                resultado[nombre] = resultado.get(nombre, CERO) + mov.monto
        return dict(sorted(resultado.items(), key=lambda par: par[1], reverse=True))

    # =========================================================== persistencia
    def a_dict(self) -> dict:
        with self._candado:
            return {
                "nombre": self.nombre,
                "usuarios": [u.a_dict() for u in self.__usuarios.values()],
                "categorias": [c.a_dict() for c in self.__categorias.values()],
                "movimientos": [m.a_dict() for m in self.__movimientos],
            }

    def guardar(self) -> None:
        self._repositorio.guardar(self.a_dict())

    def cargar(self) -> int:
        """Reemplaza el contenido con lo guardado. Devuelve cuántos movimientos leyó."""
        datos = self._repositorio.cargar()
        if not datos:
            return 0
        with self._candado:
            self.__usuarios.clear()
            self.__categorias.clear()
            self.__movimientos.clear()
            self.agregar_usuarios(*(Usuario.desde_dict(u) for u in datos["usuarios"]))
            self.agregar_categorias(*(Categoria.desde_dict(c) for c in datos["categorias"]))
            for registro in datos["movimientos"]:
                self.__movimientos.append(
                    Movimiento.desde_dict(registro, self.usuario, self.categoria))
            self._recalcular_pote()
            return len(self.__movimientos)


def _coincide(valor: str, esperado: object) -> bool:
    return esperado is None or valor.lower() == str(esperado).strip().lower()

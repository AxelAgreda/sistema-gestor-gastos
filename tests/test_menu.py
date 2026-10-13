"""Prueba del menú simulando lo que escribe el usuario."""

from gestor_gastos.consola.menu import MenuConsola


def test_menu_registra_y_muestra_resumen(tmp_path, billetera, capsys):
    respuestas = iter([
        "1",            # registrar
        "1", "1", "1",  # tipo Gasto, usuario Edwin, categoría Comida
        "12.50", "Pizza", "2", "2026-10-15",
        "3", "2026-10",  # resumen de octubre
        "1", "1", "1", "1", "abc", "x", "1", "",  # monto inválido
        "0",
    ])
    MenuConsola(billetera, tmp_path, entrada=lambda _: next(respuestas)).ejecutar()
    salida = capsys.readouterr().out
    assert "✓ Guardado" in salida and "Pizza" in salida
    assert "Balance" in salida and "-12.50" in salida
    assert "MontoInvalidoError" in salida
    assert len(billetera) == 1

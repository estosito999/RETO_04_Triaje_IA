import numpy as np

from analisis.metricas import matriz_clasificacion
from interfaz.visualizaciones import vista_turno
from modelos.variables import ALTA, BAJA, Parametros
from simulacion.generador_datos import PacienteSintetico
from simulacion.motor import _simular_estrategia


def test_vista_muestra_asignacion_solo_despues_del_triaje_y_excluye_llegada_al_cierre():
    p = Parametros(pacientes=2, medicos=1, enfermeros=1, horas_turno=1)
    cohorte = [
        PacienteSintetico(1, 1, ALTA, 0.1, 0.1, 1, 4, False, 0, 0),
        PacienteSintetico(2, 60, BAJA, 0.1, 0.1, 1, 4, False, 0, 0),
    ]
    resultado = _simular_estrategia(p, cohorte, asistido=True)
    antes = vista_turno(resultado.pacientes, 1.5, asistido=True)
    sin_clasificar = next(traza for traza in antes.data if traza.name == "Sin clasificar")
    assert list(sin_clasificar.text) == ["1"]
    assert sin_clasificar.customdata[0][2] == "Sin clasificar"
    assert sum(len(traza.x) for traza in antes.data) == 1

    despues = vista_turno(resultado.pacientes, 60, asistido=True)
    asignada_baja = next(traza for traza in despues.data if traza.name == "Baja (3)")
    assert list(asignada_baja.text) == ["1"]
    assert list(asignada_baja.customdata[0][1:]) == ["Alta (1)", "Baja (3)"]
    assert sum(len(traza.x) for traza in despues.data) == resultado.cronologia.llegados.iloc[-1] == 1

    matriz = matriz_clasificacion(resultado)
    assert matriz.loc["Alta", "Baja"] == 1
    assert matriz.to_numpy().sum() == 1


def test_fifo_muestra_referencia_y_clasificacion_no_aplica():
    p = Parametros(pacientes=1, medicos=1, enfermeros=1, horas_turno=1)
    cohorte = [PacienteSintetico(1, 1, ALTA, 0.1, 0.1, 1, 4, False, 0, 0)]
    resultado = _simular_estrategia(p, cohorte, asistido=False)
    figura = vista_turno(resultado.pacientes, 3)
    alta = next(traza for traza in figura.data if traza.name == "Alta (1)")
    assert list(alta.text) == ["1"]
    assert alta.customdata[0][2] == "No aplica en FIFO"
    np.testing.assert_array_equal(matriz_clasificacion(resultado), np.zeros((3, 3), dtype=int))

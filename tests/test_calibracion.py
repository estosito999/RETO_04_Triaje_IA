from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from analisis.calibracion import calibrar_desde_datos
from modelos.variables import Parametros


def _datos() -> pd.DataFrame:
    return pd.DataFrame({
        "llegada_min": [1, 5, 10, 20, 30, 40, 65, 70],
        "duracion_triaje_min": [2, 3, 4, 5, 2, 3, 4, 5],
        "duracion_consulta_min": [10, 14, 15, 21, 20, 28, 12, 18],
        "prioridad_referencia": [1, 1, 2, 2, 3, 3, 1, 2],
    })


def test_calibracion_incluye_horas_y_turnos_sin_llegadas():
    p = replace(Parametros(), horas_turno=4)
    ajustados, informe = calibrar_desde_datos(_datos(), p, numero_turnos=2)
    assert ajustados.llegadas_por_hora == 1
    assert ajustados.perfil_llegadas == (3.0, 1.0, 0.0, 0.0)
    assert ajustados.triaje_medio_min == 3.5
    assert ajustados.medias_consulta_prioridad == pytest.approx((12.0, 18.0, 24.0))
    assert ajustados.proporcion_prioritarios == 0.75
    assert ajustados.fraccion_alta_prioritarios == 0.5
    assert informe.attrs["metadatos"]["horas_observadas"] == 8
    assert informe.estimacion.map(np.isfinite).all()


def test_calibracion_conserva_medias_de_grupos_ausentes_y_formas_sin_variacion():
    datos = _datos().iloc[:2].copy()
    datos["duracion_triaje_min"] = 4
    datos["duracion_consulta_min"] = 12
    p = replace(Parametros(), horas_turno=1, medias_consulta_prioridad=(20.0, 22.0, 24.0))
    ajustados, informe = calibrar_desde_datos(datos, p)
    assert ajustados.medias_consulta_prioridad == (12, 22, 24)
    assert ajustados.forma_triaje == p.forma_triaje
    assert ajustados.forma_consulta == p.forma_consulta
    assert informe.attrs["metadatos"]["grupos_sin_ajuste_de_media"] == ["Media", "Baja"]


def test_calibracion_sin_prioritarios_conserva_separacion_alta_media():
    datos = _datos().iloc[:2].copy()
    datos["prioridad_referencia"] = 3
    p = replace(Parametros(), horas_turno=1, fraccion_alta_prioritarios=0.65)
    ajustados, informe = calibrar_desde_datos(datos, p)
    assert ajustados.proporcion_prioritarios == 0
    assert ajustados.fraccion_alta_prioritarios == 0.65
    fila = informe.loc[informe.parametro == "fraccion_alta_prioritarios"].iloc[0]
    assert fila.n == 0
    assert fila.metodo == "valor anterior conservado"


@pytest.mark.parametrize("columna,valor", [
    ("llegada_min", -1), ("llegada_min", 60), ("duracion_consulta_min", np.nan),
    ("duracion_triaje_min", 0), ("prioridad_referencia", 1.5), ("prioridad_referencia", 4),
])
def test_calibracion_rechaza_datos_invalidos_sin_descartarlos(columna, valor):
    datos = _datos().iloc[:2].astype(float)
    datos.loc[0, columna] = valor
    with pytest.raises(ValueError):
        calibrar_desde_datos(datos, replace(Parametros(), horas_turno=1))


def test_calibracion_rechaza_estimacion_fuera_de_rango_sin_recortarla():
    datos = _datos().iloc[:2].copy()
    datos["duracion_consulta_min"] = [100, 120]
    with pytest.raises(ValueError, match="fuera del rango"):
        calibrar_desde_datos(datos, replace(Parametros(), horas_turno=1))


@pytest.mark.parametrize("turnos", [0, -1, 1.5, True])
def test_calibracion_exige_exposicion_valida(turnos):
    with pytest.raises(ValueError, match="turnos completos"):
        calibrar_desde_datos(_datos(), Parametros(), numero_turnos=turnos)

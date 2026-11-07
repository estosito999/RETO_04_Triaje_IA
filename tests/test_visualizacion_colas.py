import numpy as np
import pandas as pd
import pytest

from interfaz.visualizaciones import vista_turno
from modelos.variables import ALTA, BAJA, Parametros
from simulacion.generador_datos import PacienteSintetico
from simulacion.motor import _simular_estrategia


@pytest.mark.parametrize("etapa", [0, 2])
def test_cola_de_cien_pacientes_se_dibuja_completa_dentro_de_su_etapa(etapa):
    pacientes = pd.DataFrame({
        "id_paciente": range(1, 101), "llegada_min": 0., "estado": "cola_medica",
        "prioridad_referencia": BAJA, "prioridad_asignada": BAJA,
        "inicio_triaje_min": 1. if etapa == 2 else np.nan,
        "fin_triaje_min": 2. if etapa == 2 else np.nan,
        "inicio_consulta_min": np.nan, "fin_consulta_min": np.nan,
    })
    figura = vista_turno(pacientes, 4, asistido=True)
    puntos = [(x, y) for traza in figura.data for x, y in zip(traza.x, traza.y)]
    ids = [identificador for traza in figura.data for identificador in traza.text]
    assert len(puntos) == len(set(puntos)) == len(set(ids)) == 100
    assert all(etapa - .46 < x < etapa + .46 and .05 < y < .85 for x, y in puntos)
    assert next(a.text for a in figura.layout.annotations if a.x == etapa) == "100"
    assert next(a.text for a in figura.layout.annotations if a.x == 4) == "0"


def test_punto_aparece_al_llegar_y_sale_exactamente_al_terminar_consulta():
    p = Parametros(pacientes=1, medicos=1, enfermeros=1, horas_turno=1)
    cohorte = [PacienteSintetico(1, 1, ALTA, .9, .9, 1, 4, True, 0, 120)]
    resultado = _simular_estrategia(p, cohorte, asistido=True)
    fin = resultado.pacientes.fin_consulta_min.iloc[0]
    assert fin == 6
    assert resultado.pacientes.tele_respondida_min.isna().all()

    for minuto, activos, salidas in ((.999, 0, 0), (1., 1, 0), (fin - .001, 1, 0), (fin, 0, 1), (60., 0, 1)):
        figura = vista_turno(resultado.pacientes, minuto, asistido=True, eventos=resultado.eventos)
        assert sum(len(traza.x) for traza in figura.data) == activos
        assert next(a.text for a in figura.layout.annotations if a.x == 4) == str(salidas)
    assert len(resultado.pacientes) == 1

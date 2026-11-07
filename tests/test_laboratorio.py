from dataclasses import asdict, replace
import json

import pandas as pd
import pytest

from analisis.experimentos import ejecutar_replicas, semillas_replicas
from modelos.variables import BAJA
from simulacion.escenarios import PARAMETROS_LABORATORIO, REPETICIONES_LABORATORIO
from simulacion.generador_datos import PacienteSintetico, generar_pacientes
import simulacion.motor as motor


def test_laboratorio_observa_un_dia_con_llegadas_cortas_y_cupo_acotado():
    p = PARAMETROS_LABORATORIO
    assert p.horas_turno == 24
    assert p.turno_min == p.horizonte_min == 1440
    cohorte = generar_pacientes(p)
    assert len(cohorte) == 100
    assert 0 < cohorte[-1].llegada_min <= 500 < p.turno_min
    assert all(caso.duracion_consulta_min >= 15 for caso in cohorte)


@pytest.mark.parametrize("semilla", [42, 43, 44])
def test_laboratorio_limita_admisiones_y_eventos_al_turno(semilla):
    p = replace(PARAMETROS_LABORATORIO, semilla=semilla)
    exp = motor.simular(p)
    for resultado in (exp.referencia, exp.asistido):
        admitidos = resultado.pacientes.loc[resultado.pacientes.estado.ne("no_llego")]
        assert len(admitidos) <= 100
        assert admitidos.llegada_min.between(0, 1440, inclusive="left").all()
        assert len(admitidos) == 100
        assert resultado.cronologia.cola_medica.max() > 0
        assert resultado.eventos.minuto.between(0, 1440, inclusive="left").all()
        assert resultado.cronologia.minuto.iloc[-1] == 1440
        assert resultado.cronologia.llegados.iloc[-1] == len(admitidos)


def test_politicas_del_laboratorio_comparten_entradas_y_duraciones():
    exp = motor.simular(PARAMETROS_LABORATORIO)
    fifo, asistido = exp.referencia.pacientes, exp.asistido.pacientes
    entradas = ["id_paciente", "llegada_min", "prioridad_referencia", "senal_a", "senal_b"]
    pd.testing.assert_frame_equal(fifo[entradas], asistido[entradas])
    for inicio, fin in (
        ("inicio_triaje_min", "fin_triaje_min"),
        ("inicio_consulta_min", "fin_servicio_local_min"),
    ):
        completos = fifo[fin].notna() & asistido[fin].notna()
        assert completos.any()
        pd.testing.assert_series_equal(
            fifo.loc[completos, fin] - fifo.loc[completos, inicio],
            asistido.loc[completos, fin] - asistido.loc[completos, inicio],
            check_names=False,
        )


def test_llegadas_al_cierre_o_despues_no_se_admiten(monkeypatch):
    cohorte = [
        PacienteSintetico(i, llegada, BAJA, .2, .2, 4, 16, False, .1, 45)
        for i, llegada in enumerate((1., 1439., 1440., 1441.), start=1)
    ]
    monkeypatch.setattr(motor, "generar_pacientes", lambda _: cohorte)
    exp = motor.simular(PARAMETROS_LABORATORIO)
    for resultado in (exp.referencia, exp.asistido):
        tardios = resultado.pacientes.llegada_min >= 1440
        assert resultado.pacientes.loc[tardios, "estado"].eq("no_llego").all()
        assert set(resultado.eventos.id_paciente) == {1, 2}
        assert resultado.eventos.minuto.lt(1440).all()
        assert resultado.cronologia.llegados.iloc[-1] == 2


def test_replicas_cambian_azar_y_conservan_condiciones_del_laboratorio():
    p = PARAMETROS_LABORATORIO
    semillas = semillas_replicas(REPETICIONES_LABORATORIO, p.semilla)
    assert len(semillas) == len(set(semillas)) == 30
    assert generar_pacientes(replace(p, semilla=semillas[0])) != generar_pacientes(
        replace(p, semilla=semillas[1])
    )
    mediciones = ejecutar_replicas(p, semillas[:2])
    assert set(mediciones.semilla) == set(semillas[:2])
    assert set(mediciones.estrategia) == {"FIFO", "Triaje asistido"}
    condiciones = asdict(p)
    condiciones.pop("semilla")
    for parametros in mediciones.parametros_json.unique():
        observados = json.loads(parametros)
        observados.pop("semilla")
        # La serialización JSON representa las tuplas como listas.
        assert observados == json.loads(json.dumps(condiciones))

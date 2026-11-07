from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from analisis.metricas import resumir
from modelos.variables import ALTA, Parametros
from simulacion.generador_datos import PacienteSintetico, generar_intentos_conexion, generar_pacientes
import simulacion.motor as motor


def test_teleconsulta_reintenta_hasta_recuperar_conexion_sin_ocupar_personal(monkeypatch):
    p = Parametros(pacientes=1, medicos=1, enfermeros=1, horas_turno=1,
                   disponibilidad_conexion=0.5, intervalo_reintento_min=5)
    paciente = PacienteSintetico(1, 1, ALTA, 0.9, 0.9, 1, 4, True, 0.9, 9)
    monkeypatch.setattr(motor, "generar_intentos_conexion", lambda *_: np.array([0.9, 0.8, 0.1]))
    resultado = motor._simular_estrategia(p, [paciente], asistido=True)
    fila = resultado.pacientes.iloc[0]
    assert fila.tele_solicitada_min == 2
    assert fila.tele_enviada_min == 12
    assert fila.tele_respondida_min == 21
    assert fila.fin_consulta_min == 6
    assert fila.intentos_envio == 3
    assert fila.ultimo_intento_envio_min == 12
    intentos = resultado.eventos.loc[resultado.eventos.evento == "tele_intento", "minuto"]
    assert list(intentos) == [2, 7, 12]
    serie = resultado.cronologia.set_index("minuto")
    assert tuple(serie.loc[5, ["telepor_enviar", "teleesperando_respuesta", "telerespondidas"]]) == (1, 0, 0)
    assert tuple(serie.loc[15, ["telepor_enviar", "teleesperando_respuesta", "telerespondidas"]]) == (0, 1, 0)
    assert tuple(serie.loc[25, ["telepor_enviar", "teleesperando_respuesta", "telerespondidas"]]) == (0, 0, 1)
    metricas = resumir(resultado, p)
    assert metricas["reintentos_envio"] == 2
    assert metricas["demora_envio_teleconsulta_min"] == 10
    assert metricas["respuesta_teleconsulta_min"] == 9
    assert metricas["respuesta_total_teleconsulta_min"] == 19


def test_sin_conexion_los_reintentos_terminan_al_cierre_del_turno():
    p = Parametros(pacientes=1, horas_turno=1, disponibilidad_conexion=0, intervalo_reintento_min=5)
    paciente = PacienteSintetico(1, 48, ALTA, 0.9, 0.9, 1, 4, True, 0.1, 9)
    resultado = motor._simular_estrategia(p, [paciente], asistido=True)
    fila = resultado.pacientes.iloc[0]
    assert fila.intentos_envio == 3  # 49, 54, 59; el siguiente está fuera del turno.
    assert pd.isna(fila.tele_enviada_min)
    assert resultado.eventos.minuto.max() == 59
    metricas = resumir(resultado, p)
    assert metricas["teleconsultas_sin_enviar"] == metricas["teleconsultas_pendientes"] == 1
    assert metricas["teleconsultas_esperando_respuesta"] == 0
    assert metricas["respuesta_total_teleconsulta_min"] is None


def test_sorteos_emparejados_y_balance_de_pendientes_en_cada_instante():
    p = Parametros(disponibilidad_conexion=0.1, intervalo_reintento_min=3)
    paciente = generar_pacientes(p)[0]
    sorteos = generar_intentos_conexion(p, paciente)
    np.testing.assert_array_equal(sorteos, generar_intentos_conexion(replace(p, disponibilidad_conexion=1), paciente))
    assert sorteos[0] == paciente.sorteo_conexion
    assert len(sorteos) > p.turno_min / p.intervalo_reintento_min
    primera = motor.simular(p)
    repetida = motor.simular(p)
    pd.testing.assert_frame_equal(primera.asistido.eventos, repetida.asistido.eventos)
    for resultado in (primera.referencia, primera.asistido):
        serie = resultado.cronologia
        assert (serie.telependientes == serie.telepor_enviar + serie.teleesperando_respuesta).all()
        assert (serie[["telepor_enviar", "teleesperando_respuesta", "telerespondidas"]] >= 0).all().all()
        enviadas = resultado.eventos.loc[resultado.eventos.evento == "tele_enviada", "id_paciente"]
        assert not enviadas.duplicated().any()


@pytest.mark.parametrize("intervalo", [0, -1, 61, float("nan"), float("inf")])
def test_rechaza_intervalo_de_reintento_invalido(intervalo):
    with pytest.raises(ValueError):
        Parametros(intervalo_reintento_min=intervalo)

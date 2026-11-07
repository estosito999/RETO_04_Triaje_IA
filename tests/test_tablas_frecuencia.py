from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from analisis.metricas import carga_ofrecida
from modelos.distribuciones import (
    TABLA_INTERARRIBOS, TABLA_SERVICIOS, generar_desde_frecuencias, media_frecuencias,
)
from modelos.variables import Parametros
from simulacion.generador_datos import generar_pacientes
from simulacion.motor import simular


@pytest.mark.parametrize("tabla,esperada", [(TABLA_INTERARRIBOS, 2.56), (TABLA_SERVICIOS, 25.)])
def test_medias_exactas_de_las_tablas(tabla, esperada):
    assert media_frecuencias(tabla) == pytest.approx(esperada)


@pytest.mark.parametrize("tabla", [TABLA_INTERARRIBOS, TABLA_SERVICIOS])
def test_transformada_inversa_respeta_fronteras_izquierdas_y_soporte(tabla):
    valores, frecuencias = np.asarray(tabla).T
    fronteras = frecuencias.cumsum() / frecuencias.sum()
    np.testing.assert_array_equal(generar_desde_frecuencias(tabla, fronteras), valores)
    np.testing.assert_array_equal(
        generar_desde_frecuencias(tabla, np.nextafter(fronteras[:-1], 1.)), valores[1:],
    )
    np.testing.assert_array_equal(generar_desde_frecuencias(tabla, [0., 1.]), valores[[0, -1]])
    muestra = generar_desde_frecuencias(tabla, np.random.Generator(np.random.PCG64(42)).random(1000))
    assert set(muestra) == set(valores)


@pytest.mark.parametrize("cambio", [
    {"usar_tablas_frecuencia": 1},
    {"perfil_llegadas": (1.,) * 8},
    {"generar_hasta_cierre": True},
    {"medias_consulta_prioridad": (15., 25., 35.)},
])
def test_rechaza_configuraciones_incompatibles_con_tablas(cambio):
    with pytest.raises(ValueError):
        Parametros(**({"usar_tablas_frecuencia": True} | cambio))


def test_carga_nominal_usa_medias_de_tablas_aunque_los_campos_genericos_difieran():
    p = Parametros(usar_tablas_frecuencia=True, medicos=2)
    esperado = 25 / (2.56 * 2)
    assert carga_ofrecida(p) == pytest.approx(esperado)
    assert carga_ofrecida(replace(p, llegadas_por_hora=1, duracion_consulta_min=2)) == pytest.approx(esperado)


def test_generacion_por_tablas_es_reproducible_y_separa_flujos():
    p = Parametros(usar_tablas_frecuencia=True, pacientes=100, horas_turno=24)
    primera = generar_pacientes(p)
    assert primera == generar_pacientes(p)
    assert primera != generar_pacientes(replace(p, semilla=43))
    assert primera == generar_pacientes(replace(p, llegadas_por_hora=1, duracion_consulta_min=2))
    intervalos = np.diff([0.] + [paciente.llegada_min for paciente in primera])
    assert set(intervalos) <= {valor for valor, _ in TABLA_INTERARRIBOS}
    assert {paciente.duracion_consulta_min for paciente in primera} <= {valor for valor, _ in TABLA_SERVICIOS}
    generica = generar_pacientes(replace(p, usar_tablas_frecuencia=False))
    np.testing.assert_array_equal(
        [paciente.duracion_triaje_min for paciente in primera],
        [paciente.duracion_triaje_min for paciente in generica],
    )
    for discreto, continuo in zip(primera, generica):
        assert (discreto.prioridad_referencia, discreto.senal_a, discreto.senal_b,
                discreto.requiere_teleconsulta, discreto.sorteo_conexion, discreto.demora_remota_min) == (
                    continuo.prioridad_referencia, continuo.senal_a, continuo.senal_b,
                    continuo.requiere_teleconsulta, continuo.sorteo_conexion, continuo.demora_remota_min)


def test_modelo_generico_conserva_la_cohorte_previa_al_modo_tablas():
    cohorte = generar_pacientes(Parametros(pacientes=3))
    assert not Parametros().usar_tablas_frecuencia
    np.testing.assert_allclose([p.llegada_min for p in cohorte],
                               [4.843888203313488, 13.985374124115978, 16.272776746583922], rtol=0, atol=1e-12)
    np.testing.assert_allclose([p.duracion_triaje_min for p in cohorte],
                               [1.7182237066056276, 5.046156248677989, 4.598873761269615], rtol=0, atol=1e-12)
    np.testing.assert_allclose([p.duracion_consulta_min for p in cohorte],
                               [13.827716660883667, 21.15744220565658, 16.379665473730345], rtol=0, atol=1e-12)


def test_treinta_semillas_consecutivas_forman_cola_y_respetan_cupo_y_corte():
    p = Parametros(usar_tablas_frecuencia=True, pacientes=100, horas_turno=24,
                   medicos=2, enfermeros=1, llegadas_por_hora=60 / 2.56, duracion_consulta_min=25)
    for semilla in range(42, 72):
        exp = simular(replace(p, semilla=semilla))
        fifo, asistido = exp.referencia, exp.asistido
        entradas = ["id_paciente", "llegada_min", "prioridad_referencia", "senal_a", "senal_b"]
        pd.testing.assert_frame_equal(fifo.pacientes[entradas], asistido.pacientes[entradas])
        assert fifo.cronologia.cola_medica.max() > 0
        assert fifo.cronologia.llegados.iloc[-1] == 100
        for resultado in (fifo, asistido):
            assert resultado.pacientes.estado.ne("no_llego").sum() <= 100
            assert resultado.eventos.minuto.between(0, 1440, inclusive="left").all()
            assert resultado.cronologia.minuto.iloc[-1] == 1440

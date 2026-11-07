from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from analisis.experimentos import ejecutar_replicas, resumen_pareado, semillas_replicas
from analisis.metricas import carga_ofrecida, clasificacion_por_prioridad, resumir
from analisis.validacion import diagnosticar_azar
from modelos.variables import ALTA, BAJA, Parametros
from simulacion.generador_datos import PacienteSintetico
from simulacion.motor import _simular_estrategia


def cohorte_con_pendiente():
    return [PacienteSintetico(1, 1, ALTA, .9, .9, 1, 100, False, .1, 0),
            PacienteSintetico(2, 3, BAJA, .2, .2, 1, 4, False, .1, 0)]


def test_esperas_censuradas_incluyen_paciente_que_no_inicia_y_no_imputan_cero():
    p = Parametros(pacientes=2, horas_turno=1, medicos=1, enfermeros=1)
    r = _simular_estrategia(p, cohorte_con_pendiente(), True)
    m = resumir(r, p)
    assert m["pacientes_llegados"] == 2
    assert m["consultas_iniciadas"] == 1
    assert m["pacientes_sin_iniciar_consulta"] == 1
    assert m["pacientes_sin_completar"] == 2
    assert m["tiempo_hasta_atencion_min"] == 1
    assert m["espera_acumulada_hasta_consulta_min"] == 29  # (1 + 57) / 2
    assert m["espera_medica_acumulada_min"] == 28  # (0 + 56) / 2
    assert m["carga_medicos_pct"] == pytest.approx(100*58/60)


def test_seguimiento_no_contamina_metricas_del_cierre():
    p = Parametros(pacientes=2, horas_turno=1, medicos=1, enfermeros=1)
    con_seguimiento = replace(p, seguimiento_min=120)
    original = resumir(_simular_estrategia(p, cohorte_con_pendiente(), True), p)
    extendido = resumir(_simular_estrategia(con_seguimiento, cohorte_con_pendiente(), True), con_seguimiento)
    assert extendido["pacientes_atendidos"] == 2
    assert extendido["pacientes_atendidos_al_cierre"] == original["pacientes_atendidos"] == 0
    assert extendido["carga_medicos_pct_al_cierre"] == original["carga_medicos_pct"]
    assert extendido["espera_acumulada_hasta_consulta_min_al_cierre"] == original["espera_acumulada_hasta_consulta_min"]
    assert extendido["horizonte_observacion_min"] == 180
    assert extendido["horizonte_observacion_min_al_cierre"] == 60


def test_clasificador_reporta_fallo_alto_y_perdida_asimetrica():
    p = Parametros(pacientes=2, horas_turno=1)
    pacientes = [PacienteSintetico(1, 1, ALTA, .1, .1, 1, 4, False, .1, 0),
                 PacienteSintetico(2, 2, BAJA, .9, .9, 1, 4, False, .1, 0)]
    r = _simular_estrategia(p, pacientes, True)
    m = resumir(r, p)
    assert m["sensibilidad_alta_pct"] == 0
    assert m["perdida_clasificacion_media"] == 6  # (alta->baja=10 + baja->alta=2) / 2
    clases = clasificacion_por_prioridad(r).set_index("prioridad_referencia")
    assert clases.loc[ALTA, "subtriaje_pct"] == 100
    assert pd.isna(clases.loc[2, "sensibilidad_pct"])


def test_carga_ofrecida_pondera_perfil_y_distribucion_de_clases():
    p = Parametros(horas_turno=2, perfil_llegadas=(0., 2.), medias_consulta_prioridad=(30., 20., 10.))
    assert carga_ofrecida(p) == pytest.approx(12*(.12*30+.18*20+.7*10)/(60*3))


def datos_pareados(diferencias):
    return pd.DataFrame([{"escenario": "Caso", "condicion": "Base", "semilla": i,
        "estrategia": estrategia, "metrica": "espera", "valor": valor}
        for i, d in enumerate(diferencias)
        for estrategia, valor in (("FIFO", 10.), ("Triaje asistido", 10+d))])


def test_ic_pareado_calcula_diferencias_por_semilla_y_student():
    fila = resumen_pareado(datos_pareados([1., 2., 3.])).iloc[0]
    assert fila.pares_validos == 3
    assert fila.diferencia_media == 2
    assert fila.error_estandar == pytest.approx(1/np.sqrt(3))
    assert fila.ic95_inferior == pytest.approx(-.4841377, abs=1e-6)
    assert fila.ic95_superior == pytest.approx(4.4841377, abs=1e-6)


def test_ic_no_reemplaza_faltantes_por_cero_y_una_replica_no_da_ic():
    datos = datos_pareados([1., np.nan])
    fila = resumen_pareado(datos).iloc[0]
    assert fila.repeticiones == 2
    assert fila.pares_validos == 1 and fila.pares_faltantes == 1
    assert fila.diferencia_media == 1
    assert pd.isna(fila.ic95_inferior)
    with pytest.raises(ValueError, match="duplicadas"):
        resumen_pareado(pd.concat([datos, datos.iloc[:1]]))


def test_faltan_ambas_politicas_de_una_metrica_se_cuentan_como_par_faltante():
    datos = datos_pareados([1., 2., 3.])
    otra = datos.copy().assign(metrica="otra")
    datos = pd.concat([datos.loc[datos.semilla != 1], otra], ignore_index=True)
    fila = resumen_pareado(datos).set_index("metrica").loc["espera"]
    assert fila.repeticiones == 3
    assert fila.pares_faltantes == 1


def test_replicas_misma_configuracion_reproducibles_y_semillas_distintas():
    p = Parametros(pacientes=10, horas_turno=1)
    semillas = semillas_replicas(2, 42)
    assert semillas == [42, 43]
    primera = ejecutar_replicas(p, semillas)
    pd.testing.assert_frame_equal(primera, ejecutar_replicas(p, semillas))
    assert primera.escenario.eq("Configuración actual").all()
    assert primera.condicion.eq("Configurada").all()
    assert set(primera.semilla) == {42, 43}


def test_diagnosticos_son_reproducibles_y_comprueban_tiempos_reales_del_generador():
    a = diagnosticar_azar(42, 2000)
    pd.testing.assert_frame_equal(a, diagnosticar_azar(42, 2000))
    assert a.attrs["metadatos"]["generador"] == "PCG64"
    assert set(a.prueba) >= {"Uniformidad KS", "Autocorrelación lag 1", "Duración de consulta KS"}
    assert a.p_valor.dropna().between(0, 1).all()
    media = a.loc[a.prueba == "Media uniforme", "estadistico"].iloc[0]
    assert .47 < media < .53
    with pytest.raises(ValueError):
        diagnosticar_azar(42, 10)

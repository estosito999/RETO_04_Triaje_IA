from dataclasses import replace

import pandas as pd
import pytest

from analisis.metricas import comparar, espera_por_prioridad, resumir
from modelos.modelo_matematico import prioridad_asistida, prioridad_referencia
from modelos.variables import ALTA, BAJA, MEDIA, Parametros
from simulacion.escenarios import ESCENARIOS
from simulacion.generador_datos import PacienteSintetico, generar_pacientes
from simulacion.motor import _simular_estrategia, simular


@pytest.mark.parametrize("nombre", list(ESCENARIOS))
def test_balance_de_pacientes_y_limites_de_recursos_en_todo_evento(nombre):
    p = ESCENARIOS[nombre]
    exp = simular(p)
    columnas_pareadas = ["id_paciente", "llegada_min", "prioridad_referencia", "senal_a", "senal_b"]
    pd.testing.assert_frame_equal(exp.referencia.pacientes[columnas_pareadas], exp.asistido.pacientes[columnas_pareadas])
    for r in (exp.referencia, exp.asistido):
        assert r.eventos.minuto.is_monotonic_increasing
        assert r.eventos.minuto.between(0, p.turno_min, inclusive="left").all()
        assert r.cronologia.minuto.iloc[0] == 0
        assert r.cronologia.minuto.iloc[-1] == p.turno_min
        assert (r.cronologia >= 0).all().all()
        estados = ["cola_enfermeria", "enfermeros_ocupados", "cola_medica", "medicos_ocupados", "atendidos"]
        pd.testing.assert_series_equal(r.cronologia[estados].sum(axis=1), r.cronologia.llegados, check_names=False)
        assert r.cronologia.atendidos.iloc[-1] == (r.pacientes.estado == "atendido").sum()

        for recurso, comienzo, fin in (
            (p.enfermeros, "inicio_triaje", "fin_triaje"), (p.medicos, "inicio_consulta", "fin_consulta"),
        ):
            ocupados = r.eventos.evento.map({comienzo: 1, fin: -1}).fillna(0).cumsum()
            assert ocupados.between(0, recurso).all()

        for previo, siguiente in (
            ("llegada_min", "inicio_triaje_min"), ("inicio_triaje_min", "fin_triaje_min"),
            ("fin_triaje_min", "inicio_consulta_min"), ("inicio_consulta_min", "fin_consulta_min"),
            ("inicio_consulta_min", "tele_solicitada_min"), ("tele_solicitada_min", "tele_enviada_min"),
            ("tele_enviada_min", "tele_respondida_min"),
        ):
            pares = r.pacientes.loc[r.pacientes[siguiente].notna()]
            assert (pares[siguiente] >= pares[previo]).all()
        m = resumir(r, p)
        assert m["pacientes_atendidos"] <= m["pacientes_llegados"] <= p.pacientes
        assert 0 <= m["carga_medicos_pct"] <= 100
        assert 0 <= m["carga_enfermeros_pct"] <= 100
        assert m["teleconsultas_pendientes"] == r.cronologia.telependientes.iloc[-1]


def test_fifo_y_prioridades_se_aplican_solo_en_la_cola_medica_sin_interrumpir_consulta():
    p = Parametros(pacientes=3, enfermeros=1, medicos=1, horas_turno=1)
    cohorte = [
        PacienteSintetico(1, 1, MEDIA, 0.62, 0.62, 1, 12, False, 0, 0),
        PacienteSintetico(2, 3, BAJA, 0.2, 0.2, 1, 4, False, 0, 0),
        PacienteSintetico(3, 5, ALTA, 0.95, 0.95, 1, 4, False, 0, 0),
    ]
    fifo = _simular_estrategia(p, cohorte, asistido=False)
    asistido = _simular_estrategia(p, cohorte, asistido=True)
    inicios_fifo = fifo.eventos.loc[fifo.eventos.evento == "inicio_consulta", "id_paciente"]
    inicios_asistido = asistido.eventos.loc[asistido.eventos.evento == "inicio_consulta", "id_paciente"]
    assert inicios_fifo.to_list() == [1, 2, 3]
    assert inicios_asistido.to_list() == [1, 3, 2]
    assert asistido.pacientes.fin_consulta_min.iloc[0] == 14
    assert asistido.pacientes.inicio_consulta_min.iloc[2] == 14
    assert resumir(asistido, p)["carga_medicos_pct"] == pytest.approx(100 * 20 / 60)


def test_teleconsulta_sin_conexion_queda_pendiente_y_no_ocupa_el_recurso_local():
    p = replace(Parametros(), disponibilidad_conexion=0, respuesta_remota_min=0)
    sin_conexion = simular(p).asistido
    conectados = simular(replace(p, disponibilidad_conexion=1)).asistido
    assert sin_conexion.pacientes.tele_solicitada_min.notna().any()
    assert sin_conexion.pacientes.tele_enviada_min.isna().all()
    assert sin_conexion.pacientes.tele_respondida_min.isna().all()
    assert sin_conexion.cronologia.telependientes.iloc[-1] > 0
    pd.testing.assert_series_equal(conectados.pacientes.fin_consulta_min, sin_conexion.pacientes.fin_consulta_min)
    assert conectados.pacientes.tele_solicitada_min.equals(
        conectados.pacientes.tele_respondida_min.rename("tele_solicitada_min"),
    )
    assert conectados.cronologia.telependientes.iloc[-1] == 0


def test_pacientes_generados_despues_del_cierre_no_entran_en_el_denominador():
    p = Parametros(pacientes=500, llegadas_por_hora=1, horas_turno=1)
    exp = simular(p)
    tabla = exp.asistido.pacientes
    llegados = tabla.llegada_min < p.turno_min
    assert len(tabla) == p.pacientes
    assert llegados.sum() < p.pacientes
    assert (tabla.estado.loc[~llegados] == "no_llego").all()
    assert exp.asistido.cronologia.llegados.iloc[-1] == llegados.sum()
    assert comparar(exp).loc["Triaje asistido", "pacientes_llegados"] == llegados.sum()


def test_etiquetas_reglas_y_metricas_de_clasificacion_son_reproducibles():
    assert [prioridad_referencia(v) for v in (0.0, 0.55, 0.80)] == [BAJA, MEDIA, ALTA]
    assert [prioridad_asistida(v, v) for v in (0.2, 0.6, 0.9)] == [BAJA, MEDIA, ALTA]
    p = Parametros()
    exp = simular(p)
    repeticion = simular(p)
    pd.testing.assert_frame_equal(exp.asistido.pacientes, repeticion.asistido.pacientes)
    pd.testing.assert_frame_equal(exp.referencia.eventos, repeticion.referencia.eventos)
    pd.testing.assert_frame_equal(exp.asistido.cronologia, repeticion.asistido.cronologia)
    assert not exp.asistido.pacientes.equals(simular(replace(p, semilla=p.semilla + 1)).asistido.pacientes)
    m = comparar(exp)
    t = exp.asistido.pacientes.dropna(subset=["prioridad_asignada"])
    assert m.loc["Triaje asistido", "errores_subtriaje"] == (t.prioridad_asignada > t.prioridad_referencia).sum()
    assert m.loc["Triaje asistido", "concordancia_pct"] == pytest.approx(100 * (t.prioridad_asignada == t.prioridad_referencia).mean())
    assert pd.isna(m.loc["FIFO", "concordancia_pct"])
    assert espera_por_prioridad(exp).pacientes.sum() == sum(
        r.pacientes.inicio_consulta_min.notna().sum() for r in (exp.referencia, exp.asistido)
    )


def test_controles_de_llegadas_y_prioridades_modifican_la_cohorte_sintetica():
    p = Parametros(pacientes=30, llegadas_por_hora=10, proporcion_prioritarios=0)
    base = generar_pacientes(p)
    alta_demanda = generar_pacientes(replace(p, llegadas_por_hora=20, proporcion_prioritarios=1))
    assert alta_demanda[-1].llegada_min == pytest.approx(base[-1].llegada_min / 2)
    assert all(paciente.prioridad_referencia == BAJA for paciente in base)
    assert all(paciente.prioridad_referencia in (ALTA, MEDIA) for paciente in alta_demanda)


@pytest.mark.parametrize("cambio", [
    {"semilla": -1}, {"pacientes": 0}, {"medicos": 0}, {"enfermeros": 17},
    {"disponibilidad_conexion": 1.1}, {"llegadas_por_hora": float("nan")},
])
def test_rechaza_parametros_invalidos(cambio):
    with pytest.raises(ValueError):
        Parametros(**cambio)

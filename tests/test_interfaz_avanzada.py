from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
from streamlit.testing.v1 import AppTest

import interfaz.exportacion as exportacion
from interfaz.visualizaciones import vista_turno
from modelos.variables import ALTA, BAJA, Parametros
from simulacion.escenarios import PARAMETROS_LABORATORIO, REPETICIONES_LABORATORIO
from simulacion.generador_datos import PacienteSintetico
from simulacion.motor import _simular_estrategia, simular


APP = Path(__file__).resolve().parents[1] / "main.py"


def test_sesion_con_ajuste_anterior_vuelve_a_condiciones_fijas():
    anteriores = replace(PARAMETROS_LABORATORIO, horas_turno=8, perfil_llegadas=(),
                         llegadas_por_hora=12, medicos=4, pacientes=20, seguimiento_min=30)
    app = AppTest.from_file(APP, default_timeout=60)
    app.session_state.modo = "Laboratorio"
    app.session_state.experimento = simular(anteriores)
    app.session_state.configuracion_calibrada = anteriores
    app.session_state.calibracion_aplicada = (anteriores, None)
    app.session_state.seleccionar_ajuste = True
    app.session_state.paso = 10
    app.session_state.reproduciendo = True
    app.session_state.proximo_paso = 0.0
    app.run()
    assert not app.exception
    assert app.session_state.experimento.parametros == PARAMETROS_LABORATORIO
    assert app.session_state.paso == 0
    assert not app.session_state.reproduciendo
    assert not app.file_uploader


def test_nueva_jornada_conserva_condiciones_y_renueva_azar_y_exportacion(monkeypatch):
    archivos = []

    def capturar_zip(memoria, *args, **kwargs):
        archivos.append(memoria)
        return ZipFile(memoria, *args, **kwargs)

    monkeypatch.setattr(exportacion, "ZipFile", capturar_zip)
    app = AppTest.from_file(APP, default_timeout=60)
    app.session_state.modo = "Laboratorio"
    app.run()
    assert not app.exception
    original = app.session_state.experimento
    app.button(key="ejecutar_replicas").click().run()
    assert not app.exception
    parametros, datos, resumen = app.session_state.replicas_resultado
    assert parametros == PARAMETROS_LABORATORIO
    assert datos.semilla.nunique() == REPETICIONES_LABORATORIO == 30
    assert resumen.repeticiones.eq(30).all()
    jornadas = next(tabla.value for tabla in app.dataframe
                    if {"Réplica", "Semilla", "Política"}.issubset(tabla.value.columns))
    assert len(jornadas) == 60
    assert jornadas.Semilla.nunique() == 30
    assert set(jornadas["Política"]) == {"FIFO", "Triaje asistido"}
    assert jornadas["Pacientes ingresados"].le(100).all()
    with ZipFile(BytesIO(archivos[-1].getvalue())) as archivo:
        assert "jornadas.csv" in archivo.namelist()
        assert {"frecuencias_interarribos.csv", "frecuencias_servicio.csv"}.issubset(archivo.namelist())
    app.button(key="validar_azar").click().run()
    assert not app.exception
    assert not app.session_state.diagnostico_azar[1].empty
    descarga = next(b for b in app.download_button if b.label == "Descargar resultados (ZIP)")
    descarga.click().run()
    assert not app.exception
    assert app.session_state.experimento is original
    assert app.session_state.experimento.parametros == PARAMETROS_LABORATORIO

    app.button(key="avanzar").click().run()
    assert not app.exception
    assert app.session_state.paso == 1
    ordinal = app.session_state.jornada_laboratorio
    app.button(key="nueva_jornada").click().run()
    assert not app.exception
    actual = app.session_state.experimento
    semilla = app.session_state.semilla_laboratorio
    assert 0 <= semilla < 2**32
    assert semilla != original.parametros.semilla
    assert actual.parametros == replace(PARAMETROS_LABORATORIO, semilla=semilla)
    assert app.session_state.jornada_laboratorio == ordinal + 1
    assert not actual.asistido.pacientes.llegada_min.equals(original.asistido.pacientes.llegada_min)
    assert app.session_state.paso == 0
    assert not app.session_state.reproduciendo
    assert app.session_state.get("replicas_resultado") is None
    assert app.session_state.get("diagnostico_azar") is None
    with ZipFile(BytesIO(archivos[-1].getvalue())) as archivo:
        parametros_exportados = json.loads(archivo.read("parametros.json"))
        assert parametros_exportados["semilla"] == semilla
    repetida = simular(actual.parametros)
    pd.testing.assert_frame_equal(actual.asistido.pacientes, repetida.asistido.pacientes)

    app.radio(key="politica_simulacion").set_value("FIFO").run()
    assert not app.exception
    app.button(key="avanzar").click().run()
    assert not app.exception
    assert app.session_state.experimento is actual
    assert app.session_state.semilla_laboratorio == semilla

    app.button(key="ejecutar_replicas").click().run()
    assert not app.exception
    nuevos_parametros, nuevos_datos, nuevo_resumen = app.session_state.replicas_resultado
    assert nuevos_parametros == actual.parametros
    assert nuevos_datos.semilla.nunique() == 30
    assert nuevo_resumen.repeticiones.eq(30).all()
    assert set(nuevos_datos.semilla) != set(datos.semilla)
    assert not nuevos_datos.valor.equals(datos.valor)


def test_reproduccion_no_muestra_reevaluacion_futura():
    p = Parametros(pacientes=2, horas_turno=1, medicos=1, enfermeros=1, deterioro_cada_min=10)
    cohorte = [
        PacienteSintetico(1, 1, ALTA, .95, .95, 1, 30, False, 0, 0),
        PacienteSintetico(2, 3, BAJA, .1, .1, 1, 3, False, 0, 0),
    ]
    resultado = _simular_estrategia(p, cohorte, True)
    for minuto, etiqueta in ((9, "Baja (3)"), (15, "Media (2)"), (25, "Alta (1)")):
        figura = vista_turno(resultado.pacientes, minuto, asistido=True, eventos=resultado.eventos)
        traza = next(t for t in figura.data if t.name == etiqueta)
        assert "2" in list(traza.text)

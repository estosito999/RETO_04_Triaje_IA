from pathlib import Path

from streamlit.testing.v1 import AppTest

from interfaz.visualizaciones import vista_turno
from modelos.variables import ALTA, BAJA, Parametros
from simulacion.generador_datos import PacienteSintetico
from simulacion.motor import _simular_estrategia


APP = Path(__file__).resolve().parents[1] / "main.py"


def test_configuracion_invalida_se_recupera_y_cohorte_vacia_se_visualiza():
    app = AppTest.from_file(APP, default_timeout=60).run()
    original = app.session_state.experimento
    app.text_input(key="perfil_Turno habitual").set_value("1, 2")
    next(b for b in app.button if b.label == "Preparar experimento").click().run()
    assert not app.exception
    assert app.error
    assert app.session_state.experimento == original
    app.text_input(key="perfil_Turno habitual").set_value("0,0,0,0,0,0,0,0")
    app.checkbox(key="continuas_Turno habitual").set_value(True)
    app.checkbox(key="compartida_Turno habitual").set_value(True)
    app.number_input(key="seguimiento_Turno habitual").set_value(30.0)
    next(b for b in app.button if b.label == "Preparar experimento").click().run()
    assert not app.exception
    assert app.session_state.experimento.asistido.pacientes.empty
    assert app.session_state.experimento.asistido.cronologia.minuto.iloc[-1] == 510
    assert len(app.get("plotly_chart")) == 3


def test_repeticiones_diagnosticos_y_ajuste_desde_la_interfaz():
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.number_input(key="cantidad_replicas").set_value(2)
    app.button(key="ejecutar_replicas").click().run()
    assert not app.exception
    _, datos, resumen = app.session_state.replicas_resultado
    assert datos.semilla.nunique() == 2
    assert resumen.pares_validos.max() == 2
    app.button(key="validar_azar").click().run()
    assert not app.exception
    assert not app.session_state.diagnostico_azar[1].empty
    csv = ("llegada_min,duracion_triaje_min,duracion_consulta_min,prioridad_referencia\n"
           "10,3,14,1\n70,5,18,1\n130,3,13,2\n190,5,15,2\n250,3,12,3\n310,5,20,3\n")
    app.file_uploader(key="datos_calibracion").upload("turno.csv", csv.encode())
    app.button(key="ajustar_datos").click().run()
    assert not app.exception
    assert app.session_state.ajuste_preparado[1].llegadas_por_hora == .75
    app.button(key="aplicar_ajuste").click().run()
    assert not app.exception
    assert app.session_state.experimento.parametros.llegadas_por_hora == .75
    assert app.selectbox(key="escenario").value == "Datos ajustados"
    assert app.number_input(key="llegadas_Datos ajustados").value == .75


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

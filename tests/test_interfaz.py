from pathlib import Path

from streamlit.testing.v1 import AppTest

from simulacion.escenarios import PARAMETROS_LABORATORIO


APP = Path(__file__).resolve().parents[1] / "main.py"


def test_laboratorio_muestra_condiciones_fijas_sin_controles_de_parametros():
    app = AppTest.from_file(APP, default_timeout=45)
    app.session_state.modo = "Laboratorio"
    app.run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == [
        "A · Introducción", "B · Condiciones fijas", "C · Simulación",
        "D · Análisis", "E · Conclusiones",
    ]
    assert not app.sidebar.children
    for tipo in ("number_input", "slider", "selectbox", "text_input", "checkbox", "file_uploader"):
        assert not app.get(tipo)
    assert not any(b.label == "Preparar experimento" for b in app.button)

    exp = app.session_state.experimento
    assert exp.parametros == PARAMETROS_LABORATORIO
    assert app.session_state.semilla_laboratorio == exp.parametros.semilla
    assert len(exp.asistido.pacientes) == 100
    assert not exp.parametros.generar_hasta_cierre
    for resultado in (exp.referencia, exp.asistido):
        llegadas = resultado.eventos.loc[resultado.eventos.evento == "llegada", "minuto"]
        assert len(llegadas) <= 100
        assert llegadas.lt(1440).all()
        assert llegadas.diff().dropna().between(1, 5).all()
        assert resultado.cronologia.cola_medica.max() > 0
    frecuencias = [tabla.value for tabla in app.table if "Frecuencia" in tabla.value.columns]
    assert len(frecuencias) == 2
    assert all(tabla.Frecuencia.sum() == 50 and tabla.Acumulada.iloc[-1] == 1 for tabla in frecuencias)


def test_reproduccion_y_politica_no_cambian_el_experimento_fijo():
    app = AppTest.from_file(APP, default_timeout=45)
    app.session_state.modo = "Laboratorio"
    app.run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 3
    original = app.session_state.experimento
    semilla = app.session_state.semilla_laboratorio
    assert app.session_state.paso == 0
    app.button(key="avanzar").click().run()
    assert not app.exception
    assert app.session_state.paso == 1
    app.button(key="iniciar").click().run()
    assert not app.exception
    assert app.session_state.reproduciendo
    app.button(key="pausar").click().run()
    assert not app.exception
    assert not app.session_state.reproduciendo
    app.select_slider(key="velocidad").set_value(2.0).run()
    assert not app.exception
    politica = next(widget for widget in app.radio if widget.label == "Política en pantalla")
    politica.set_value("FIFO").run()
    assert not app.exception
    assert app.session_state.experimento is original
    assert app.session_state.semilla_laboratorio == semilla
    assert original.parametros == PARAMETROS_LABORATORIO
    app.button(key="reiniciar").click().run()
    assert not app.exception
    assert app.session_state.paso == 0

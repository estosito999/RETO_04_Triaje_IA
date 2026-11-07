from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_panel_y_reproduccion():
    app = AppTest.from_file(Path(__file__).resolve().parents[1] / "main.py", default_timeout=45).run()
    app.segmented_control(key="modo").set_value("Laboratorio").run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 3
    assert app.session_state.paso == 0
    app.button(key="avanzar").click().run()
    assert app.session_state.paso == 1
    app.button(key="iniciar").click().run()
    assert app.session_state.reproduciendo
    app.button(key="pausar").click().run()
    assert not app.session_state.reproduciendo
    app.button(key="reiniciar").click().run()
    assert app.session_state.paso == 0

    conexion = next(widget for widget in app.slider if widget.label == "Disponibilidad de conexión (%)")
    conexion.set_value(0)
    reintento = next(widget for widget in app.number_input if widget.label == "Intervalo de reintento de envío (min)")
    reintento.set_value(3.0)
    preparar = next(widget for widget in app.button if widget.label == "Preparar experimento")
    preparar.click().run()
    assert not app.exception
    exp = app.session_state.experimento
    assert exp.parametros.disponibilidad_conexion == 0
    assert exp.parametros.intervalo_reintento_min == 3.0
    assert exp.asistido.pacientes.tele_enviada_min.isna().all()
    assert exp.asistido.pacientes.intentos_envio.max() > 1

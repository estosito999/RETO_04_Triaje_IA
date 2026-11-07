from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

from streamlit.testing.v1 import AppTest

from analisis.evidencia_pitch import generar_evidencia, resumir_evidencia
from interfaz.pitch import CAPITULOS, _paquete
from modelos.variables import Parametros


APP = Path(__file__).resolve().parents[1] / "main.py"


def test_pitch_abre_y_se_navega_sin_perder_el_laboratorio():
    app = AppTest.from_file(APP, default_timeout=60).run()
    assert not app.exception
    assert app.segmented_control(key="modo").value == "Pitch"
    assert len(CAPITULOS) == 5
    assert app.segmented_control(key="pitch_capitulo").value == CAPITULOS[0]
    assert app.button(key="pitch_anterior").disabled
    app.button(key="pitch_siguiente").click().run()
    assert not app.exception
    assert app.segmented_control(key="pitch_capitulo").value == CAPITULOS[1]
    app.segmented_control(key="pitch_capitulo").set_value(CAPITULOS[2]).run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 2
    app.slider(key="pitch_conexion_Sobrecarga de llegadas").set_value(0).run()
    assert not app.exception
    app.segmented_control(key="pitch_capitulo").set_value(CAPITULOS[3]).run()
    assert not app.exception
    assert any(m.value == "Bs 14,272" for m in app.metric)
    app.checkbox(key="pitch_fin_reutilizar").set_value(False).run()
    assert not app.exception
    assert any(m.value == "Bs 18,297" for m in app.metric)
    app.button(key="pitch_siguiente").click().run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 1
    assert any("incluye cero" in item.value for item in app.markdown)
    assert app.button(key="pitch_siguiente").disabled
    app.segmented_control(key="modo").set_value("Laboratorio").run()
    assert not app.exception
    p = app.session_state.experimento.parametros
    app.segmented_control(key="modo").set_value("Pitch").run()
    app.segmented_control(key="modo").set_value("Laboratorio").run()
    assert not app.exception
    assert app.session_state.experimento.parametros == p


def test_descarga_de_evidencia_incluye_semillas_parametros_y_pares():
    p = Parametros(pacientes=8, horas_turno=1)
    datos, diferencias = generar_evidencia(p, 2)
    tabla = resumir_evidencia(datos, diferencias)
    with ZipFile(BytesIO(_paquete(datos, diferencias, tabla))) as archivo:
        assert set(archivo.namelist()) == {"mediciones.csv", "diferencias.csv", "resumen.csv", "metadatos.json", "LEEME.txt"}
        metadata = json.loads(archivo.read("metadatos.json"))
        assert metadata["semillas"] == [42, 43]
        assert metadata["horizonte_principal_min"] == 60
        assert metadata["parametros"]["pacientes"] == 8

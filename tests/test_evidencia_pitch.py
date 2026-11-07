import numpy as np
import pandas as pd
import pytest

from analisis.evidencia_pitch import METRICAS_PITCH, generar_evidencia, resumir_evidencia
from analisis.experimentos import resumen_pareado
from modelos.variables import Parametros


def mediciones(metrica, fifo, asistido):
    return pd.DataFrame([{
        "escenario": "Caso", "condicion": "Configurada", "semilla": i,
        "estrategia": estrategia, "metrica": metrica, "valor": valor,
    } for i, (a, b) in enumerate(zip(fifo, asistido))
      for estrategia, valor in (("FIFO", a), ("Triaje asistido", b))])


def test_evidencia_real_conserva_plan_semillas_politicas_y_clasificacion_solo_asistida():
    p = Parametros(semilla=123, pacientes=15, horas_turno=1)
    datos, diferencias = generar_evidencia(p, 2)
    assert set(datos.semilla) == {123, 124}
    assert set(datos.estrategia) == {"FIFO", "Triaje asistido"}
    assert set(datos.metrica) == set(METRICAS_PITCH)
    assert datos.attrs["metadatos"]["horizonte_principal_min"] == 60
    assert datos.attrs["metadatos"]["repeticiones_planificadas"] == 2
    llegados = datos.loc[datos.metrica == "pacientes_llegados_al_cierre"].pivot(
        index="semilla", columns="estrategia", values="valor")
    pd.testing.assert_series_equal(llegados.FIFO, llegados["Triaje asistido"], check_names=False)
    tabla = resumir_evidencia(datos, diferencias).set_index("metrica")
    assert tabla.loc["pacientes_llegados_al_cierre", "diferencia_media"] == 0
    assert tabla.loc["sensibilidad_alta_pct_al_cierre", "fifo_repeticiones_observadas"] == 0
    assert pd.isna(tabla.loc["sensibilidad_alta_pct_al_cierre", "fifo_media"])


def test_sin_pacientes_altos_no_se_inventa_espera_cero_ni_sensibilidad():
    p = Parametros(pacientes=15, horas_turno=1, proporcion_prioritarios=0)
    datos, diferencias = generar_evidencia(p, 2)
    tabla = resumir_evidencia(datos, diferencias).set_index("metrica")
    for metrica in ("espera_medica_alta_min_al_cierre", "sensibilidad_alta_pct_al_cierre"):
        assert pd.isna(tabla.loc[metrica, "asistido_media"])
        assert tabla.loc[metrica, "asistido_repeticiones_observadas"] == 0
        assert tabla.loc[metrica, "pares_validos"] == 0
        assert pd.isna(tabla.loc[metrica, "ic95_inferior"])


def test_medias_descriptivas_y_diferencia_pareada_no_mezclan_denominadores():
    datos = mediciones("espera_medica_alta_min_al_cierre", [10, np.nan], [8, 100])
    fila = resumir_evidencia(datos).iloc[0]
    assert fila.fifo_media == 10
    assert fila.asistido_media == 54
    assert fila.fifo_repeticiones_observadas == 1
    assert fila.asistido_repeticiones_observadas == 2
    assert fila.diferencia_media == -2  # Un solo par completo, no 54 - 10.
    assert fila.pares_validos == 1 and fila.pares_faltantes == 1
    assert pd.isna(fila.ic95_inferior)


def test_porcentajes_son_medias_por_turno_y_fifo_sin_clasificar_permanece_ausente():
    datos = mediciones("sensibilidad_alta_pct_al_cierre", [np.nan, np.nan], [100, 0])
    fila = resumir_evidencia(datos).iloc[0]
    assert fila.asistido_media == 50
    assert fila.unidad == "% por turno"
    assert pd.isna(fila.fifo_media) and pd.isna(fila.diferencia_media)
    assert fila.pares_validos == 0


def test_rechaza_resumen_incompatible_y_mezcla_de_escenarios():
    datos = mediciones("pacientes_atendidos_al_cierre", [10, 10], [11, 12])
    incorrecto = resumen_pareado(datos)
    incorrecto["diferencia_media"] = 100
    with pytest.raises(ValueError, match="no corresponden"):
        resumir_evidencia(datos, incorrecto)
    with pytest.raises(ValueError, match="un solo escenario"):
        resumir_evidencia(pd.concat([datos, datos.assign(escenario="Otro")]))


def test_evidencia_no_depende_de_csv_guardado_y_una_replica_no_da_ic(monkeypatch):
    def no_leer(*args, **kwargs):
        raise AssertionError("La evidencia no debe leer archivos CSV.")
    monkeypatch.setattr(pd, "read_csv", no_leer)
    datos, diferencias = generar_evidencia(Parametros(pacientes=5, horas_turno=1), 1)
    tabla = resumir_evidencia(datos, diferencias)
    assert tabla.ic95_inferior.isna().all()
    assert tabla.ic95_superior.isna().all()
    with pytest.raises(ValueError):
        generar_evidencia(Parametros(), 0)

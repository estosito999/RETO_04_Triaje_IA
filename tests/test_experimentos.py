from dataclasses import replace
import json

import pandas as pd
import pytest

import analisis.experimentos as protocolo


def test_protocolo_reproduce_condiciones_y_registra_parametros(monkeypatch):
    base = replace(next(iter(protocolo.ESCENARIOS.values())), horas_turno=1, pacientes=20)
    monkeypatch.setattr(protocolo, "ESCENARIOS", {"Prueba": base})
    primera = protocolo.ejecutar_experimentos([42])
    repetida = protocolo.ejecutar_experimentos([42])
    pd.testing.assert_frame_equal(primera, repetida)
    assert primera.condicion.nunique() == 2
    assert primera.estrategia.nunique() == 2
    assert primera.escenario.eq("Prueba").all()
    assert primera.semilla.eq(42).all()
    assert all(json.loads(p)["semilla"] == 42 for p in primera.parametros_json)


@pytest.mark.parametrize("semillas", [[], [42, 42], [-1]])
def test_protocolo_rechaza_semillas_invalidas(semillas):
    with pytest.raises(ValueError):
        protocolo.ejecutar_experimentos(semillas)

from dataclasses import replace

import numpy as np
import pytest

from analisis.viabilidad import PresupuestoPiloto, desglose_presupuesto, escenarios_escala, evaluar_presupuesto


def test_presupuesto_base_expone_costos_y_no_estima_retorno():
    r = evaluar_presupuesto(PresupuestoPiloto())
    # 80h×80 + (12h×80 + 16h×100 + 4h×80) = 9280 Bs.
    assert r["inversion_base_bs"] == 9280
    assert r["contingencia_bs"] == 1392
    assert r["inversion_inicial_bs"] == 10672
    assert r["operacion_mensual_bs"] == 300
    assert r["total_horizonte_bs"] == r["costo_por_centro_bs"] == 14272
    assert r["equipo_por_centro_bs"] == 0
    assert r["moneda"] == "BOB"
    assert "retorno" not in r and "ahorro" not in r
    assert any("ilustrativos" in nota for nota in r["notas"])


def test_compra_equipo_se_repite_por_centro_y_contingencia_solo_inversion():
    base = PresupuestoPiloto(centros=3, meses=6)
    reuso = evaluar_presupuesto(base)
    compra = evaluar_presupuesto(replace(base, reutilizar_equipo=False))
    assert compra["inversion_base_bs"]-reuso["inversion_base_bs"] == 3*3500
    assert compra["inversion_inicial_bs"]-reuso["inversion_inicial_bs"] == pytest.approx(3*3500*1.15)
    assert compra["operacion_mensual_bs"] == reuso["operacion_mensual_bs"] == 500
    assert compra["operacion_total_horizonte_bs"] == 3000


def test_horizonte_modifica_solo_operacion_y_sin_contingencia_opex():
    p = PresupuestoPiloto(contingencia_pct=25)
    uno = evaluar_presupuesto(replace(p, meses=1))
    doce = evaluar_presupuesto(p)
    assert uno["inversion_inicial_bs"] == doce["inversion_inicial_bs"]
    assert doce["total_horizonte_bs"]-uno["total_horizonte_bs"] == 11*300
    assert doce["contingencia_bs"] == doce["inversion_base_bs"]*.25


def test_desglose_suma_total_y_prorrateo_conserva_costos():
    p = PresupuestoPiloto(centros=5, meses=9, reutilizar_equipo=False)
    r = evaluar_presupuesto(p)
    desglose = desglose_presupuesto(p)
    assert len(desglose) == 8
    assert desglose.importe_bs.sum() == pytest.approx(r["total_horizonte_bs"])
    assert r["costo_por_centro_bs"]*5 == pytest.approx(r["total_horizonte_bs"])
    assert desglose.attrs["metadatos"]["supuestos"]["meses"] == 9


def test_escala_conserva_costos_centrales_y_horizonte():
    p = PresupuestoPiloto(meses=6)
    tabla = escenarios_escala(p, centros=(1, 3, 5, 10))
    assert tabla.centros.tolist() == [1, 3, 5, 10]
    assert tabla.meses.eq(6).all()
    for fila in tabla.to_dict("records"):
        r = evaluar_presupuesto(replace(p, centros=fila["centros"]))
        assert fila["total_horizonte_bs"] == r["total_horizonte_bs"]
        assert fila["costo_por_centro_bs"] == r["total_horizonte_bs"]/fila["centros"]
    assert tabla.total_horizonte_bs.is_monotonic_increasing
    assert tabla.costo_por_centro_bs.is_monotonic_decreasing


@pytest.mark.parametrize("cambio", [
    {"centros": 0}, {"centros": True}, {"centros": 1.0}, {"meses": -1}, {"meses": False},
    {"horas_desarrollo": -1}, {"tarifa_tecnica_bs": np.inf}, {"contingencia_pct": np.nan},
    {"tarifa_revision_bs": True}, {"equipo_por_centro_bs": "3500"}, {"reutilizar_equipo": 1},
])
def test_validacion_rechaza_supuestos_invalidos(cambio):
    with pytest.raises(ValueError):
        PresupuestoPiloto(**cambio)


def test_permite_costos_cero_y_rechaza_desbordamiento_y_escala_vacia():
    p = PresupuestoPiloto(horas_desarrollo=0, horas_datos_por_centro=0, horas_revision_por_centro=0,
                         horas_capacitacion_por_centro=0, operacion_fija_mensual_bs=0,
                         operacion_por_centro_mensual_bs=0)
    assert evaluar_presupuesto(p)["total_horizonte_bs"] == 0
    with pytest.raises(ValueError, match="rango numérico"):
        evaluar_presupuesto(PresupuestoPiloto(horas_desarrollo=1e308, tarifa_tecnica_bs=1e308))
    with pytest.raises(ValueError):
        escenarios_escala(PresupuestoPiloto(), centros=())

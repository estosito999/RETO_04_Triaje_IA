from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from modelos.modelo_matematico import prioridad_asistida
from modelos.variables import ALTA, BAJA, MEDIA, Parametros
from simulacion.generador_datos import (
    PacienteSintetico, TrayectoriaConexion, generar_pacientes, generar_trayectoria_conexion,
)
import simulacion.motor as motor


def paciente(numero, llegada=1, prioridad=BAJA, triaje=1, consulta=4, tele=False, demora=10):
    senal = {ALTA: .95, MEDIA: .62, BAJA: .2}[prioridad]
    return PacienteSintetico(numero, llegada, prioridad, senal, senal, triaje, consulta, tele, .1, demora)


def test_llegadas_por_horas_sin_cupo_respetan_horas_sin_demanda():
    p = Parametros(pacientes=1, horas_turno=3, llegadas_por_hora=60,
                   perfil_llegadas=(0, 2, 0), generar_hasta_cierre=True)
    cohorte = generar_pacientes(p)
    assert len(cohorte) > p.pacientes
    assert all(60 <= caso.llegada_min < 120 for caso in cohorte)
    assert cohorte == generar_pacientes(replace(p, pacientes=500))
    resultados = motor.simular(p)
    for resultado in (resultados.referencia, resultados.asistido):
        assert resultado.cronologia.llegados.iloc[-1] == len(cohorte)


def test_perfil_totalmente_vacio_no_fabrica_pacientes_y_conserva_tablas_utilizables():
    p = Parametros(horas_turno=1, perfil_llegadas=(0,), generar_hasta_cierre=True)
    exp = motor.simular(p)
    assert exp.asistido.pacientes.empty
    assert "inicio_consulta_min" in exp.asistido.pacientes
    assert exp.asistido.eventos.empty
    assert exp.asistido.cronologia.llegados.eq(0).all()
    assert exp.asistido.cronologia.minuto.iloc[-1] == 60


def test_medias_de_servicio_por_prioridad_cambian_solo_duraciones():
    base = Parametros(pacientes=500)
    original = generar_pacientes(base)
    nuevo = generar_pacientes(replace(base, triaje_medio_min=8,
                                     medias_consulta_prioridad=(32, 16, 8)))
    assert set(caso.prioridad_referencia for caso in original) == {ALTA, MEDIA, BAJA}
    for antes, despues in zip(original, nuevo):
        assert antes.llegada_min == despues.llegada_min
        assert antes.senal_a == despues.senal_a
        assert despues.duracion_triaje_min == pytest.approx(2 * antes.duracion_triaje_min)
        escala = {ALTA: 2, MEDIA: 1, BAJA: .5}[antes.prioridad_referencia]
        assert despues.duracion_consulta_min == pytest.approx(escala * antes.duracion_consulta_min)


def test_clasificador_acepta_parametros_y_conserva_interfaz_original():
    assert prioridad_asistida(.9, .1) == MEDIA
    assert prioridad_asistida(.9, .1, Parametros(peso_senal_a=1)) == ALTA
    assert prioridad_asistida(.9, .1, peso_senal_a=0) == BAJA


def test_fraccion_alta_prioritarios_separa_clases_y_conserva_el_predeterminado():
    base = Parametros(pacientes=100, proporcion_prioritarios=1)
    assert base.fraccion_alta_prioritarios == .4
    assert generar_pacientes(base) == generar_pacientes(replace(base, fraccion_alta_prioritarios=.4))
    solo_altas = generar_pacientes(replace(base, fraccion_alta_prioritarios=1))
    solo_medias = generar_pacientes(replace(base, fraccion_alta_prioritarios=0))
    assert all(caso.prioridad_referencia == ALTA for caso in solo_altas)
    assert all(caso.prioridad_referencia == MEDIA for caso in solo_medias)
    assert [caso.llegada_min for caso in solo_altas] == [caso.llegada_min for caso in solo_medias]


@pytest.mark.parametrize("disponibilidad", [0, 1])
def test_conexion_compartida_extremos_exactos(disponibilidad):
    p = Parametros(disponibilidad_conexion=disponibilidad, conexion_compartida=True)
    trayectoria = generar_trayectoria_conexion(p)
    assert len(trayectoria.tiempos) == 1
    assert all(trayectoria.conectada(t) == bool(disponibilidad) for t in (0, 1, 100, p.horizonte_min))


def test_conexion_global_reproducible_no_depende_de_recursos_ni_politica():
    p = Parametros(disponibilidad_conexion=.4, conexion_compartida=True,
                   persistencia_conexion_min=5, seguimiento_min=30)
    a = generar_trayectoria_conexion(p)
    b = generar_trayectoria_conexion(replace(p, medicos=8, pacientes=5, especialistas_remotos=2))
    np.testing.assert_array_equal(a.tiempos, b.tiempos)
    np.testing.assert_array_equal(a.estados, b.estados)
    assert len(a.tiempos) > 2
    assert np.all(a.estados[1:] != a.estados[:-1])


def test_corte_compartido_afecta_todos_los_envios_simultaneos(monkeypatch):
    p = Parametros(pacientes=2, medicos=2, enfermeros=2, horas_turno=1,
                   disponibilidad_conexion=.5, conexion_compartida=True)
    trayectoria = TrayectoriaConexion(np.array([0., 12.]), np.array([False, True]))
    monkeypatch.setattr(motor, "generar_trayectoria_conexion", lambda _: trayectoria)
    # Los sorteos individuales dirían conexión inmediata; el corte del centro manda.
    cohorte = [paciente(1, tele=True), paciente(2, tele=True)]
    for asistido in (False, True):
        resultado = motor._simular_estrategia(p, cohorte, asistido)
        assert resultado.pacientes.tele_solicitada_min.eq(2).all()
        assert resultado.pacientes.tele_enviada_min.eq(12).all()
        assert resultado.pacientes.intentos_envio.eq(3).all()


def test_especialista_unico_serializa_respuestas_sin_bloquear_consulta_por_defecto():
    p = Parametros(pacientes=2, medicos=2, enfermeros=2, horas_turno=1,
                   especialistas_remotos=1, disponibilidad_conexion=1)
    cohorte = [paciente(1, tele=True), paciente(2, tele=True)]
    r = motor._simular_estrategia(p, cohorte, asistido=True)
    assert sorted(r.pacientes.tele_respondida_min) == [12, 22]
    assert sorted(r.pacientes.inicio_atencion_remota_min) == [2, 12]
    assert r.pacientes.fin_consulta_min.eq(6).all()
    paralelo = motor._simular_estrategia(replace(p, especialistas_remotos=0), cohorte, asistido=True)
    assert paralelo.pacientes.tele_respondida_min.eq(12).all()


def test_esperar_respuesta_retiene_medico_y_sin_respuesta_permanece_ocupado():
    p = Parametros(pacientes=2, medicos=1, enfermeros=2, horas_turno=1,
                   disponibilidad_conexion=1, esperar_teleconsulta=True)
    cohorte = [paciente(1, consulta=2, tele=True), paciente(2, llegada=2)]
    r = motor._simular_estrategia(p, cohorte, asistido=True)
    assert r.pacientes.fin_servicio_local_min.iloc[0] == 4
    assert r.pacientes.fin_consulta_min.iloc[0] == 12
    assert r.pacientes.inicio_consulta_min.iloc[1] == 12
    bloqueado = motor._simular_estrategia(replace(p, disponibilidad_conexion=0), cohorte, asistido=True)
    assert pd.isna(bloqueado.pacientes.fin_consulta_min.iloc[0])
    assert pd.isna(bloqueado.pacientes.inicio_consulta_min.iloc[1])
    assert bloqueado.cronologia.medicos_ocupados.iloc[-1] == 1
    assert bloqueado.cronologia.telependientes.iloc[-1] == 1


def test_seguimiento_termina_consultas_y_respuestas_sin_admitir_llegadas_tardias():
    p = Parametros(pacientes=2, horas_turno=1, seguimiento_min=15.5,
                   disponibilidad_conexion=1)
    cohorte = [paciente(1, llegada=58, consulta=4, tele=True), paciente(2, llegada=61)]
    r = motor._simular_estrategia(p, cohorte, asistido=True)
    assert r.horizonte_min == 75.5
    assert r.cronologia.minuto.iloc[-1] == 75.5
    assert r.pacientes.fin_consulta_min.iloc[0] == 63
    assert r.pacientes.tele_respondida_min.iloc[0] == 69
    assert r.pacientes.estado.iloc[1] == "no_llego"
    assert r.cronologia.set_index("minuto").loc[60, "atendidos"] == 0
    assert r.cronologia.atendidos.iloc[-1] == 1
    assert motor.Resultado(r.pacientes, r.eventos, r.cronologia).horizonte_min is None


def test_deterioro_reordena_sin_interrumpir_y_conserva_etiquetas_iniciales():
    p = Parametros(pacientes=3, enfermeros=1, medicos=1, horas_turno=1)
    cohorte = [paciente(1, prioridad=MEDIA, consulta=20),
               paciente(2, llegada=2), paciente(3, llegada=10, prioridad=ALTA)]
    base = motor._simular_estrategia(p, cohorte, asistido=True)
    nuevo = motor._simular_estrategia(replace(p, deterioro_cada_min=5), cohorte, asistido=True)
    assert base.eventos.loc[base.eventos.evento.eq("inicio_consulta"), "id_paciente"].tolist() == [1, 3, 2]
    assert nuevo.eventos.loc[nuevo.eventos.evento.eq("inicio_consulta"), "id_paciente"].tolist() == [1, 2, 3]
    fila = nuevo.pacientes.iloc[1]
    assert fila.prioridad_referencia == fila.prioridad_asignada == BAJA
    assert fila.prioridad_actual == ALTA
    assert fila.reevaluaciones == 2
    assert nuevo.pacientes.fin_consulta_min.iloc[0] == base.pacientes.fin_consulta_min.iloc[0] == 22
    cambios = nuevo.eventos.loc[nuevo.eventos.evento.eq("reevaluacion")]
    assert cambios.minuto.tolist() == [8, 13]
    assert cambios.prioridad_actual.tolist() == [MEDIA, ALTA]
    fifo = motor._simular_estrategia(replace(p, deterioro_cada_min=5), cohorte, asistido=False)
    assert fifo.pacientes.reevaluaciones.eq(0).all()


@pytest.mark.parametrize("cambio", [
    {"perfil_llegadas": (1,)}, {"perfil_llegadas": (-1,) * 8},
    {"medias_consulta_prioridad": (1, 2)}, {"medias_consulta_prioridad": (1, 0, 2)},
    {"forma_triaje": 0}, {"forma_consulta": float("nan")},
    {"triaje_medio_min": -1}, {"persistencia_conexion_min": 0},
    {"especialistas_remotos": -1}, {"seguimiento_min": -1},
    {"umbral_alto": .4, "umbral_medio": .5}, {"generar_hasta_cierre": 1},
    {"fraccion_alta_prioritarios": -0.1}, {"fraccion_alta_prioritarios": 1.1},
])
def test_rechaza_configuraciones_avanzadas_inconsistentes(cambio):
    with pytest.raises(ValueError):
        Parametros(**cambio)

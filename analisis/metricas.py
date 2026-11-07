"""Métricas observadas con denominadores y censura temporal explícitos."""

import numpy as np
import pandas as pd

from modelos.distribuciones import TABLA_INTERARRIBOS, TABLA_SERVICIOS, media_frecuencias
from modelos.variables import PRIORIDADES, Parametros
from simulacion.motor import Experimento, Resultado

# Filas referencia, columnas asignación; costos educativos relativos, no clínicos.
COSTOS_CLASIFICACION = np.array([[0., 5., 10.], [1., 0., 3.], [2., 1., 0.]])


def _media(s: pd.Series) -> float | None:
    return float(s.mean()) if s.notna().any() else None


def _percentil(s: pd.Series, q: float) -> float | None:
    return float(s.quantile(q)) if s.notna().any() else None


def _horizonte(p: Parametros) -> float:
    return float(p.turno_min + getattr(p, "seguimiento_min", 0))


def _antes(s: pd.Series, horizonte: float) -> pd.Series:
    return s.notna() & (s < horizonte)


def _carga(inicios: pd.Series, fines: pd.Series, turno: float, recursos: int) -> float:
    activos = _antes(inicios, turno)
    minutos = fines.loc[activos].fillna(turno).clip(upper=turno) - inicios.loc[activos]
    return float(100 * minutos.clip(lower=0).sum() / (turno * recursos))


def carga_ofrecida(p: Parametros) -> float:
    """Carga nominal durante llegadas; no ocupación medida ni equilibrio garantizado."""
    if p.usar_tablas_frecuencia:
        tasa = 60 / media_frecuencias(TABLA_INTERARRIBOS)
        servicio = media_frecuencias(TABLA_SERVICIOS)
        return float(tasa * servicio / (60 * p.medicos))
    perfil = getattr(p, "perfil_llegadas", ())
    tasa = p.llegadas_por_hora * (float(np.mean(perfil)) if perfil else 1)
    medias = getattr(p, "medias_consulta_prioridad", ())
    f = p.proporcion_prioritarios
    g = getattr(p, "fraccion_alta_prioritarios", .4)
    servicio = float(np.dot([g*f, (1-g)*f, 1-f], medias)) if medias else p.duracion_consulta_min
    return float(tasa * servicio / (60 * p.medicos))


def _resumen_horizonte(resultado: Resultado, p: Parametros, h: float) -> dict:
    t = resultado.pacientes
    llegadas = t.llegada_min < min(h, p.turno_min)
    inicio, fin, triaje = (_antes(t[c], h) for c in ("inicio_consulta_min", "fin_consulta_min", "fin_triaje_min"))
    nl, nf = int(llegadas.sum()), int(fin.sum())
    clasificados = t.loc[triaje & t.prioridad_asignada.notna()]
    coincide = clasificados.prioridad_asignada == clasificados.prioridad_referencia
    subtriaje = clasificados.prioridad_asignada > clasificados.prioridad_referencia
    altas = clasificados.loc[clasificados.prioridad_referencia == 1]
    perdidas = COSTOS_CLASIFICACION[clasificados.prioridad_referencia.to_numpy(dtype=int)-1,
                                   clasificados.prioridad_asignada.to_numpy(dtype=int)-1]
    enviadas, respondidas = (_antes(t[c], h) for c in ("tele_enviada_min", "tele_respondida_min"))
    ns = int(_antes(t.tele_solicitada_min, h).sum())
    ne, nr = int(enviadas.sum()), int(respondidas.sum())
    remoto = _antes(t.inicio_atencion_remota_min, h) if "inicio_atencion_remota_min" in t else enviadas
    esperas = t.loc[inicio, "inicio_consulta_min"] - t.loc[inicio, "llegada_min"]
    # Las esperas sin terminar aportan minutos transcurridos, nunca cero ni tiempos imputados.
    observados = t.inicio_consulta_min.where(inicio, h)
    acumulada = observados.loc[llegadas] - t.loc[llegadas, "llegada_min"]
    medica_acumulada = observados.loc[triaje] - t.loc[triaje, "fin_triaje_min"]
    intentos = resultado.eventos.loc[(resultado.eventos.evento == "tele_intento") & (resultado.eventos.minuto < h)]
    return {
        "horizonte_observacion_min": h,
        "pacientes_llegados": nl, "pacientes_atendidos": nf, "consultas_iniciadas": int(inicio.sum()),
        "pacientes_sin_iniciar_consulta": int((llegadas & ~inicio).sum()), "pacientes_sin_completar": nl-nf,
        "atendidos_pct": 100*nf/nl if nl else None,
        "tiempo_hasta_atencion_min": _media(esperas),
        "tiempo_hasta_atencion_p90_min": _percentil(esperas, .90),
        "tiempo_hasta_atencion_p95_min": _percentil(esperas, .95),
        "muestra_esperas_iniciadas": int(inicio.sum()),
        "espera_acumulada_hasta_consulta_min": _media(acumulada),
        "espera_acumulada_total_min": float(acumulada.sum()),
        "espera_medica_acumulada_min": _media(medica_acumulada), "muestra_esperas_medicas": int(triaje.sum()),
        "carga_medicos_pct": _carga(t.inicio_consulta_min, t.fin_consulta_min, h, p.medicos),
        "carga_enfermeros_pct": _carga(t.inicio_triaje_min, t.fin_triaje_min, h, p.enfermeros),
        "carga_ofrecida_medica": carga_ofrecida(p),
        "concordancia_pct": 100*float(coincide.mean()) if len(clasificados) else None,
        "errores_subtriaje": int(subtriaje.sum()) if len(clasificados) else None,
        "tasa_subtriaje_pct": 100*float(subtriaje.mean()) if len(clasificados) else None,
        "sensibilidad_alta_pct": 100*float((altas.prioridad_asignada == 1).mean()) if len(altas) else None,
        "muestra_referencia_alta": len(altas),
        "perdida_clasificacion_media": float(perdidas.mean()) if len(perdidas) else None,
        "teleconsultas_pendientes": ns-nr, "teleconsultas_sin_enviar": ns-ne,
        "teleconsultas_esperando_respuesta": ne-nr, "teleconsultas_respondidas": nr,
        "teleconsultas_en_cola_remota": int((enviadas & ~remoto).sum()),
        "teleconsultas_en_atencion_remota": int((remoto & ~respondidas).sum()),
        "espera_colaremota_min": _media(t.loc[remoto, "inicio_atencion_remota_min"]-t.loc[remoto, "tele_enviada_min"])
            if "inicio_atencion_remota_min" in t else (0.0 if ne else None),
        "reintentos_envio": len(intentos)-ns,
        "demora_envio_teleconsulta_min": _media(t.loc[enviadas, "tele_enviada_min"]-t.loc[enviadas, "tele_solicitada_min"]),
        "respuesta_teleconsulta_min": _media(t.loc[respondidas, "tele_respondida_min"]-t.loc[respondidas, "tele_enviada_min"]),
        "respuesta_total_teleconsulta_min": _media(t.loc[respondidas, "tele_respondida_min"]-t.loc[respondidas, "tele_solicitada_min"]),
    }


def resumir(resultado: Resultado, p: Parametros) -> dict[str, float | int | None]:
    """Sin sufijo: final observado; *_al_cierre: corte al terminar las llegadas.

    Espera acumulada: promedio del tiempo observado hasta consulta o corte,
    sobre TODOS los elegibles. No estima la espera completa de censurados.
    """
    resumen = _resumen_horizonte(resultado, p, _horizonte(p))
    resumen.update({f"{k}_al_cierre": v for k, v in _resumen_horizonte(resultado, p, p.turno_min).items()})
    return resumen


def comparar(exp: Experimento) -> pd.DataFrame:
    return pd.DataFrame([resumir(exp.referencia, exp.parametros), resumir(exp.asistido, exp.parametros)],
                        index=pd.Index(["FIFO", "Triaje asistido"], name="Estrategia")).astype(float)


def matriz_clasificacion(resultado: Resultado) -> pd.DataFrame:
    """Cuenta asignación inicial frente a referencia sintética inicial."""
    c = resultado.pacientes.dropna(subset=["prioridad_asignada"])
    matriz = pd.crosstab(c.prioridad_referencia, c.prioridad_asignada)
    return matriz.reindex(index=PRIORIDADES, columns=PRIORIDADES, fill_value=0).astype(int).rename(
        index=PRIORIDADES, columns=PRIORIDADES).rename_axis(index="Referencia sintética", columns="Prioridad asignada")


def clasificacion_por_prioridad(resultado: Resultado) -> pd.DataFrame:
    c = resultado.pacientes.dropna(subset=["prioridad_asignada"])
    filas = []
    for prioridad, nombre in PRIORIDADES.items():
        casos = c.loc[c.prioridad_referencia == prioridad]
        filas.append({"prioridad_referencia": prioridad, "prioridad": nombre, "clasificados": len(casos),
            "sensibilidad_pct": 100*float((casos.prioridad_asignada == prioridad).mean()) if len(casos) else None,
            "subtriaje_pct": 100*float((casos.prioridad_asignada > prioridad).mean()) if len(casos) else None,
            "sobretriaje_pct": 100*float((casos.prioridad_asignada < prioridad).mean()) if len(casos) else None})
    return pd.DataFrame(filas)


def espera_por_prioridad(exp: Experimento, al_cierre: bool = False) -> pd.DataFrame:
    h = float(exp.parametros.turno_min) if al_cierre else _horizonte(exp.parametros)
    filas = []
    for estrategia, resultado in (("FIFO", exp.referencia), ("Triaje asistido", exp.asistido)):
        for prioridad in PRIORIDADES:
            t = resultado.pacientes.loc[(resultado.pacientes.prioridad_referencia == prioridad)
                & (resultado.pacientes.llegada_min < min(h, exp.parametros.turno_min))]
            iniciados = t.loc[_antes(t.inicio_consulta_min, h)]
            triaje = t.loc[_antes(t.fin_triaje_min, h)]
            observados = t.inicio_consulta_min.where(_antes(t.inicio_consulta_min, h), h)
            espera = iniciados.inicio_consulta_min-iniciados.fin_triaje_min
            pendientes = len(t)-len(iniciados)
            filas.append({"estrategia": estrategia, "prioridad_referencia": prioridad,
                "pacientes": len(iniciados), "llegados": len(t), "pendientes_sin_consulta": pendientes,
                "pendientes_sin_consulta_pct": 100*pendientes/len(t) if len(t) else None,
                "sin_completar": len(t)-int(_antes(t.fin_consulta_min, h).sum()),
                "espera_medica_min": _media(espera), "espera_medica_p90_min": _percentil(espera, .9),
                "espera_medica_p95_min": _percentil(espera, .95),
                "tiempo_hasta_atencion_min": _media(iniciados.inicio_consulta_min-iniciados.llegada_min),
                "espera_acumulada_hasta_consulta_min": _media(observados-t.llegada_min),
                "espera_medica_acumulada_min": _media(observados.loc[triaje.index]-triaje.fin_triaje_min),
                "muestra_esperas_medicas": len(triaje), "horizonte_min": h})
    return pd.DataFrame(filas).astype({"espera_medica_min": float, "tiempo_hasta_atencion_min": float})

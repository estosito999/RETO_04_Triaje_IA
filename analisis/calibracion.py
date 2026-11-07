"""Calibración descriptiva a partir de turnos completos declarados por el usuario.

No interpreta señales clínicas ni entrena el clasificador. Los tiempos de servicio
deben ser observaciones completas, no esperas ni duraciones cortadas al cierre.
"""

from dataclasses import replace
from numbers import Integral

import numpy as np
import pandas as pd

from modelos.variables import PRIORIDADES, Parametros

COLUMNAS_CALIBRACION = (
    "llegada_min", "duracion_triaje_min", "duracion_consulta_min", "prioridad_referencia",
)


def calibrar_desde_datos(
    datos: pd.DataFrame, p: Parametros, numero_turnos: int = 1,
) -> tuple[Parametros, pd.DataFrame]:
    """Estima tasas por hora y parámetros Gamma mediante momentos.

    ``llegada_min`` es relativa al inicio de cada turno. ``numero_turnos`` incluye
    los turnos sin llegadas; cada turno dura ``p.horas_turno``. Las cuatro columnas
    son obligatorias y todas las duraciones deben estar completas y ser positivas.
    No se eliminan filas incompletas ni se recortan estimaciones a los rangos de la
    aplicación. Las clases con menos de dos servicios conservan su media anterior.

    La tabla devuelta incluye los tamaños de muestra y el alcance de cada ajuste;
    ``tabla.attrs['metadatos']`` conserva denominadores y supuestos del conjunto.
    """
    if isinstance(numero_turnos, bool) or not isinstance(numero_turnos, Integral) or numero_turnos < 1:
        raise ValueError("El número de turnos completos debe ser un entero positivo.")
    faltan = [col for col in COLUMNAS_CALIBRACION if col not in datos.columns]
    if faltan:
        raise ValueError("Faltan columnas de calibración: " + ", ".join(faltan) + ".")
    if len(datos) < 2:
        raise ValueError("Se requieren al menos dos pacientes con servicios completos para calibrar.")
    tabla = datos.loc[:, COLUMNAS_CALIBRACION].apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(tabla.to_numpy(dtype=float)).all():
        raise ValueError(
            "Las columnas de calibración deben contener números finitos y duraciones completas. "
            "No se imputan ni se descartan servicios censurados o incompletos."
        )
    if not tabla.llegada_min.between(0, p.turno_min, inclusive="left").all():
        raise ValueError("Cada llegada_min debe estar entre 0 y el cierre, relativa al inicio de su turno.")
    if not (tabla[["duracion_triaje_min", "duracion_consulta_min"]] > 0).all().all():
        raise ValueError("Las duraciones de los servicios completos deben ser mayores que cero.")
    if not tabla.prioridad_referencia.isin(PRIORIDADES).all():
        raise ValueError("prioridad_referencia debe ser 1 (alta), 2 (media) o 3 (baja).")

    filas: list[dict[str, object]] = []

    def registrar(nombre: str, valor: float, n: int, metodo: str, observacion: str = "") -> None:
        filas.append({
            "parametro": nombre, "estimacion": float(valor), "n": int(n),
            "metodo": metodo, "observacion": observacion,
        })

    total = len(tabla)
    horas_observadas = int(numero_turnos) * p.horas_turno
    tasa = total / horas_observadas
    conteos = np.bincount(
        (tabla.llegada_min.to_numpy(dtype=float) // 60).astype(int), minlength=p.horas_turno,
    )
    perfil = tuple(float(c / numero_turnos / tasa) for c in conteos)
    registrar(
        "llegadas_por_hora", tasa, total, "conteo / horas observadas",
        f"Denominador: {horas_observadas} horas en {numero_turnos} turnos completos; incluye horas sin llegadas.",
    )
    for hora, factor in enumerate(perfil):
        registrar(
            f"perfil_llegadas_hora_{hora + 1}", factor, int(conteos[hora]),
            "tasa de la hora / tasa global", "Factor multiplicativo de llegadas_por_hora.",
        )

    triajes = tabla.duracion_triaje_min.to_numpy(dtype=float)
    media_triaje = float(triajes.mean())
    varianza_triaje = float(triajes.var(ddof=1))
    forma_triaje = media_triaje**2 / varianza_triaje if varianza_triaje > 0 else p.forma_triaje
    registrar("triaje_medio_min", media_triaje, total, "media de servicios completos")
    registrar(
        "forma_triaje", forma_triaje, total,
        "momentos: media² / varianza muestral" if varianza_triaje > 0 else "valor anterior conservado",
        "Varianza cero: la forma Gamma no es identificable con estos datos." if varianza_triaje == 0 else "",
    )

    medias_anteriores = p.medias_consulta_prioridad or (p.duracion_consulta_min,) * 3
    medias = list(medias_anteriores)
    suma_residuos = 0.0
    grados_libertad = 0
    grupos_sin_ajuste = []
    for prioridad, nombre in PRIORIDADES.items():
        servicios = tabla.loc[tabla.prioridad_referencia == prioridad, "duracion_consulta_min"].to_numpy(dtype=float)
        if len(servicios) >= 2:
            medias[prioridad - 1] = float(servicios.mean())
            suma_residuos += float(np.square(servicios / medias[prioridad - 1] - 1).sum())
            grados_libertad += len(servicios) - 1
            metodo = "media de servicios completos de la clase"
            observacion = ""
        else:
            grupos_sin_ajuste.append(nombre)
            metodo = "valor anterior conservado"
            observacion = "Menos de dos servicios completos en esta clase; su media no se estima."
        registrar(f"consulta_media_{nombre.lower()}_min", medias[prioridad - 1], len(servicios), metodo, observacion)

    forma_consulta = grados_libertad / suma_residuos if suma_residuos > 0 else p.forma_consulta
    registrar(
        "forma_consulta", forma_consulta, sum(int((tabla.prioridad_referencia == k).sum()) for k in PRIORIDADES
                                             if int((tabla.prioridad_referencia == k).sum()) >= 2),
        "momentos con variación normalizada dentro de cada clase" if suma_residuos > 0 else "valor anterior conservado",
        "Forma común a las tres clases; evita confundir diferencias de medias con variación interna."
        if suma_residuos > 0 else "Variación interna insuficiente: se conserva la forma anterior.",
    )
    media_consulta = float(tabla.duracion_consulta_min.mean())
    registrar("duracion_consulta_min", media_consulta, total, "media global de servicios completos")
    proporcion = float((tabla.prioridad_referencia < 3).mean())
    registrar(
        "proporcion_prioritarios", proporcion, total, "fracción observada de prioridades alta y media",
    )
    prioritarios = int((tabla.prioridad_referencia < 3).sum())
    fraccion_alta = float((tabla.prioridad_referencia == 1).sum() / prioritarios) if prioritarios else p.fraccion_alta_prioritarios
    registrar(
        "fraccion_alta_prioritarios", fraccion_alta, prioritarios,
        "fracción observada de prioridad alta entre alta y media" if prioritarios else "valor anterior conservado",
        "Sin pacientes prioritarios: la separación alta/media no se puede estimar." if not prioritarios else "",
    )
    try:
        ajustados = replace(
            p, llegadas_por_hora=tasa, perfil_llegadas=perfil,
            triaje_medio_min=media_triaje, forma_triaje=forma_triaje,
            duracion_consulta_min=media_consulta, forma_consulta=forma_consulta,
            medias_consulta_prioridad=tuple(medias), proporcion_prioritarios=proporcion,
            fraccion_alta_prioritarios=fraccion_alta,
        )
    except ValueError as error:
        raise ValueError(
            f"Los parámetros estimados quedan fuera del rango admitido: {error} "
            "No se han recortado ni aplicado estimaciones. Revisa los datos o los límites del modelo."
        ) from error
    informe = pd.DataFrame(filas)
    informe.attrs["metadatos"] = {
        "numero_turnos": int(numero_turnos), "horas_por_turno": p.horas_turno,
        "horas_observadas": horas_observadas, "pacientes_observados": total,
        "grupos_sin_ajuste_de_media": grupos_sin_ajuste,
        "metodo": "momentos con servicios completos",
        "supuestos": [
            "Todos los turnos declarados están completamente observados, incluidos los turnos sin llegadas.",
            "Llegadas expresadas en minutos desde el inicio de cada turno.",
            "Servicios completos: no sustituir duraciones pendientes por el tiempo transcurrido al cierre.",
            "Muestra sin selección por finalización de consulta; un archivo solo de atendidos puede sesgar el ajuste.",
            "El ajuste describe esta muestra; no acredita validez clínica ni entrena el clasificador.",
        ],
    }
    return ajustados, informe

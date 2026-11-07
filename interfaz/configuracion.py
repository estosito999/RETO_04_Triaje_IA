"""Condiciones de lectura del único experimento del laboratorio."""

import pandas as pd
import streamlit as st

from modelos.distribuciones import TABLA_INTERARRIBOS, TABLA_SERVICIOS, media_frecuencias
from modelos.variables import Parametros


def tablas_frecuencias() -> dict[str, pd.DataFrame]:
    tablas = {}
    for nombre, frecuencias in (("frecuencias_interarribos", TABLA_INTERARRIBOS),
                               ("frecuencias_servicio", TABLA_SERVICIOS)):
        tabla = pd.DataFrame(frecuencias, columns=["Tiempo (min)", "Frecuencia"])
        tabla["Probabilidad"] = tabla.Frecuencia / tabla.Frecuencia.sum()
        tabla["Acumulada"] = tabla.Frecuencia.cumsum() / tabla.Frecuencia.sum()
        tablas[nombre] = tabla
    return tablas


def mostrar_condiciones(p: Parametros) -> None:
    st.header("B · Condiciones fijas")
    st.write("Hospital abierto las 24 horas: se compara el mismo día con dos políticas de atención.")
    st.table(
        {
            "Duración del día": f"{p.horas_turno} horas",
            "Cupo diario": f"Máximo {p.pacientes} pacientes",
            "Llegadas": f"Entre 1 y 5 minutos; media {media_frecuencias(TABLA_INTERARRIBOS):.2f} minutos",
            "Enfermería": f"{p.enfermeros} puesto disponible · evaluación de {p.triaje_medio_min:g} minutos, en promedio",
            "Medicina": f"{p.medicos} médicos simultáneos · consulta de {p.duracion_consulta_min:g} minutos, en promedio",
            "Casos prioritarios": f"{p.proporcion_prioritarios:.0%} de probabilidad por paciente",
            "Políticas comparadas": "FIFO y triaje asistido sobre los mismos pacientes",
        },
        border="horizontal",
        width="stretch",
        alt="Condiciones fijas del día simulado y cupo máximo de pacientes",
    )
    st.info(
        f"Cada réplica incluye hasta {p.pacientes} pacientes del día. Al alcanzar el cupo se sigue observando "
        f"la atención hasta completar las {p.horas_turno} horas. Las llegadas cortas concentran el ingreso "
        "de los 100 pacientes en las primeras horas y forman colas. "
        "La medianoche es un corte de observación: el hospital continúa abierto y los pendientes no se dan de alta."
    )
    st.caption(
        "La dotación se mantiene mediante relevos de personal implícitos. Los tiempos y las prioridades "
        "se sortean con las mismas reglas en todas las jornadas; el porcentaje prioritario no es una cuota exacta."
    )
    st.subheader("Tablas de frecuencia")
    llegadas, servicios = st.columns(2)
    tablas = tablas_frecuencias()
    with llegadas:
        st.markdown("**Tiempo entre llegadas**")
        st.table(tablas["frecuencias_interarribos"], hide_index=True,
                 alt="Tiempos entre llegadas y sus frecuencias, probabilidades y acumuladas")
    with servicios:
        st.markdown("**Tiempo de consulta médica**")
        st.table(tablas["frecuencias_servicio"], hide_index=True,
                 alt="Tiempos de servicio médico y sus frecuencias, probabilidades y acumuladas")
    st.caption(
        "Las frecuencias son pesos sintéticos sobre 50 casos de referencia, no registros de un hospital real. "
        "Cada jornada sortea sus tiempos con estas probabilidades; sus frecuencias observadas pueden variar. "
        "El tiempo de consulta varía entre 15 y 35 minutos, con media de 25."
    )
    st.caption(
        "Se estudia un episodio de congestión dentro de un día de 24 horas. Cada réplica empieza vacía "
        "a las 00:00 y no hereda pacientes de otro día."
    )
    with st.expander("Teleconsulta y reproducibilidad"):
        st.write(
            f"La teleconsulta funciona en paralelo, sin retener al médico: disponibilidad de conexión "
            f"{p.disponibilidad_conexion:.0%}, respuesta media de {p.respuesta_remota_min:g} minutos y "
            f"reintento de envío cada {p.intervalo_reintento_min:g} minutos."
        )
        st.caption(
            f"Semilla de esta jornada: {p.semilla}. Nueva jornada aleatoria cambia los pacientes y los tiempos. "
            "La semilla queda en la exportación para reproducirlos; las condiciones se conservan."
        )

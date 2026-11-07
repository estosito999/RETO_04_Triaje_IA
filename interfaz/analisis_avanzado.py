"""Repeticiones y diagnósticos del experimento con condiciones fijas."""

import pandas as pd
import streamlit as st

from analisis.experimentos import ejecutar_replicas, resumen_pareado, semillas_replicas
from analisis.validacion import diagnosticar_azar
from modelos.variables import Parametros
from simulacion.escenarios import REPETICIONES_LABORATORIO


@st.cache_data(show_spinner=False, max_entries=8)
def _repetir(p: Parametros) -> tuple[pd.DataFrame, pd.DataFrame]:
    semillas = semillas_replicas(REPETICIONES_LABORATORIO, p.semilla)
    datos = ejecutar_replicas(p, semillas)
    return datos, resumen_pareado(datos)


def mostrar_herramientas(p: Parametros) -> dict[str, pd.DataFrame]:
    tablas = {}
    with st.expander("Repetir y medir incertidumbre"):
        st.caption(f"Se comparan {REPETICIONES_LABORATORIO} jornadas con las mismas condiciones fijas y una semilla "
                   "distinta por jornada. Dentro de ella, ambas políticas comparten pacientes. "
                   "El intervalo mide variación entre turnos del modelo, no incertidumbre clínica ni del ajuste de parámetros.")
        if st.button(f"Comparar {REPETICIONES_LABORATORIO} jornadas", key="ejecutar_replicas"):
            with st.spinner("Calculando las repeticiones…"):
                datos, resumen = _repetir(p)
                st.session_state.replicas_resultado = (p, datos, resumen)
        guardado = st.session_state.get("replicas_resultado")
        if guardado and guardado[0] == p:
            _, datos, resumen = guardado
            indicadores = {
                "pacientes_llegados": "Pacientes ingresados",
                "pacientes_atendidos": "Consultas completadas",
                "pacientes_sin_iniciar_consulta": "Sin iniciar consulta",
                "tiempo_hasta_atencion_min": "Tiempo medio hasta consulta (min)",
                "carga_medicos_pct": "Ocupación médica (%)",
            }
            jornadas = datos.loc[datos.metrica.isin(indicadores)].pivot(
                index=["semilla", "estrategia"], columns="metrica", values="valor",
            ).reset_index()
            orden = {semilla: i + 1 for i, semilla in enumerate(datos.semilla.unique())}
            jornadas.insert(0, "replica", jornadas.semilla.map(orden))
            jornadas = jornadas[["replica", "semilla", "estrategia", *indicadores]].sort_values(
                ["replica", "estrategia"],
            ).rename(columns={"replica": "Réplica", "semilla": "Semilla", "estrategia": "Política", **indicadores})
            jornadas.columns.name = None
            st.subheader("Resultados de cada jornada")
            st.dataframe(jornadas, key="resultados_jornadas", hide_index=True, width="stretch",
                         alt="Treinta réplicas diarias con sus semillas y resultados de ambas políticas")
            st.caption("Cada par de filas representa el mismo día con FIFO y triaje asistido. "
                       "Las jornadas cambian al azar; las condiciones de atención permanecen fijas.")
            st.subheader("Diferencias e incertidumbre entre jornadas")
            visible = resumen.drop(columns=["escenario", "condicion"]).assign(
                metrica=resumen.metrica.str.replace("_", " ").str.capitalize(),
            ).rename(columns={"metrica": "Métrica", "repeticiones": "Repeticiones",
                "pares_validos": "Pares válidos", "pares_faltantes": "Pares sin observación",
                "diferencia_media": "Diferencia media", "desviacion_diferencias": "Desviación de diferencias",
                "error_estandar": "Error estándar", "ic95_inferior": "IC 95 % inferior", "ic95_superior": "IC 95 % superior"})
            st.dataframe(visible, hide_index=True, width="stretch", alt="Diferencias entre políticas con intervalos de confianza")
            st.caption("Diferencia = triaje asistido − FIFO. En tiempos y errores, un valor negativo indica una reducción. "
                       "Los grupos sin observaciones quedan vacíos; revisa el número de pares válidos de cada métrica.")
            st.download_button("Descargar diferencias e intervalos", resumen.to_csv(index=False).encode("utf-8-sig"),
                               "resumen_pareado.csv", "text/csv", key="descargar_replicas", on_click="ignore")
            tablas.update(replicas=datos, jornadas=jornadas, resumen_pareado=resumen)

    with st.expander("Comprobar el generador y las distribuciones"):
        st.caption("Se conserva PCG64. Los diagnósticos contrastan uniformes, independencia aproximada y distribuciones "
                   "de entrada de la configuración base conocida. No contrastan las tablas de frecuencia "
                   "del laboratorio ni prueban que las entradas representen un hospital real.")
        if st.button("Ejecutar diagnósticos estadísticos", key="validar_azar"):
            st.session_state.diagnostico_azar = (p.semilla, diagnosticar_azar(p.semilla, n=10000))
        diagnostico = st.session_state.get("diagnostico_azar")
        if diagnostico and diagnostico[0] == p.semilla:
            st.dataframe(diagnostico[1].rename(columns={"prueba": "Prueba", "distribucion": "Distribución",
                         "n": "Muestra", "estadistico": "Estadístico", "p_valor": "Valor p",
                         "referencia": "Referencia", "interpretacion": "Interpretación"}),
                         hide_index=True, width="stretch", alt="Diagnósticos estadísticos de PCG64 y sus distribuciones")
            st.caption("Un valor p pequeño es una señal para investigar; varios contrastes también pueden producir "
                       "alertas por azar. No se eligen semillas para hacer aprobar los contrastes.")
            tablas["diagnostico_azar"] = diagnostico[1]
    return tablas

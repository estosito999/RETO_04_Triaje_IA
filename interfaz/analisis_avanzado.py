"""Herramientas opcionales para contrastar supuestos y repetir el experimento."""

from dataclasses import asdict
import json

import numpy as np
import pandas as pd
import streamlit as st

from analisis.calibracion import calibrar_desde_datos
from analisis.experimentos import ejecutar_replicas, resumen_pareado
from analisis.validacion import diagnosticar_azar
from modelos.variables import Parametros


@st.cache_data(show_spinner=False, max_entries=8)
def _repetir(p: Parametros, cantidad: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    semillas = [int(s.generate_state(1)[0]) for s in np.random.SeedSequence(p.semilla).spawn(cantidad)]
    datos = ejecutar_replicas(p, semillas)
    return datos, resumen_pareado(datos)


def mostrar_herramientas(p: Parametros) -> dict[str, pd.DataFrame]:
    tablas = {}
    with st.expander("Repetir y medir incertidumbre"):
        st.caption("Cada repetición usa una semilla distinta. Dentro de ella, ambas políticas comparten pacientes. "
                   "El intervalo mide variación entre turnos del modelo, no incertidumbre clínica ni del ajuste de parámetros.")
        with st.form("replicas"):
            cantidad = st.number_input("Repeticiones", 2, 500, 30, key="cantidad_replicas")
            ejecutar = st.form_submit_button("Comparar varias repeticiones", key="ejecutar_replicas")
        if ejecutar:
            with st.spinner("Calculando las repeticiones…"):
                datos, resumen = _repetir(p, cantidad)
                st.session_state.replicas_resultado = (p, datos, resumen)
        guardado = st.session_state.get("replicas_resultado")
        if guardado and guardado[0] == p:
            _, datos, resumen = guardado
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
            tablas.update(replicas=datos, resumen_pareado=resumen)
        elif guardado:
            st.caption("La configuración cambió. Ejecuta de nuevo para obtener intervalos de esta corrida.")

    with st.expander("Comprobar el generador y las distribuciones"):
        st.caption("Se conserva PCG64. Los diagnósticos contrastan uniformes, independencia aproximada y distribuciones "
                   "de entrada con parámetros conocidos; no prueban que representen un centro real.")
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


def mostrar_calibracion(p: Parametros) -> Parametros | None:
    with st.expander("Ajustar parámetros con registros de turnos completos"):
        st.caption("El CSV debe contener llegada_min (desde el inicio de cada turno), duracion_triaje_min, "
                   "duracion_consulta_min y prioridad_referencia (1, 2 o 3). Declara todos los turnos observados, "
                   "incluidos los que no tuvieron llegadas. Los tiempos deben ser completos y positivos; "
                   "una muestra elegida solo entre casos atendidos puede sesgar el ajuste.")
        st.download_button("Descargar cabecera del CSV", 
                           "llegada_min,duracion_triaje_min,duracion_consulta_min,prioridad_referencia\n".encode("utf-8"),
                           "plantilla_calibracion.csv", "text/csv", key="plantilla_calibracion", on_click="ignore")
        with st.form("calibracion"):
            archivo = st.file_uploader("Registros para el ajuste", type=["csv"], key="datos_calibracion")
            turnos = st.number_input("Turnos completos observados", 1, 100000, 1, key="turnos_calibracion")
            ajustar = st.form_submit_button("Calcular ajuste", key="ajustar_datos")
        if ajustar:
            if archivo is None:
                st.error("Selecciona el CSV de registros antes de calcular el ajuste.")
            else:
                try:
                    datos = pd.read_csv(archivo)
                    ajustado, tabla = calibrar_desde_datos(datos, p, numero_turnos=turnos)
                    st.session_state.ajuste_preparado = (p, ajustado, tabla)
                except (ValueError, TypeError, pd.errors.ParserError, UnicodeDecodeError) as error:
                    st.session_state.pop("ajuste_preparado", None)
                    st.error(f"No se pudo ajustar la muestra: {error}")
        ajuste = st.session_state.get("ajuste_preparado")
        if ajuste and ajuste[0] == p:
            _, ajustado, tabla = ajuste
            st.dataframe(tabla.rename(columns={"parametro": "Parámetro", "estimacion": "Estimación",
                         "n": "Muestra", "metodo": "Método", "observacion": "Observación"}),
                         hide_index=True, width="stretch", alt="Parámetros ajustados y tamaños de muestra")
            st.caption("El ajuste describe el CSV aportado. El clasificador sigue siendo una regla; esta operación no entrena una IA.")
            st.download_button("Descargar parámetros ajustados", json.dumps(asdict(ajustado), ensure_ascii=False, indent=2),
                               "parametros_ajustados.json", "application/json", key="descargar_ajuste", on_click="ignore")
            if st.button("Preparar con parámetros ajustados", key="aplicar_ajuste"):
                return ajustado
    return None

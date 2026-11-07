from dataclasses import asdict

import pandas as pd
import streamlit as st

from analisis.metricas import comparar, espera_por_prioridad, matriz_clasificacion, clasificacion_por_prioridad
from interfaz.analisis_avanzado import mostrar_calibracion, mostrar_herramientas
from interfaz.configuracion import panel
from interfaz.exportacion import exportar
from interfaz.reproduccion import mostrar_reproduccion, reiniciar_reproduccion
from interfaz.visualizaciones import comparar_esperas, cronologia, vista_turno
from modelos.variables import PRIORIDADES, Parametros
from simulacion.escenarios import ESCENARIOS
from simulacion.motor import Experimento, simular
from simulacion.generador_datos import generar_trayectoria_conexion

EVENTOS = {
    "llegada": "Llegada al centro", "inicio_triaje": "Inicio de evaluación",
    "fin_triaje": "Fin de evaluación", "inicio_consulta": "Inicio de consulta",
    "fin_consulta": "Consulta completada", "tele_solicitada": "Teleconsulta solicitada",
    "tele_intento": "Intento de envío remoto",
    "tele_enviada": "Teleconsulta enviada", "tele_respondida": "Teleconsulta respondida",
    "reevaluacion": "Prioridad reevaluada en espera",
}
METRICAS = {
    "pacientes_llegados": "Pacientes llegados",
    "pacientes_atendidos": "Consultas completadas",
    "atendidos_pct": "Pacientes atendidos (%)",
    "tiempo_hasta_atencion_min": "Tiempo medio hasta consulta (min)",
    "carga_medicos_pct": "Ocupación médica (%)",
    "carga_enfermeros_pct": "Ocupación de enfermería (%)",
    "concordancia_pct": "Concordancia sintética (%)",
    "errores_subtriaje": "Casos de subtriaje",
    "tasa_subtriaje_pct": "Subtriaje (%)",
    "teleconsultas_pendientes": "Teleconsultas pendientes",
    "teleconsultas_sin_enviar": "Teleconsultas por enviar",
    "teleconsultas_esperando_respuesta": "Teleconsultas esperando respuesta",
    "teleconsultas_respondidas": "Teleconsultas respondidas",
    "reintentos_envio": "Reintentos de envío",
    "demora_envio_teleconsulta_min": "Espera media hasta envío (min)",
    "respuesta_teleconsulta_min": "Tiempo medio de respuesta remota (min)",
    "respuesta_total_teleconsulta_min": "Tiempo medio solicitud-respuesta (min)",
    "pacientes_sin_iniciar_consulta": "Sin iniciar consulta al final",
    "pacientes_sin_completar": "Sin completar consulta al final",
    "espera_acumulada_hasta_consulta_min": "Tiempo observado hasta consulta o corte (min)",
    "tiempo_hasta_atencion_p95_min": "P95 hasta consulta, solo iniciadas (min)",
    "sensibilidad_alta_pct": "Sensibilidad de prioridad alta (%)",
    "perdida_clasificacion_media": "Costo medio de clasificación (relativo)",
    "carga_ofrecida_medica": "Demanda / capacidad médica nominal",
}
PLOTLY = {"displaylogo": False}


def mostrar_simulacion(exp: Experimento) -> None:
    st.header("C · Simulación")
    estrategia = st.radio("Política en pantalla", ("FIFO", "Triaje asistido"), index=1, horizontal=True)
    asistido = estrategia == "Triaje asistido"
    resultado = exp.asistido if asistido else exp.referencia
    conexion = generar_trayectoria_conexion(exp.parametros) if exp.parametros.conexion_compartida else None

    def dibujar(paso: int) -> None:
        cuadro = resultado.cronologia.iloc[paso]
        a, b, c, d = st.columns(4)
        a.metric("Llegadas / completadas", f"{int(cuadro.llegados)} / {int(cuadro.atendidos)}")
        b.metric("Enfermería ocupada", f"{int(cuadro.enfermeros_ocupados)} / {exp.parametros.enfermeros}")
        c.metric("Médicos ocupados", f"{int(cuadro.medicos_ocupados)} / {exp.parametros.medicos}")
        d.metric("Teleconsultas pendientes", int(cuadro.telependientes))
        st.caption(f"Minuto simulado {cuadro.minuto:g} · "
                   f"{int(cuadro.cola_enfermeria)} en cola de enfermería · {int(cuadro.cola_medica)} en cola médica")
        st.caption(f"Teleconsulta · {int(cuadro.telepor_enviar)} por enviar · "
                   f"{int(cuadro.teleesperando_respuesta)} esperando respuesta")
        if conexion is not None:
            st.caption("Conexión compartida del centro: " + ("disponible" if conexion.conectada(cuadro.minuto) else "interrumpida"))
        st.plotly_chart(vista_turno(resultado.pacientes, cuadro.minuto, asistido=asistido, eventos=resultado.eventos),
                        width="stretch", config=PLOTLY, alt="Pacientes en cada etapa y prioridad de cola en ese instante")
        st.caption(
            "El color representa la prioridad de cola en este instante, incluidas las reevaluaciones. El gris indica "
            "que falta terminar la evaluación local. El puntero muestra la referencia inicial y la prioridad de cola."
            if asistido else
            "FIFO atiende por orden de entrada a la cola médica. Los colores muestran la referencia sintética "
            "para estudiar a quién alcanza cada política dentro del turno."
        )
        recientes = resultado.eventos.loc[resultado.eventos["minuto"] <= cuadro.minuto].tail(8)
        if recientes.empty:
            st.caption("El registro de actividad aparecerá después de las primeras llegadas.")
        else:
            st.subheader("Actividad reciente")
            registros = recientes.merge(
                resultado.pacientes[["id_paciente", "prioridad_asignada", "fin_triaje_min"]],
                on="id_paciente", how="left",
            )
            asignadas = registros.prioridad_asignada.where(registros.fin_triaje_min <= registros.minuto)
            registros = registros.assign(
                evento=registros.evento.map(EVENTOS),
                prioridad_referencia=registros.prioridad_referencia.map(PRIORIDADES),
                prioridad_asignada=asignadas.map(PRIORIDADES).fillna(
                    "Sin clasificar" if asistido else "No aplica en FIFO",
                ),
                prioridad_actual=registros.prioridad_actual.map(PRIORIDADES).fillna("Sin asignar"),
            ).drop(columns="fin_triaje_min").rename(columns={
                "minuto": "Minuto", "id_paciente": "Paciente", "evento": "Evento",
                "prioridad_referencia": "Referencia sintética", "prioridad_asignada": "Prioridad asignada",
                "prioridad_actual": "Prioridad en ese evento",
            })
            st.dataframe(registros, width="stretch", hide_index=True)

    mostrar_reproduccion(len(resultado.cronologia), dibujar)


def mostrar() -> None:
    st.caption("LABORATORIO DE SIMULACIÓN · RETO 04")
    st.title("Triaje local y teleconsulta asíncrona")
    st.write("Un experimento de colas, clasificación computacional y conectividad en un centro de salud ficticio.")
    parametros = panel()
    estado = st.session_state
    anterior = estado.get("experimento")
    if anterior is not None and (
        not hasattr(anterior.parametros, "seguimiento_min")
        or "prioridad_actual" not in anterior.asistido.eventos
    ):
        estado.experimento = simular(Parametros(**asdict(anterior.parametros)))
        reiniciar_reproduccion()
    if parametros is not None or "experimento" not in estado:
        try:
            estado.experimento = simular(parametros if parametros is not None else next(iter(ESCENARIOS.values())))
            reiniciar_reproduccion()
        except ValueError as error:
            st.error(f"No se pudo preparar la corrida. {error}")
            if "experimento" not in estado:
                st.stop()
    exp = estado.experimento
    st.caption(f"Corrida preparada · {exp.parametros.horas_turno} h de llegadas · {len(exp.asistido.pacientes)} pacientes generados "
               f"· {exp.parametros.seguimiento_min:g} min de seguimiento · Semilla {exp.parametros.semilla}")
    intro, simulacion, analisis, cierre = st.tabs(
        ("A · Introducción", "C · Simulación", "D · Análisis", "E · Conclusiones"), default="C · Simulación",
    )
    with intro:
        st.header("A · Introducción")
        st.write("Cada paciente llega a enfermería y espera una consulta médica. La política FIFO ordena la cola "
                 "médica por llegada a esa cola. La política asistida usa señales numéricas sintéticas para "
                 "asignar una prioridad en el dispositivo local.")
        st.write("Las solicitudes remotas se procesan en paralelo al turno. La conexión condiciona el envío, "
                 "mientras el clasificador local sigue disponible. Si no hay conexión, el mensaje se conserva "
                 "localmente y su envío se reintenta durante el turno.")
        st.write("En configuración puedes activar demanda por hora, tiempos por prioridad, cortes compartidos y "
                 "especialistas limitados. La reevaluación es una regla educativa de promoción en la cola. "
                 "La opción de esperar una respuesta remota mantiene al médico ocupado hasta recibirla.")
        st.info("Experimento educativo con pacientes y señales ficticios. Las prioridades y métricas tienen significado "
                "dentro de este modelo. La herramienta carece de validación clínica.")
    with simulacion:
        mostrar_simulacion(exp)
    resultados = comparar(exp)
    esperas = espera_por_prioridad(exp)
    clasificacion = matriz_clasificacion(exp.asistido)
    tabla = resultados.rename(columns=METRICAS).rename_axis("Política").reset_index()
    with analisis:
        st.header("D · Análisis")
        st.caption(f"Mismos pacientes, duraciones y recursos en las dos políticas. Llegadas hasta el minuto "
                   f"{exp.parametros.turno_min}; observación hasta el minuto {exp.parametros.horizonte_min:g}.")
        principales = ["pacientes_llegados", "pacientes_atendidos", "pacientes_sin_iniciar_consulta",
                       "pacientes_sin_completar", "tiempo_hasta_atencion_min",
                       "espera_acumulada_hasta_consulta_min", "tiempo_hasta_atencion_p95_min",
                       "carga_medicos_pct", "carga_ofrecida_medica", "sensibilidad_alta_pct",
                       "perdida_clasificacion_media", "teleconsultas_pendientes"]
        st.dataframe(resultados[principales].rename(columns=METRICAS).T.rename_axis("Métrica").reset_index(),
                     width="stretch", hide_index=True, alt="Comparación de ambas políticas al final de la observación")
        rho = resultados.loc["Triaje asistido", "carga_ofrecida_medica"]
        if rho >= 1:
            st.info(f"La carga nominal es {rho:.2f}: la demanda de servicio supera o iguala la capacidad médica "
                    "media si ese flujo se mantuviera. El cupo y el turno finito limitan la acumulación observada.")
        st.caption("La carga nominal usa el servicio local y la demanda configurada. No incluye el tiempo adicional "
                   "de retener médicos esperando teleconsulta ni representa ocupación medida.")
        st.plotly_chart(comparar_esperas(esperas), width="stretch", config=PLOTLY)
        etiquetas_espera = {"estrategia": "Política", "prioridad_referencia": "Referencia inicial",
            "llegados": "Llegados", "pacientes": "Consultas iniciadas", "pendientes_sin_consulta": "Sin iniciar",
            "sin_completar": "Sin completar", "espera_acumulada_hasta_consulta_min": "Tiempo observado hasta consulta o corte (min)",
            "espera_medica_p95_min": "P95 cola médica, solo iniciadas (min)"}
        st.dataframe(esperas[list(etiquetas_espera)].rename(columns=etiquetas_espera).replace({"Referencia inicial": PRIORIDADES}),
                     hide_index=True, width="stretch", alt="Esperas y pacientes pendientes por prioridad inicial")
        st.caption("El tiempo observado hasta consulta o corte incluye a quienes siguen esperando. Es un tiempo "
                   "acumulado con censura, no una estimación de su espera completa. Los percentiles usan solo consultas iniciadas.")
        if exp.parametros.seguimiento_min:
            cierre_tabla = resultados.filter(like="_al_cierre").rename(columns=lambda c: c.removesuffix("_al_cierre"))
            with st.expander("Comparación al cierre, antes del seguimiento"):
                st.dataframe(cierre_tabla[principales].rename(columns=METRICAS).T.rename_axis("Métrica").reset_index(),
                             hide_index=True, width="stretch", alt="Comparación de ambas políticas al terminar las llegadas")
                st.dataframe(espera_por_prioridad(exp, al_cierre=True), hide_index=True, width="stretch",
                             alt="Pacientes pendientes por prioridad al cierre de llegadas")
        serie = st.radio("Cronología de", ("FIFO", "Triaje asistido"), index=1, horizontal=True)
        datos = exp.referencia if serie == "FIFO" else exp.asistido
        st.plotly_chart(cronologia(datos.cronologia), width="stretch", config=PLOTLY)
        st.caption("La espera médica empieza al terminar enfermería. El tiempo hasta la atención empieza con la llegada. "
                   "Los promedios incluyen pacientes que iniciaron consulta y las respuestas observadas. "
                   "Las métricas de clasificación solo aplican al triaje asistido.")
        st.caption("Las teleconsultas pendientes se dividen entre las que esperan conexión para el envío y las ya "
                   "enviadas que esperan respuesta. El tiempo solicitud-respuesta incluye la demora de conexión; "
                   "la respuesta remota se mide desde el envío.")
        st.subheader("Clasificación del triaje asistido")
        clasificacion_visible = clasificacion.assign(**{"Casos clasificados": clasificacion.sum(axis=1)})
        st.dataframe(clasificacion_visible, width="stretch")
        st.caption(
            "Las filas son prioridades sintéticas de referencia y las columnas Alta, Media y Baja son asignaciones. "
            "La diagonal cuenta coincidencias. A su derecha se cuentan los casos de subtriaje y a su izquierda, "
            "los de sobretriaje. Cada fila incluye su número de pacientes clasificados."
        )
        clases = clasificacion_por_prioridad(exp.asistido)
        st.dataframe(clases.rename(columns={"prioridad": "Referencia", "clasificados": "Casos",
                     "sensibilidad_pct": "Sensibilidad (%)", "subtriaje_pct": "Subtriaje (%)",
                     "sobretriaje_pct": "Sobretriaje (%)"}).drop(columns="prioridad_referencia"),
                     hide_index=True, width="stretch", alt="Sensibilidad y tipos de error para cada prioridad")
        st.caption("La clasificación compara la asignación inicial con la referencia inicial, antes de las reevaluaciones. "
                   "Costo educativo: alta→media 5, alta→baja 10, media→alta 1, media→baja 3, "
                   "baja→alta 2 y baja→media 1; aciertos 0. Son pesos relativos sin calibración clínica.")
        adicionales = mostrar_herramientas(exp.parametros)
        if exp.parametros.conexion_compartida:
            conexion = generar_trayectoria_conexion(exp.parametros)
            adicionales["conexion_compartida"] = pd.DataFrame({"minuto": conexion.tiempos, "conectada": conexion.estados})
        ajustados = mostrar_calibracion(exp.parametros)
        if ajustados is not None:
            estado.experimento = simular(ajustados)
            estado.configuracion_calibrada = ajustados
            estado.seleccionar_ajuste = True
            estado.calibracion_aplicada = (ajustados, estado.ajuste_preparado[2])
            reiniciar_reproduccion()
            st.rerun()
        ajuste = estado.get("calibracion_aplicada")
        if ajuste and ajuste[0] == exp.parametros:
            adicionales["ajuste_parametros"] = ajuste[1]
            st.caption("Esta corrida usa parámetros ajustados al CSV aportado.")
        exportar(exp.parametros, {"comparacion": tabla, "esperas": esperas,
                                 "esperas_al_cierre": espera_por_prioridad(exp, al_cierre=True),
                                 "clasificacion_por_prioridad": clases,
                                 "clasificacion_asistida": clasificacion.reset_index(),
                                 "pacientes_fifo": exp.referencia.pacientes, "pacientes_asistido": exp.asistido.pacientes,
                                 "eventos_fifo": exp.referencia.eventos, "eventos_asistido": exp.asistido.eventos,
                                 "turno_fifo": exp.referencia.cronologia, "turno_asistido": exp.asistido.cronologia,
                                 **adicionales},
                 "triaje")
    with cierre:
        st.header("E · Conclusiones")
        referencia = resultados.loc["FIFO"]
        asistido = resultados.loc["Triaje asistido"]
        st.write(f"Llegaron {int(asistido.pacientes_llegados)} pacientes de los {len(exp.asistido.pacientes)} generados. "
                 f"FIFO completó {int(referencia.pacientes_atendidos)} consultas y triaje asistido completó "
                 f"{int(asistido.pacientes_atendidos)}. Quedaron {int(asistido.teleconsultas_pendientes)} "
                 "teleconsultas pendientes con la política asistida.")
        st.write(f"De las pendientes, {int(asistido.teleconsultas_sin_enviar)} siguen por enviar y "
                 f"{int(asistido.teleconsultas_esperando_respuesta)} esperan respuesta remota. "
                 f"Se realizaron {int(asistido.reintentos_envio)} reintentos de envío.")
        if pd.notna(asistido.concordancia_pct):
            st.write(f"La prioridad asignada coincidió con la referencia sintética en el {asistido.concordancia_pct:.1f} % "
                     f"de los casos clasificados. Hubo {int(asistido.errores_subtriaje)} casos con prioridad asignada "
                     "inferior a la etiqueta de referencia.")
        st.write("Revisa el tiempo por prioridad junto con el número de consultas completadas. La cola cambia el "
                 "orden de atención y la muestra de pacientes que llega a consulta dentro del turno. "
                 "Los supuestos de llegada, recursos y conectividad son sintéticos.")

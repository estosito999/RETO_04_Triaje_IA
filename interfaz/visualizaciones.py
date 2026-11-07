"""Gráficas de un turno simulado y de la comparación entre estrategias."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ETAPAS = (
    "Espera de triaje",
    "En triaje",
    "Espera médica",
    "En consulta",
    "Atendido",
)
TRANSICIONES = (
    "inicio_triaje_min",
    "fin_triaje_min",
    "inicio_consulta_min",
    "fin_consulta_min",
)
PRIORIDADES = {1: "Alta (1)", 2: "Media (2)", 3: "Baja (3)"}
COLORES_PRIORIDAD = {1: "#dc5064", 2: "#d18927", 3: "#3282b8"}
MAX_PUNTOS_POR_ETAPA = 24


def vista_turno(pacientes: pd.DataFrame, minuto: float, *, asistido: bool = False,
                eventos: pd.DataFrame | None = None) -> go.Figure:
    """Reconstruye una instantánea del flujo a partir de sus marcas temporales."""
    presentes = pacientes.loc[
        (pacientes["llegada_min"] <= minuto) & (pacientes["estado"] != "no_llego")
    ].copy()
    presentes["etapa"] = 0
    for etapa, campo in enumerate(TRANSICIONES, start=1):
        presentes.loc[presentes[campo] <= minuto, "etapa"] = etapa
    asignadas = presentes["prioridad_asignada"].where(presentes["fin_triaje_min"] <= minuto)
    if asistido and eventos is not None and "prioridad_actual" in eventos:
        revisiones = eventos.loc[(eventos.evento == "reevaluacion") & (eventos.minuto <= minuto)]
        ultimas = revisiones.drop_duplicates("id_paciente", keep="last").set_index("id_paciente").prioridad_actual
        actuales = presentes.id_paciente.map(ultimas)
        asignadas = actuales.combine_first(asignadas)
    presentes["referencia_visible"] = presentes["prioridad_referencia"].map(PRIORIDADES)
    presentes["asignada_visible"] = asignadas.map(PRIORIDADES).fillna("Sin clasificar" if asistido else "No aplica en FIFO")
    presentes["prioridad_color"] = asignadas.fillna(0) if asistido else presentes["prioridad_referencia"]

    fig = go.Figure()
    muestras = []
    for etapa, nombre in enumerate(ETAPAS):
        grupo = presentes.loc[presentes["etapa"] == etapa].sort_values(["llegada_min", "id_paciente"])
        muestra = grupo.head(MAX_PUNTOS_POR_ETAPA).copy()
        posiciones = range(len(muestra))
        muestra["x"] = [etapa + (i % 4 - 1.5) * 0.13 for i in posiciones]
        muestra["y"] = [0.72 - (i // 4) * 0.115 for i in posiciones]
        muestra["nombre_etapa"] = nombre
        muestras.append(muestra)
        fig.add_vrect(x0=etapa - 0.46, x1=etapa + 0.46, fillcolor="rgba(80,134,166,0.10)",
                      line_width=0, layer="below")
        fig.add_annotation(x=etapa, y=0.91, text=str(len(grupo)), showarrow=False, font=dict(size=19))

    puntos = pd.concat(muestras, ignore_index=True)
    categorias = {0: "Sin clasificar", **PRIORIDADES} if asistido else PRIORIDADES
    for prioridad, nombre in categorias.items():
        grupo = puntos.loc[puntos["prioridad_color"] == prioridad]
        fig.add_trace(go.Scatter(
            x=grupo["x"], y=grupo["y"], mode="markers", name=nombre,
            text=grupo["id_paciente"].astype(str),
            customdata=grupo[["nombre_etapa", "referencia_visible", "asignada_visible"]].to_numpy(),
            marker=dict(color=COLORES_PRIORIDAD.get(prioridad, "#8a97a8"), size=9),
            hovertemplate="Paciente %{text}<br>%{customdata[0]}<br>Referencia sintética inicial · %{customdata[1]}"
                          "<br>Prioridad de cola · %{customdata[2]}<extra></extra>",
        ))

    fig.update_xaxes(range=[-0.5, len(ETAPAS) - 0.5], tickvals=list(range(len(ETAPAS))),
                     ticktext=("Espera de<br>triaje", "En triaje", "Espera<br>médica", "En consulta", "Atendido"),
                     showgrid=False, zeroline=False, fixedrange=True)
    fig.update_yaxes(range=[0, 1], visible=False, fixedrange=True)
    fig.update_layout(
        title=f"Flujo de pacientes · minuto {minuto:g}", height=340,
        legend=dict(title_text="Prioridad asignada" if asistido else "Prioridad sintética de referencia",
                    orientation="h", y=-0.22),
        margin=dict(l=12, r=12, t=52, b=80),
    )
    return fig


def cronologia(datos: pd.DataFrame) -> go.Figure:
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.12,
                        subplot_titles=("Flujo acumulado", "Colas y ocupación", "Teleconsulta asíncrona"))
    series = (
        (1, "llegados", "Llegadas acumuladas", "#3282b8", "solid"),
        (1, "atendidos", "Atendidos acumulados", "#188879", "solid"),
        (2, "cola_enfermeria", "Espera de triaje", "#3282b8", "solid"),
        (2, "enfermeros_ocupados", "Enfermeros ocupados", "#3282b8", "dash"),
        (2, "cola_medica", "Espera médica", "#dc5064", "solid"),
        (2, "medicos_ocupados", "Médicos ocupados", "#dc5064", "dash"),
        (3, "telependientes", "Teleconsultas pendientes", "#9c68c7", "solid"),
        (3, "telepor_enviar", "Por enviar", "#d18927", "dash"),
        (3, "teleesperando_respuesta", "Esperando respuesta", "#3282b8", "dash"),
        (3, "telerespondidas", "Respuestas acumuladas", "#188879", "solid"),
    )
    for fila, campo, nombre, color, trazo in series:
        fig.add_trace(go.Scatter(
            x=datos["minuto"], y=datos[campo], name=nombre, mode="lines",
            line=dict(color=color, dash=trazo, shape="hv"),
            hovertemplate="Minuto %{x:g} · %{y}<extra>%{fullData.name}</extra>",
        ), row=fila, col=1)

    for fila, unidad in enumerate(("Pacientes", "Personas", "Teleconsultas"), start=1):
        fig.update_yaxes(title_text=unidad, rangemode="tozero", row=fila, col=1)
    fig.update_xaxes(title_text="Minuto simulado", row=3, col=1)
    fig.update_layout(height=580, legend=dict(orientation="h", y=-0.16), margin=dict(l=14, r=18, t=38, b=94))
    return fig


def comparar_esperas(datos: pd.DataFrame) -> go.Figure:
    fig = make_subplots(rows=1, cols=2, subplot_titles=("Espera médica media", "Tiempo medio hasta atención"))
    colores = ("#3282b8", "#d18927", "#188879", "#9c68c7")
    for orden, (estrategia, grupo) in enumerate(datos.groupby("estrategia", sort=False)):
        grupo = grupo.set_index("prioridad_referencia").reindex(PRIORIDADES)
        for columna, campo in enumerate(("espera_medica_min", "tiempo_hasta_atencion_min"), start=1):
            fig.add_trace(go.Bar(
                x=list(PRIORIDADES.values()), y=grupo[campo], customdata=grupo["pacientes"].fillna(0),
                name=estrategia, legendgroup=estrategia, offsetgroup=estrategia, showlegend=columna == 1,
                marker_color=colores[orden % len(colores)],
                hovertemplate="%{x}<br>%{y:.1f} min<br>Consultas iniciadas · %{customdata}<extra>%{fullData.name}</extra>",
            ), row=1, col=columna)
    fig.update_xaxes(title_text="Prioridad sintética de referencia")
    fig.update_yaxes(title_text="Minutos", rangemode="tozero", matches="y")
    fig.update_layout(
        height=365, barmode="group", legend=dict(orientation="h", y=-0.24),
        margin=dict(l=14, r=18, t=45, b=82),
    )
    return fig


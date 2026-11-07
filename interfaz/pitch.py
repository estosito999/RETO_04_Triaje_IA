"""Pitch navegable de tres minutos, conectado al motor y a evidencia reproducible."""

from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analisis.evidencia_pitch import generar_evidencia, resumir_evidencia
from analisis.metricas import carga_ofrecida, comparar
from analisis.viabilidad import PresupuestoPiloto, evaluar_presupuesto, desglose_presupuesto, escenarios_escala
from interfaz.visualizaciones import vista_turno
from modelos.variables import Parametros
from simulacion.escenarios import ESCENARIOS
from simulacion.generador_datos import generar_trayectoria_conexion
from simulacion.motor import Experimento, simular


CAPITULOS = ("01 · Oportunidad", "02 · Solución", "03 · Arquitectura", "04 · Viabilidad", "05 · Impacto y escala")
TIEMPOS = ("0:00–0:25", "0:25–0:55", "0:55–1:35", "1:35–2:15", "2:15–3:00")
NOTAS = (
    "Cuando la demanda supera la capacidad, ordenar la cola cambia quién consigue una consulta y quién sigue esperando. "
    "Nuestro problema de ingeniería es hacer comprobables esas decisiones antes de llevarlas a una operación real.",
    "Construimos un laboratorio local que compara llegada y prioridad con los mismos pacientes simulados. "
    "Podemos variar demanda, personal y conexión. El clasificador actual es una regla transparente y configurable.",
    "El centro conserva clasificación y atención local. Una cola de envíos espera conexión y puede formar una cola remota. "
    "Cada punto es un paciente sintético. Comparamos ambas políticas con las mismas entradas y mostramos quién sigue esperando.",
    "El presupuesto es ilustrativo y corresponde a evaluación retrospectiva, no a atención médica. "
    "Con un centro, doce meses y equipo reutilizado: 10.672 bolivianos de inversión y 300 por mes, total 14.272. "
    "Estos son supuestos de planificación que requieren cotizaciones y acuerdos, no precios validados.",
    "En sobrecarga y 30 repeticiones: 16,6 casos altos menos sin iniciar consulta, IC 15,2 a 17,9 menos. "
    "La contrapartida son 23,7 casos bajos más pendientes. El intervalo de consultas completadas incluye cero: "
    "defendemos una redistribución del acceso en el modelo, no mayor capacidad. Si cambias escenario, usa las cifras de pantalla.",
)
TEAL, GRIS, ROJO = "#087F8C", "#687C8A", "#C4424E"
PLOTLY = {"displaylogo": False, "displayModeBar": False}


@st.cache_data(show_spinner=False, max_entries=24)
def _corrida(p: Parametros) -> Experimento:
    return simular(p)


@st.cache_data(show_spinner=False, max_entries=8)
def _evidencia(p: Parametros) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    datos, diferencias = generar_evidencia(p, repeticiones=30)
    return datos, diferencias, resumir_evidencia(datos, diferencias)


def _saltar(desplazamiento: int) -> None:
    actual = CAPITULOS.index(st.session_state.get("pitch_capitulo", CAPITULOS[0]))
    st.session_state.pitch_capitulo = CAPITULOS[min(max(actual + desplazamiento, 0), len(CAPITULOS)-1)]


def _tarjeta(numero: str, titulo: str, cuerpo: str) -> None:
    with st.container(border=True, height="stretch"):
        st.caption(numero)
        st.subheader(titulo)
        st.markdown(cuerpo)


def _problema() -> None:
    izquierda, derecha = st.columns([1.65, 1], gap="large", vertical_alignment="center")
    with izquierda:
        st.caption("UNA DECISIÓN DE INGENIERÍA")
        st.title("¿Quién sigue esperando al cerrar el turno?")
        st.markdown("Cuando la demanda supera la capacidad, **el orden de atención cambia quién accede a una consulta**.")
        st.markdown("UMBRAL permite ensayar esa decisión, observar sus costos y conservar la evidencia.")
    with derecha:
        with st.container(border=True):
            st.caption("EL EXPERIMENTO")
            st.subheader("Mismo turno. Dos políticas.")
            st.markdown("**FIFO** atiende por llegada a la cola médica.\n\n"
                        "**Triaje asistido** atiende por prioridad asignada.")
            st.caption("Mismos pacientes sintéticos, personal y duraciones en cada comparación.")
    st.caption("Prototipo de simulación local. Los resultados presentados describen un centro ficticio.")


def _propuesta() -> None:
    st.title("Una decisión local. Una solicitud que puede esperar conexión.")
    st.markdown("Un entorno para probar **priorización, capacidad y teleconsulta** antes de diseñar un piloto.")
    a, b, c = st.columns(3, gap="medium")
    with a:
        _tarjeta("01 / EN EL CENTRO", "Evaluar", "Una regla explicable combina señales sintéticas y asigna prioridad. Se ejecuta localmente.")
    with b:
        _tarjeta("02 / CON LOS RECURSOS DISPONIBLES", "Ordenar", "La cola respeta la capacidad del personal. Una consulta iniciada continúa hasta terminar.")
    with c:
        _tarjeta("03 / CUANDO HAY CONEXIÓN", "Consultar", "La solicitud permanece pendiente, reintenta su envío y puede esperar un especialista remoto.")
    st.markdown("**La entrega actual:** motor reproducible, comparación interactiva y registros para auditar cada resultado.")
    st.caption("La teleconsulta está simulada. El clasificador actual usa reglas; incorporar un modelo validado es una etapa futura.")


def _demo() -> None:
    st.title("Una arquitectura local que conserva la solicitud.")
    st.markdown("**Centro de salud:** enfermería, clasificación y consulta. **Enlace:** cola de envíos y reintentos. "
                "**Servicio remoto:** especialistas con capacidad configurable.")
    a, b, c = st.columns([1.7, 1, 1], vertical_alignment="bottom")
    with a:
        escenario = st.selectbox("Escenario de demostración", list(ESCENARIOS), index=1, key="pitch_escenario")
    base = ESCENARIOS[escenario]
    with b:
        medicos = st.slider("Médicos disponibles", 1, 6, min(base.medicos, 6), key=f"pitch_medicos_{escenario}")
    with c:
        conexion = st.slider("Disponibilidad de conexión (%)", 0, 100, round(base.disponibilidad_conexion*100),
                             key=f"pitch_conexion_{escenario}")
    p = replace(base, medicos=medicos, disponibilidad_conexion=conexion/100)
    exp = _corrida(p)
    minuto = st.slider("Momento del turno (min)", 0, p.turno_min, p.turno_min, step=5,
                       key=f"pitch_minuto_{escenario}")
    izquierda, derecha = st.columns(2, gap="large")
    for columna, nombre, resultado, asistido in (
        (izquierda, "Orden de llegada", exp.referencia, False),
        (derecha, "Prioridad asistida", exp.asistido, True),
    ):
        with columna:
            st.subheader(nombre)
            presentes = resultado.pacientes.loc[resultado.pacientes.llegada_min <= minuto]
            pendientes = presentes.inicio_consulta_min.isna() | (presentes.inicio_consulta_min > minuto)
            altas = int(((presentes.prioridad_referencia == 1) & pendientes).sum())
            completas = int((presentes.fin_consulta_min <= minuto).sum())
            tarjetas = st.columns(2)
            tarjetas[0].metric("Alta inicial sin consulta", altas, border=True)
            tarjetas[1].metric("Consultas completadas", completas, border=True)
            figura = vista_turno(resultado.pacientes, minuto, asistido=asistido, eventos=resultado.eventos)
            figura.update_layout(height=290, margin=dict(l=4, r=4, t=42, b=65), font=dict(size=12))
            st.plotly_chart(figura, config=PLOTLY, width="stretch", key=f"pitch_flujo_{nombre}",
                            alt=f"Pacientes en cada etapa con la política {nombre} en el minuto {minuto}")
    comparacion = comparar(exp)
    with st.container(horizontal=True):
        st.caption(f"Una corrida / semilla {p.semilla} / llegadas hasta {p.turno_min} min / carga nominal local ρ={carga_ofrecida(p):.2f}.")
        st.caption(f"Teleconsultas pendientes al cierre: FIFO {int(comparacion.loc['FIFO', 'teleconsultas_pendientes_al_cierre'])}; "
                   f"asistido {int(comparacion.loc['Triaje asistido', 'teleconsultas_pendientes_al_cierre'])}.")
    if p.conexion_compartida:
        estado = generar_trayectoria_conexion(p).conectada(minuto)
        st.caption("Conexión compartida en este instante: " + ("disponible." if estado else "interrumpida."))
    st.caption("Los colores muestran la referencia inicial en FIFO y la prioridad de cola en asistido. "
               "Los contadores de alta usan la referencia inicial en ambas políticas. "
               "El dibujo muestra hasta 24 casos por etapa; los contadores incluyen todos. "
               "La solicitud remota es paralela: en estos escenarios, cambiar la conexión no modifica la atención local.")


def _fila(tabla: pd.DataFrame, metrica: str) -> pd.Series:
    return tabla.loc[tabla.metrica == metrica].iloc[0]


def _intervalo(fila: pd.Series) -> str:
    if pd.isna(fila.ic95_inferior):
        return "Sin suficientes pares para estimar un intervalo."
    return f"IC 95 % [{fila.ic95_inferior:+.2f}, {fila.ic95_superior:+.2f}] / {int(fila.pares_validos)} pares."


def _bosque(tabla: pd.DataFrame) -> go.Figure:
    seleccion = [
        ("pendientes_sin_consulta_alta_al_cierre", "Alta prioridad", TEAL),
        ("pendientes_sin_consulta_baja_al_cierre", "Baja prioridad", ROJO),
    ]
    fig = go.Figure()
    for metrica, nombre, color in seleccion:
        fila = _fila(tabla, metrica)
        if pd.isna(fila.ic95_inferior):
            continue
        fig.add_trace(go.Scatter(
            x=[fila.diferencia_media], y=[nombre], mode="markers", name=nombre,
            marker=dict(size=16, color=color),
            error_x=dict(type="data", array=[fila.ic95_superior-fila.diferencia_media],
                         arrayminus=[fila.diferencia_media-fila.ic95_inferior], color=color, thickness=3, width=8),
            hovertemplate="%{y}<br>Diferencia media: %{x:.2f} casos por turno<extra></extra>",
        ))
    fig.add_vline(x=0, line_color=GRIS, line_dash="dash", line_width=1)
    fig.update_layout(height=235, showlegend=False, margin=dict(l=8, r=25, t=15, b=45),
                      xaxis_title="Cambio en casos sin iniciar consulta al cierre (asistido − FIFO)",
                      yaxis=dict(autorange="reversed"), font=dict(size=16))
    return fig


def _paquete(datos: pd.DataFrame, diferencias: pd.DataFrame, tabla: pd.DataFrame) -> bytes:
    memoria = BytesIO()
    with ZipFile(memoria, "w", ZIP_DEFLATED) as archivo:
        for nombre, df in (("mediciones", datos), ("diferencias", diferencias), ("resumen", tabla)):
            archivo.writestr(nombre+".csv", df.to_csv(index=False).encode("utf-8-sig"))
        archivo.writestr("metadatos.json", json.dumps(datos.attrs["metadatos"], ensure_ascii=False, indent=2))
        archivo.writestr("LEEME.txt", "Resultados sintéticos. Diferencia=asistido-FIFO. Métricas al cierre. "
                         "Medias entre turnos; intervalos puntuales del 95 %, sin corrección múltiple. "
                         "Consultar denominadores, pares faltantes y parámetros antes de interpretar.")
    return memoria.getvalue()


def _resultados() -> None:
    st.title("Impacto esperado, con una contrapartida explícita.")
    st.caption("SEÑAL DEL EXPERIMENTO PARA ORIENTAR UN PILOTO / DATOS SINTÉTICOS")
    escenario = st.selectbox("Escenario de evidencia", list(ESCENARIOS), index=1, key="pitch_evidencia_escenario")
    p = ESCENARIOS[escenario]
    with st.spinner("Repitiendo el escenario con 30 semillas…"):
        datos, diferencias, tabla = _evidencia(p)
    alta = _fila(tabla, "pendientes_sin_consulta_alta_al_cierre")
    baja = _fila(tabla, "pendientes_sin_consulta_baja_al_cierre")
    capacidad = _fila(tabla, "pacientes_atendidos_al_cierre")
    a, b, c = st.columns(3)
    for columna, titulo, fila in ((a, "Alta sin consulta", alta), (b, "Baja sin consulta", baja),
                                  (c, "Consultas completadas", capacidad)):
        with columna:
            st.metric(titulo, f"{fila.diferencia_media:+.1f}", border=True)
            st.caption("Casos por turno, asistido − FIFO. " + _intervalo(fila))
    st.plotly_chart(_bosque(tabla), width="stretch", config=PLOTLY,
                    alt="Diferencias de pendientes por prioridad con intervalos del 95 por ciento y línea de cero")
    if pd.notna(capacidad.ic95_inferior) and capacidad.ic95_inferior <= 0 <= capacidad.ic95_superior:
        st.markdown("**El intervalo de consultas completadas incluye cero.** La evidencia de este escenario "
                    "sostiene una redistribución del acceso; no demuestra un aumento de capacidad.")
    else:
        st.markdown("**La capacidad y los pendientes se evalúan por separado.** Un resultado de este escenario "
                    "no acredita una mejora en otros centros o poblaciones.")
    st.caption(f"30 turnos sintéticos / semillas {p.semilla}–{p.semilla+29} / parámetros originales del escenario / "
               "corte al finalizar las llegadas. La demo tiene controles independientes. "
               "Los IC son puntuales y no incluyen incertidumbre de calibración.")
    st.markdown("**Escalamiento propuesto:** validar con un centro aliado, replicar con parámetros locales "
                "y evaluar una integración clínica independiente. El objetivo es mejorar el acceso prioritario "
                "con un costo de espera visible para los demás grupos.")
    st.caption("Buscamos un centro colaborador y acompañamiento de ingeniería y salud. "
               "Acordaríamos criterios de aceptación antes de analizar los datos del piloto.")
    with st.expander("Examinar medias, errores y denominadores"):
        columnas = {"etiqueta": "Métrica", "unidad": "Unidad", "fifo_media": "FIFO: media",
            "asistido_media": "Asistido: media", "diferencia_media": "Diferencia", "pares_validos": "Pares válidos",
            "ic95_inferior": "IC inferior", "ic95_superior": "IC superior", "denominador": "Población observada"}
        st.dataframe(tabla[list(columnas)].rename(columns=columnas), hide_index=True, width="stretch",
                     alt="Evidencia completa con medias, muestras y denominadores")
        sensibilidad = _fila(tabla, "sensibilidad_alta_pct_al_cierre")
        st.markdown(f"**Sensibilidad alta del clasificador: {sensibilidad.asistido_media:.1f} %**, media entre turnos "
                    "con observaciones. Es recuperación de etiquetas sintéticas y no precisión clínica. FIFO no clasifica.")
        st.caption("Una espera menor entre quienes sí iniciaron puede esconder más pendientes. "
                   "Las métricas acumuladas incluyen a todos los llegados, con tiempo observado hasta consulta o corte.")
    st.download_button("Descargar evidencia reproducible", _paquete(datos, diferencias, tabla),
                       "umbral_evidencia.zip", "application/zip", key="pitch_descarga_evidencia", on_click="ignore")


def _metodo() -> None:
    st.subheader("Cada comparación tiene una explicación y un registro.")
    a, b = st.columns(2, gap="large")
    with a:
        _tarjeta("CONTROL", "Las mismas entradas", "Cada par conserva pacientes, servicios y personal. "
                 "La diferencia surge de la política y su interacción con las colas.")
        _tarjeta("INCERTIDUMBRE", "Treinta realizaciones", "Semillas declaradas antes de simular. "
                 "Diferencias emparejadas e intervalos puntuales del 95 %.")
    with b:
        _tarjeta("MODELO", "Recursos y eventos", "Llegadas Poisson, servicios Gamma y conexión Markoviana opcional. "
                 "Capacidad limitada y consultas sin interrupción.")
        _tarjeta("TRAZABILIDAD", "También cuenta quien espera", "Pendientes y tiempos observados al cierre. "
                 "Parámetros, eventos y muestras disponibles para revisión.")
    with st.expander("Abrir ecuaciones y alcance de la evidencia"):
        st.latex(r"S=0.70A+0.30B\qquad \rho=\frac{\lambda\,\mathbb{E}[T]}{60c}")
        st.markdown("El puntaje base asigna alta desde 0.78 y media desde 0.54. A y B son señales artificiales. "
                    "ρ compara demanda nominal de servicio local con capacidad; no incluye retención por teleconsulta.")
        st.latex(r"\overline{D}\;\pm\;t_{0.975,n-1}\frac{s_D}{\sqrt{n}},\quad D_r=M_{asistido,r}-M_{FIFO,r}")
        st.markdown("El intervalo describe diferencias entre turnos con parámetros fijos. Grupos sin observaciones "
                    "quedan vacíos. No cubre errores del modelo ni valida resultados clínicos.")
        st.caption("PCG64 genera las entradas. SimPy calcula las esperas por eventos y recursos. "
                   "Los diagnósticos de uniformidad y dependencia son comprobaciones parciales, no pruebas de realismo.")
    st.caption("La validación externa sigue pendiente: la referencia, las señales y los costos actuales son sintéticos.")


def _defensa() -> None:
    preguntas = {
        "¿Dónde está la IA?": "Hoy usamos una regla parametrizable. Entrenar y validar un clasificador con referencia "
                              "independiente es una etapa futura. El valor demostrado es el entorno para comparar decisiones.",
        "¿La pseudoaleatoriedad fabrica la mejora?": "Fabrica entradas sintéticas compartidas por ambas políticas. "
            "Las esperas se calculan por recursos y eventos. Se declaran semillas y se muestra beneficio y contrapartida. "
            "La validez fuera de esos supuestos necesita datos independientes.",
        "¿Una prioridad mal asignada puede quedar relegada?": "Sí en el modelo. Por eso conservamos referencia y "
            "asignación, subtriaje, sensibilidad y pendientes por grupo. No estamos midiendo daño clínico.",
        "¿Ya hace teleconsultas reales?": "No. Modela solicitudes, reintentos y atención remota. "
            "La integración con un servicio sanitario requiere un desarrollo y evaluación posteriores.",
        "¿Por qué mostrar que empeora la espera de otro grupo?": "Porque priorizar redistribuye un recurso limitado. "
            "Ocultar pendientes o presentar solo promedios de atendidos impediría evaluar el costo de esa decisión.",
        "¿Qué demostraría el piloto?": "Primero, si el modelo reproduce el funcionamiento observado con la precisión "
            "acordada antes del análisis. No se plantean aún resultados clínicos, adopción ni ahorro económico demostrados.",
    }
    with st.expander("Preguntas del jurado"):
        for pregunta, respuesta in preguntas.items():
            st.markdown(f"**{pregunta}**\n\n{respuesta}")
    guion = Path(__file__).resolve().parents[1] / "PITCH.md"
    st.download_button("Descargar guion de 3 minutos y defensa", guion.read_bytes(), "UMBRAL_pitch_3_minutos.md",
                       "text/markdown", key="pitch_descarga_guion", on_click="ignore")


def _viabilidad() -> None:
    st.title("Un piloto acotado. Un presupuesto que se puede revisar.")
    st.caption("ESCENARIO ILUSTRATIVO EN BOLIVIANOS / SIN COTIZACIONES / EVALUACIÓN RETROSPECTIVA")
    a, b, c = st.columns(3, vertical_alignment="bottom")
    centros = a.slider("Centros en el piloto", 1, 10, 1, key="pitch_fin_centros")
    meses = b.slider("Horizonte presupuestado (meses)", 1, 24, 12, key="pitch_fin_meses")
    reutilizar = c.checkbox("Reutilizar equipo disponible", True, key="pitch_fin_reutilizar")
    base = PresupuestoPiloto()
    valores = {}
    with st.expander("Revisar y editar los supuestos del presupuesto"):
        izquierda, derecha = st.columns(2)
        campos = (
            ("horas_desarrollo", "Desarrollo y ajuste central (h)"),
            ("tarifa_tecnica_bs", "Tarifa técnica supuesta (Bs/h)"),
            ("equipo_por_centro_bs", "Equipo nuevo por centro (Bs)"),
            ("horas_datos_por_centro", "Preparación de datos por centro (h)"),
            ("horas_revision_por_centro", "Revisión profesional por centro (h)"),
            ("tarifa_revision_bs", "Tarifa de revisión supuesta (Bs/h)"),
            ("horas_capacitacion_por_centro", "Capacitación por centro (h)"),
            ("operacion_fija_mensual_bs", "Soporte fijo mensual del laboratorio (Bs)"),
            ("operacion_por_centro_mensual_bs", "Soporte mensual por centro (Bs)"),
            ("contingencia_pct", "Contingencia de inversión (%)"),
        )
        for i, (campo, etiqueta) in enumerate(campos):
            with (izquierda if i % 2 == 0 else derecha):
                valores[campo] = st.number_input(etiqueta, min_value=0.0, value=float(getattr(base, campo)),
                                                 key=f"pitch_fin_{campo}")
        st.caption("La contingencia se aplica a la inversión inicial. La operación contempla soporte del laboratorio; "
                   "no estima una prestación médica ni una integración operativa real.")
    try:
        p = PresupuestoPiloto(centros=centros, meses=meses, reutilizar_equipo=reutilizar, **valores)
        presupuesto = evaluar_presupuesto(p)
    except ValueError as error:
        st.error(f"Revisa los supuestos: {error}")
        return
    a, b, c = st.columns(3)
    a.metric("Inversión inicial", f"Bs {presupuesto['inversion_inicial_bs']:,.0f}", border=True)
    b.metric("Operación mensual", f"Bs {presupuesto['operacion_mensual_bs']:,.0f}", border=True)
    c.metric(f"Total de {meses} meses", f"Bs {presupuesto['total_horizonte_bs']:,.0f}", border=True)
    st.markdown("**Implementación propuesta:** acuerdo con un centro, ajuste con registros completos y contraste "
                "en turnos reservados. Los criterios se fijan con profesionales antes de evaluar resultados.")
    st.caption("No se presentan ahorros, ingresos ni retorno de inversión demostrados. Atención médica, "
               "integraciones clínicas y sus costos adicionales deben presupuestarse en una etapa posterior.")
    with st.expander("Desglose y proyección al replicar centros"):
        st.dataframe(desglose_presupuesto(p).rename(columns={"concepto": "Concepto", "categoria": "Categoría",
                     "base_calculo": "Cálculo", "importe_bs": "Importe (Bs)"}), hide_index=True,
                     width="stretch", alt="Presupuesto ilustrativo con base de cálculo por concepto")
        st.dataframe(escenarios_escala(p).rename(columns={"centros": "Centros", "meses": "Meses",
                     "inversion_inicial_bs": "Inversión inicial (Bs)", "operacion_mensual_bs": "Operación mensual (Bs)",
                     "total_horizonte_bs": "Total (Bs)", "costo_por_centro_bs": "Total por centro (Bs)"}),
                     hide_index=True, width="stretch", alt="Proyección de costos para uno, tres, cinco y diez centros")
        st.caption("Esta proyección prorratea costos fijos bajo los mismos supuestos. No demuestra capacidad técnica "
                   "a escala, rentabilidad ni efectos clínicos.")
        st.download_button("Descargar presupuesto ilustrativo", desglose_presupuesto(p).to_csv(index=False).encode("utf-8-sig"),
                           "umbral_presupuesto_ilustrativo.csv", "text/csv", key="pitch_descarga_presupuesto", on_click="ignore")


def mostrar_pitch() -> None:
    st.caption("UMBRAL / RETO 04 / PROTOTIPO EXPERIMENTAL")
    capitulo = st.segmented_control("Capítulos del pitch", CAPITULOS, default=CAPITULOS[0], required=True,
                                    key="pitch_capitulo", label_visibility="collapsed", width="stretch")
    indice = CAPITULOS.index(capitulo or CAPITULOS[0])
    st.caption(f"Diapositiva {indice+1} de 5 / Guion de 3 minutos / {TIEMPOS[indice]}")
    (_problema, _propuesta, _demo, _viabilidad, _resultados)[indice]()
    st.space("small")
    anterior, centro, siguiente = st.columns([1, 3, 1], vertical_alignment="center")
    anterior.button("Anterior", key="pitch_anterior", disabled=indice == 0,
                    on_click=_saltar, args=(-1,), width="stretch")
    centro.progress((indice+1)/5, text="Datos sintéticos. Resultados auditables. Validación externa pendiente.")
    siguiente.button("Siguiente", key="pitch_siguiente", disabled=indice == len(CAPITULOS)-1,
                     on_click=_saltar, args=(1,), type="primary", width="stretch")
    with st.expander("Notas para presentar este capítulo"):
        st.markdown(NOTAS[indice])
        st.caption("El guion completo y las respuestas de defensa se descargan en el anexo de preguntas.")
    with st.expander("Anexo para preguntas: método, límites y defensa"):
        _metodo()
        _defensa()
    carpeta = Path(__file__).resolve().parents[1] / "pitch_entregable"
    archivos = [("PDF de 5 diapositivas", "pdf", "application/pdf"),
                ("PowerPoint editable", "pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")]
    disponibles = [(etiqueta, carpeta/f"UMBRAL_pitch_ejecutivo.{extension}", mime) for etiqueta, extension, mime in archivos
                   if (carpeta/f"UMBRAL_pitch_ejecutivo.{extension}").exists()]
    if disponibles:
        with st.container(horizontal=True):
            for etiqueta, archivo, mime in disponibles:
                st.download_button(etiqueta, archivo.read_bytes(), archivo.name, mime,
                                   key=f"pitch_archivo_{archivo.suffix}", on_click="ignore")
        st.caption("Los archivos descargables usan el presupuesto ilustrativo base; los controles interactivos no los modifican.")

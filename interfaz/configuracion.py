import streamlit as st

from modelos.variables import Parametros
from simulacion.escenarios import ESCENARIOS


def _lista_numeros(texto: str) -> tuple[float, ...]:
    return tuple(float(valor.strip()) for valor in texto.split(",")) if texto.strip() else ()


def panel() -> Parametros | None:
    with st.sidebar:
        st.header("B · Configuración")
        escenarios = dict(ESCENARIOS)
        if "configuracion_calibrada" in st.session_state:
            escenarios["Datos ajustados"] = st.session_state.configuracion_calibrada
        if st.session_state.pop("seleccionar_ajuste", False):
            for clave in list(st.session_state):
                if clave.endswith("_Datos ajustados"):
                    del st.session_state[clave]
            st.session_state.escenario = "Datos ajustados"
        escenario = st.selectbox("Escenario", list(escenarios), key="escenario")
        base = escenarios[escenario]
        with st.form(f"configuracion_{escenario}"):
            semilla = st.number_input("Semilla", 0, 2**32 - 1, base.semilla, key=f"semilla_{escenario}")
            pacientes = st.number_input("Cantidad de pacientes generados", 1, 500, base.pacientes,
                                        key=f"pacientes_{escenario}")
            frecuencia = st.number_input("Llegadas por hora", 0.5, 60.0, base.llegadas_por_hora, 0.5,
                                         key=f"llegadas_{escenario}")
            medicos = st.number_input("Médicos", 1, 16, base.medicos, key=f"medicos_{escenario}")
            enfermeros = st.number_input("Enfermeros", 1, 16, base.enfermeros, key=f"enfermeros_{escenario}")
            duracion = st.number_input("Duración media de consulta (min)", 2.0, 60.0, base.duracion_consulta_min,
                                       key=f"consulta_{escenario}")
            prioritarios = st.slider("Casos prioritarios (%)", 0, 100, round(base.proporcion_prioritarios * 100),
                                     key=f"prioritarios_{escenario}")
            demora = st.number_input("Respuesta remota media (min)", 0.0, 240.0, base.respuesta_remota_min,
                                     key=f"respuesta_{escenario}")
            conexion = st.slider("Disponibilidad de conexión (%)", 0, 100,
                                  round(base.disponibilidad_conexion * 100), key=f"conexion_{escenario}")
            reintento = st.number_input("Intervalo de reintento de envío (min)", 1.0, 60.0,
                                        base.intervalo_reintento_min, key=f"reintento_{escenario}")
            horas = st.number_input("Duración del turno (h)", 1, 24, base.horas_turno, key=f"horas_{escenario}")
            with st.expander("Demanda y tiempos de atención"):
                fraccion_alta = st.slider("Prioridad alta entre los casos prioritarios (%)", 0, 100,
                                          round(base.fraccion_alta_prioritarios * 100), key=f"fraccion_alta_{escenario}")
                continuas = st.checkbox("Generar llegadas hasta el cierre", base.generar_hasta_cierre,
                                        key=f"continuas_{escenario}",
                                        help="Desactiva el cupo de pacientes generados; las llegadas se cierran al terminar el turno.")
                perfil = st.text_input("Factores de llegada por hora", ", ".join(map(str, base.perfil_llegadas)),
                                       key=f"perfil_{escenario}",
                                       help="Un factor entre 0 y 5 por cada hora, separado por comas. Vacío: tasa constante. Usa punto decimal.")
                medias = st.text_input("Consulta media por prioridad: alta, media, baja (min)",
                                       ", ".join(map(str, base.medias_consulta_prioridad)), key=f"medias_{escenario}",
                                       help="Tres medias separadas por comas. Vacío: media común del panel principal.")
                media_triaje = st.number_input("Evaluación de enfermería media (min)", min(0.1, float(base.triaje_medio_min)), 240.0,
                                               float(base.triaje_medio_min), key=f"media_triaje_{escenario}")
                forma_triaje = st.number_input("Forma Gamma de enfermería", min(0.1, float(base.forma_triaje)), 10000.0,
                                               float(base.forma_triaje), key=f"forma_triaje_{escenario}",
                                               help="A igual media, una forma mayor reduce la variabilidad.")
                forma_consulta = st.number_input("Forma Gamma de medicina", min(0.1, float(base.forma_consulta)), 10000.0,
                                                 float(base.forma_consulta), key=f"forma_consulta_{escenario}")
            with st.expander("Conexión, especialistas y seguimiento"):
                compartida = st.checkbox("Cortes de conexión compartidos por todo el centro", base.conexion_compartida,
                                         key=f"compartida_{escenario}")
                persistencia = st.number_input("Escala temporal de la conexión (min)", 0.1, 240.0,
                                                float(base.persistencia_conexion_min), key=f"persistencia_{escenario}",
                                                help="Controla la persistencia de los estados conectado y desconectado. La disponibilidad fija su proporción media.")
                especialistas = st.number_input("Especialistas remotos (0 = sin límite)", 0, 16,
                                                 base.especialistas_remotos, key=f"especialistas_{escenario}")
                esperar = st.checkbox("Mantener al médico ocupado hasta la respuesta remota", base.esperar_teleconsulta,
                                      key=f"esperar_{escenario}",
                                      help="Si se activa y no llega respuesta, la consulta sigue ocupando al médico hasta el fin de la observación.")
                seguimiento = st.number_input("Seguimiento después del cierre (min)", 0.0, 1440.0,
                                                float(base.seguimiento_min), key=f"seguimiento_{escenario}",
                                                help="Sigue atendiendo y observando respuestas, sin admitir nuevas llegadas.")
                deterioro = st.number_input("Reevaluar prioridad en espera cada (min; 0 = desactivado)", 0.0, 240.0,
                                             float(base.deterioro_cada_min), key=f"deterioro_{escenario}",
                                             help="Regla educativa: cada intervalo sube un nivel la prioridad de la cola asistida, hasta alta. No es un modelo clínico de deterioro.")
            with st.expander("Regla de clasificación"):
                peso = st.slider("Peso de la señal A", 0.0, 1.0, float(base.peso_senal_a), 0.05,
                                 key=f"peso_{escenario}")
                umbral_alto = st.number_input("Umbral de prioridad alta", 0.01, 1.0,
                                               float(base.umbral_alto), 0.01, key=f"alto_{escenario}")
                umbral_medio = st.number_input("Umbral de prioridad media", 0.0, 0.99,
                                                float(base.umbral_medio), 0.01, key=f"medio_{escenario}")
            aplicar = st.form_submit_button("Preparar experimento", type="primary", width="stretch")
        st.caption("Los pacientes cuya llegada está prevista después del cierre quedan fuera del turno observado.")
        if aplicar:
            try:
                return Parametros(
                    semilla=semilla, pacientes=pacientes, llegadas_por_hora=frecuencia, medicos=medicos,
                    enfermeros=enfermeros, duracion_consulta_min=duracion, proporcion_prioritarios=prioritarios / 100,
                    respuesta_remota_min=demora, disponibilidad_conexion=conexion / 100, horas_turno=horas,
                    intervalo_reintento_min=reintento, generar_hasta_cierre=continuas,
                    perfil_llegadas=_lista_numeros(perfil), medias_consulta_prioridad=_lista_numeros(medias),
                    triaje_medio_min=media_triaje, forma_triaje=forma_triaje, forma_consulta=forma_consulta,
                    conexion_compartida=compartida, persistencia_conexion_min=persistencia,
                    especialistas_remotos=especialistas, esperar_teleconsulta=esperar,
                    seguimiento_min=seguimiento, deterioro_cada_min=deterioro,
                    fraccion_alta_prioritarios=fraccion_alta / 100,
                    peso_senal_a=peso, umbral_alto=umbral_alto, umbral_medio=umbral_medio,
                )
            except ValueError as error:
                st.error(f"Revisa la configuración: {error}")
    return None

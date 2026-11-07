from modelos.variables import Parametros
from modelos.distribuciones import TABLA_INTERARRIBOS, TABLA_SERVICIOS, media_frecuencias

PARAMETROS_LABORATORIO = Parametros(
    semilla=42,
    pacientes=100,
    llegadas_por_hora=60 / media_frecuencias(TABLA_INTERARRIBOS),
    medicos=2,
    enfermeros=1,
    duracion_consulta_min=media_frecuencias(TABLA_SERVICIOS),
    triaje_medio_min=4,
    forma_triaje=6,
    forma_consulta=8,
    horas_turno=24,
    proporcion_prioritarios=0.30,
    fraccion_alta_prioritarios=0.40,
    respuesta_remota_min=45,
    disponibilidad_conexion=0.85,
    intervalo_reintento_min=5,
    generar_hasta_cierre=False,
    perfil_llegadas=(),
    usar_tablas_frecuencia=True,
    medias_consulta_prioridad=(),
    conexion_compartida=False,
    especialistas_remotos=0,
    esperar_teleconsulta=False,
    deterioro_cada_min=0,
    seguimiento_min=0,
    peso_senal_a=0.70,
    umbral_alto=0.78,
    umbral_medio=0.54,
)
REPETICIONES_LABORATORIO = 30

ESCENARIOS = {
    "Turno habitual": Parametros(),
    "Sobrecarga de llegadas": Parametros(
        pacientes=180, llegadas_por_hora=26, medicos=2, enfermeros=2,
        duracion_consulta_min=20, proporcion_prioritarios=0.40,
    ),
    "Conexión intermitente": Parametros(
        pacientes=110, llegadas_por_hora=15, medicos=3, enfermeros=2,
        disponibilidad_conexion=0.28, respuesta_remota_min=80, proporcion_prioritarios=0.35,
    ),
    "Demanda variable y cortes compartidos": Parametros(
        pacientes=400, llegadas_por_hora=18, medicos=3, enfermeros=2,
        perfil_llegadas=(0.6, 1.0, 1.8, 1.5, 1.0, 0.8, 0.7, 0.6),
        medias_consulta_prioridad=(24.0, 18.0, 12.0), proporcion_prioritarios=0.40,
        conexion_compartida=True, disponibilidad_conexion=0.60, persistencia_conexion_min=20,
        especialistas_remotos=2, respuesta_remota_min=30, deterioro_cada_min=30,
    ),
}

from modelos.variables import Parametros

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

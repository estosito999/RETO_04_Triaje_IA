from dataclasses import dataclass
from math import isfinite
from numbers import Real

ALTA, MEDIA, BAJA = 1, 2, 3
PRIORIDADES = {ALTA: "Alta", MEDIA: "Media", BAJA: "Baja"}
UMBRAL_ALTO_REFERENCIA = 0.80
UMBRAL_MEDIO_REFERENCIA = 0.55
UMBRAL_ALTO_ASISTIDO = 0.78
UMBRAL_MEDIO_ASISTIDO = 0.54
PESO_SENAL_A = 0.70
TRIAJE_MEDIO_MIN = 4.0
PASO_VISUAL_MIN = 5


@dataclass(frozen=True)
class Parametros:
    semilla: int = 42
    pacientes: int = 90
    llegadas_por_hora: float = 12.0
    medicos: int = 3
    enfermeros: int = 2
    duracion_consulta_min: float = 16.0
    proporcion_prioritarios: float = 0.30
    respuesta_remota_min: float = 45.0
    disponibilidad_conexion: float = 0.85
    intervalo_reintento_min: float = 5.0
    horas_turno: int = 8
    perfil_llegadas: tuple[float, ...] = ()
    generar_hasta_cierre: bool = False
    triaje_medio_min: float = TRIAJE_MEDIO_MIN
    forma_triaje: float = 6.0
    forma_consulta: float = 8.0
    medias_consulta_prioridad: tuple[float, ...] = ()
    conexion_compartida: bool = False
    persistencia_conexion_min: float = 20.0
    especialistas_remotos: int = 0
    esperar_teleconsulta: bool = False
    deterioro_cada_min: float = 0.0
    peso_senal_a: float = PESO_SENAL_A
    umbral_alto: float = UMBRAL_ALTO_ASISTIDO
    umbral_medio: float = UMBRAL_MEDIO_ASISTIDO
    seguimiento_min: float = 0.0
    fraccion_alta_prioritarios: float = 0.40
    usar_tablas_frecuencia: bool = False

    def __post_init__(self) -> None:
        enteros = (
            (self.semilla, 0, 2**32 - 1, "semilla"),
            (self.pacientes, 1, 500, "pacientes"),
            (self.medicos, 1, 16, "médicos"),
            (self.enfermeros, 1, 16, "enfermeros"),
            (self.horas_turno, 1, 24, "horas del turno"),
            (self.especialistas_remotos, 0, 1000, "especialistas remotos"),
        )
        for valor, minimo, maximo, nombre in enteros:
            if type(valor) is not int or not minimo <= valor <= maximo:
                raise ValueError(f"El valor de {nombre} debe ser un entero entre {minimo} y {maximo}.")
        rangos = (
            (self.llegadas_por_hora, 0.5, 60, "llegadas por hora"),
            (self.duracion_consulta_min, 2, 60, "duración de consulta"),
            (self.proporcion_prioritarios, 0, 1, "proporción de prioridades alta y media"),
            (self.respuesta_remota_min, 0, 240, "demora remota"),
            (self.disponibilidad_conexion, 0, 1, "disponibilidad de conexión"),
            (self.intervalo_reintento_min, 1, 60, "intervalo de reintento"),
            (self.peso_senal_a, 0, 1, "peso de la señal A"),
            (self.umbral_alto, 0, 1, "umbral alto"),
            (self.umbral_medio, 0, 1, "umbral medio"),
            (self.deterioro_cada_min, 0, 10080, "intervalo de deterioro"),
            (self.seguimiento_min, 0, 10080, "seguimiento posterior al turno"),
            (self.fraccion_alta_prioritarios, 0, 1, "fracción alta entre prioritarios"),
        )
        for valor, minimo, maximo, nombre in rangos:
            if not isinstance(valor, Real) or not isfinite(valor) or not minimo <= valor <= maximo:
                raise ValueError(f"El valor de {nombre} debe estar entre {minimo} y {maximo}.")
        positivos = (
            (self.triaje_medio_min, 240, "duración media del triaje"),
            (self.forma_triaje, 10000, "forma gamma de triaje"),
            (self.forma_consulta, 10000, "forma gamma de consulta"),
            (self.persistencia_conexion_min, 10080, "persistencia de la conexión"),
        )
        for valor, maximo, nombre in positivos:
            if not isinstance(valor, Real) or not isfinite(valor) or not 0 < valor <= maximo:
                raise ValueError(f"El valor de {nombre} debe ser positivo y como máximo {maximo}.")
        if self.umbral_medio >= self.umbral_alto:
            raise ValueError("El umbral medio debe ser menor que el umbral alto.")
        for nombre in ("generar_hasta_cierre", "conexion_compartida", "esperar_teleconsulta", "usar_tablas_frecuencia"):
            if type(getattr(self, nombre)) is not bool:
                raise ValueError(f"El valor de {nombre} debe ser booleano.")
        for nombre, longitud, minimo, maximo in (
            ("perfil_llegadas", self.horas_turno, 0, 5),
            ("medias_consulta_prioridad", 3, 0, 240),
        ):
            valores = getattr(self, nombre)
            if not isinstance(valores, (tuple, list)):
                raise ValueError(f"{nombre} debe ser una secuencia de valores.")
            if valores and len(valores) != longitud:
                raise ValueError(f"{nombre} debe tener {longitud} valores o estar vacío.")
            if any(not isinstance(v, Real) or not isfinite(v) or not minimo <= v <= maximo for v in valores):
                raise ValueError(f"Los valores de {nombre} deben estar entre {minimo} y {maximo}.")
            if nombre == "medias_consulta_prioridad" and any(v <= 0 for v in valores):
                raise ValueError("Las medias de consulta por prioridad deben ser positivas.")
            object.__setattr__(self, nombre, tuple(float(v) for v in valores))
        if self.usar_tablas_frecuencia and (
            self.perfil_llegadas or self.generar_hasta_cierre or self.medias_consulta_prioridad
        ):
            raise ValueError(
                "Las tablas de frecuencia requieren cupo fijo, sin perfil horario ni medias de consulta por prioridad."
            )

    @property
    def turno_min(self) -> int:
        return self.horas_turno * 60

    @property
    def horizonte_min(self) -> float:
        return self.turno_min + self.seguimiento_min

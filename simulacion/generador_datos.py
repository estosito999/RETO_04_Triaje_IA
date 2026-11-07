from dataclasses import dataclass
from math import ceil

import numpy as np

from modelos.modelo_matematico import prioridad_referencia
from modelos.variables import UMBRAL_ALTO_REFERENCIA, UMBRAL_MEDIO_REFERENCIA, Parametros

MAX_PACIENTES_GENERADOS = 100_000
MAX_TRANSICIONES_CONEXION = 100_000


@dataclass(frozen=True)
class PacienteSintetico:
    id_paciente: int
    llegada_min: float
    prioridad_referencia: int
    senal_a: float
    senal_b: float
    duracion_triaje_min: float
    duracion_consulta_min: float
    requiere_teleconsulta: bool
    sorteo_conexion: float
    demora_remota_min: float


@dataclass(frozen=True)
class TrayectoriaConexion:
    """Estados de una única conexión del centro, indexados por tiempo absoluto."""

    tiempos: np.ndarray
    estados: np.ndarray

    def conectada(self, minuto: float) -> bool:
        indice = max(0, int(np.searchsorted(self.tiempos, minuto, side="right")) - 1)
        return bool(self.estados[indice])


def generar_trayectoria_conexion(p: Parametros) -> TrayectoriaConexion:
    """CTMC estacionaria: tasas on->off=(1-p)/tau y off->on=p/tau.

    No consume los flujos de pacientes. Ambas políticas consultan la misma
    trayectoria global aunque soliciten sus teleconsultas a horas distintas.
    """
    disponibilidad = p.disponibilidad_conexion
    if disponibilidad in (0, 1):
        return TrayectoriaConexion(np.array([0.0]), np.array([bool(disponibilidad)]))
    azar = np.random.Generator(np.random.PCG64(np.random.SeedSequence(p.semilla, spawn_key=(5,))))
    conectado = bool(azar.random() < disponibilidad)
    tiempos, estados = [0.0], [conectado]
    for _ in range(MAX_TRANSICIONES_CONEXION):
        tasa = (1 - disponibilidad if conectado else disponibilidad) / p.persistencia_conexion_min
        siguiente = tiempos[-1] + float(azar.exponential(1 / tasa))
        if siguiente >= p.horizonte_min:
            return TrayectoriaConexion(np.asarray(tiempos), np.asarray(estados))
        conectado = not conectado
        tiempos.append(siguiente)
        estados.append(conectado)
    raise ValueError("La conexión supera el límite de 100000 transiciones; aumenta su persistencia.")


def _generar_llegadas(p: Parametros, azar: np.random.Generator) -> np.ndarray:
    # Esta rama conserva exactamente el protocolo y los sorteos originales.
    if not p.perfil_llegadas and not p.generar_hasta_cierre:
        return azar.exponential(60 / p.llegadas_por_hora, p.pacientes).cumsum()
    factores = np.asarray(p.perfil_llegadas or (1.0,) * p.horas_turno)
    intensidad_hora = p.llegadas_por_hora * factores
    acumulada = intensidad_hora.cumsum()
    total = float(acumulada[-1])
    if p.generar_hasta_cierre:
        segmentos, ultimo, cantidad = [], 0.0, 0
        while ultimo < total:
            candidatos = ultimo + azar.exponential(1.0, 1024).cumsum()
            dentro = candidatos[candidatos < total]
            segmentos.append(dentro)
            cantidad += len(dentro)
            if cantidad > MAX_PACIENTES_GENERADOS:
                raise ValueError("El turno supera el límite de seguridad de 100000 pacientes.")
            ultimo = float(candidatos[-1])
        riesgos = np.concatenate(segmentos) if segmentos else np.empty(0)
    else:
        riesgos = azar.exponential(1.0, p.pacientes).cumsum()
    tiempos = np.full(len(riesgos), np.inf)
    validos = riesgos < total
    horas = np.searchsorted(acumulada, riesgos[validos], side="right")
    anteriores = np.concatenate(([0.0], acumulada[:-1]))
    tiempos[validos] = 60 * horas + 60 * (riesgos[validos] - anteriores[horas]) / intensidad_hora[horas]
    return tiempos


def generar_intentos_conexion(p: Parametros, paciente: PacienteSintetico) -> np.ndarray:
    """Mismos sorteos por paciente en ambas políticas, sin consumir el azar de las llegadas.

    La conexión se comprueba al solicitar y después a intervalos regulares. Cada
    intento es Bernoulli independiente; no se modela una cobertura geográfica.
    La secuencia finita cubre también el seguimiento posterior al turno.
    """
    azar = np.random.Generator(np.random.PCG64(np.random.SeedSequence(p.semilla, spawn_key=(4, paciente.id_paciente))))
    adicionales = ceil(p.horizonte_min / p.intervalo_reintento_min)
    return np.concatenate(([paciente.sorteo_conexion], azar.random(adicionales)))


def generar_pacientes(p: Parametros) -> list[PacienteSintetico]:
    semillas = np.random.SeedSequence(p.semilla).spawn(4)
    llegadas, casos, recursos, remoto = (np.random.Generator(np.random.PCG64(s)) for s in semillas)
    tiempos_llegada = _generar_llegadas(p, llegadas)
    n = len(tiempos_llegada)

    fraccion = p.proporcion_prioritarios
    altas = p.fraccion_alta_prioritarios
    estratos = casos.choice(3, n, p=[altas * fraccion, (1 - altas) * fraccion, 1 - fraccion])
    inferiores = np.array([UMBRAL_ALTO_REFERENCIA, UMBRAL_MEDIO_REFERENCIA, 0.0])
    superiores = np.array([1.0, UMBRAL_ALTO_REFERENCIA, UMBRAL_MEDIO_REFERENCIA])
    indice = casos.uniform(inferiores[estratos], superiores[estratos])
    senales_a = np.clip(indice + casos.normal(0, 0.13, n), 0, 1)
    senales_b = np.clip(0.8 * indice + 0.1 + casos.normal(0, 0.15, n), 0, 1)

    triajes = recursos.gamma(p.forma_triaje, p.triaje_medio_min / p.forma_triaje, n)
    medias_consulta = np.asarray(p.medias_consulta_prioridad)[estratos] if p.medias_consulta_prioridad else p.duracion_consulta_min
    consultas = recursos.gamma(p.forma_consulta, medias_consulta / p.forma_consulta, n)
    solicita = remoto.random(n) < np.array([0.40, 0.27, 0.12])[estratos]
    conexion = remoto.random(n)
    demora = p.respuesta_remota_min * remoto.uniform(0.7, 1.3, n)

    return [
        PacienteSintetico(
            i + 1, float(tiempos_llegada[i]), prioridad_referencia(float(indice[i])),
            float(senales_a[i]), float(senales_b[i]), float(triajes[i]), float(consultas[i]),
            bool(solicita[i]), float(conexion[i]), float(demora[i]),
        )
        for i in range(n)
    ]

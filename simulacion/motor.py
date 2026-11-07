from collections.abc import Generator
from dataclasses import dataclass
from typing import Any, cast

import numpy as np
import pandas as pd
from simpy import Environment, PriorityResource, Resource
from simpy.events import Event
from simpy.resources.resource import PriorityRequest, SortedQueue

from modelos.modelo_matematico import prioridad_asistida
from modelos.variables import ALTA, PASO_VISUAL_MIN, Parametros
from simulacion.generador_datos import (
    PacienteSintetico, generar_intentos_conexion, generar_pacientes, generar_trayectoria_conexion,
)

ESTADOS_POR_EVENTO = {
    "llegada": "cola_enfermeria",
    "inicio_triaje": "en_triaje",
    "fin_triaje": "cola_medica",
    "inicio_consulta": "en_consulta",
    "fin_consulta": "atendido",
}
CAMBIOS_POR_EVENTO = {
    "llegada": {"llegados": 1, "cola_enfermeria": 1},
    "inicio_triaje": {"cola_enfermeria": -1, "enfermeros_ocupados": 1},
    "fin_triaje": {"enfermeros_ocupados": -1, "cola_medica": 1},
    "inicio_consulta": {"cola_medica": -1, "medicos_ocupados": 1},
    "fin_consulta": {"medicos_ocupados": -1, "atendidos": 1},
    "tele_solicitada": {"telependientes": 1, "telepor_enviar": 1},
    "tele_intento": {},
    "tele_enviada": {"telepor_enviar": -1, "teleesperando_respuesta": 1},
    "tele_respondida": {"telependientes": -1, "teleesperando_respuesta": -1, "telerespondidas": 1},
    "reevaluacion": {},
}
COLUMNAS_EVENTOS = ("minuto", "id_paciente", "evento", "prioridad_referencia", "prioridad_actual")
COLUMNAS_ESTADO = (
    "llegados", "cola_enfermeria", "enfermeros_ocupados", "cola_medica", "medicos_ocupados",
    "atendidos", "telependientes", "telepor_enviar", "teleesperando_respuesta", "telerespondidas",
)


@dataclass(frozen=True)
class Resultado:
    pacientes: pd.DataFrame
    eventos: pd.DataFrame
    cronologia: pd.DataFrame
    horizonte_min: float | None = None


@dataclass(frozen=True)
class Experimento:
    parametros: Parametros
    referencia: Resultado
    asistido: Resultado


def _registro(paciente: PacienteSintetico) -> dict[str, Any]:
    return {
        "id_paciente": paciente.id_paciente,
        "llegada_min": paciente.llegada_min,
        "prioridad_referencia": paciente.prioridad_referencia,
        "prioridad_asignada": np.nan,
        "prioridad_actual": np.nan,
        "reevaluaciones": 0,
        "senal_a": paciente.senal_a,
        "senal_b": paciente.senal_b,
        **{f"{evento}_min": np.nan for evento in CAMBIOS_POR_EVENTO if evento not in ("llegada", "tele_intento")},
        "intentos_envio": 0,
        "ultimo_intento_envio_min": np.nan,
        "inicio_atencion_remota_min": np.nan,
        "fin_servicio_local_min": np.nan,
        "estado": "no_llego",
    }


def _cronologia(eventos: pd.DataFrame, cierre: float) -> pd.DataFrame:
    muestras = np.append(np.arange(0, cierre, PASO_VISUAL_MIN), cierre)
    cambios = np.zeros((len(eventos) + 1, len(COLUMNAS_ESTADO)), dtype=int)
    indices = {nombre: i for i, nombre in enumerate(COLUMNAS_ESTADO)}
    for fila, evento in enumerate(eventos.evento, start=1):
        for campo, delta in CAMBIOS_POR_EVENTO[evento].items():
            cambios[fila, indices[campo]] = delta
    incluidos = np.searchsorted(eventos.minuto.to_numpy(dtype=float), muestras, side="right")
    estados = pd.DataFrame(cambios.cumsum(axis=0)[incluidos], columns=COLUMNAS_ESTADO)
    estados.insert(0, "minuto", muestras)
    return estados


def _simular_estrategia(p: Parametros, cohorte: list[PacienteSintetico], asistido: bool) -> Resultado:
    reloj = Environment()
    enfermeria = Resource(reloj, capacity=p.enfermeros)
    consultas = PriorityResource(reloj, capacity=p.medicos)
    especialistas = Resource(reloj, capacity=p.especialistas_remotos) if p.especialistas_remotos else None
    conexion = generar_trayectoria_conexion(p) if p.conexion_compartida else None
    registros = {paciente.id_paciente: _registro(paciente) for paciente in cohorte}
    eventos: list[tuple[float, int, str, int, float]] = []

    def registrar(paciente: PacienteSintetico, evento: str) -> None:
        fila = registros[paciente.id_paciente]
        if evento == "tele_intento":
            fila["intentos_envio"] += 1
            fila["ultimo_intento_envio_min"] = reloj.now
        else:
            fila[f"{evento}_min"] = reloj.now
        if evento in ESTADOS_POR_EVENTO:
            fila["estado"] = ESTADOS_POR_EVENTO[evento]
        eventos.append((reloj.now, paciente.id_paciente, evento, paciente.prioridad_referencia, fila["prioridad_actual"]))

    def teleconsulta(paciente: PacienteSintetico) -> Generator[Event, object, None]:
        registrar(paciente, "tele_solicitada")
        for sorteo in generar_intentos_conexion(p, paciente):
            registrar(paciente, "tele_intento")
            conectado = conexion.conectada(reloj.now) if conexion is not None else sorteo < p.disponibilidad_conexion
            if conectado:
                registrar(paciente, "tele_enviada")
                if especialistas is None:
                    registros[paciente.id_paciente]["inicio_atencion_remota_min"] = reloj.now
                    yield reloj.timeout(paciente.demora_remota_min)
                else:
                    with especialistas.request() as recurso:
                        yield recurso
                        registros[paciente.id_paciente]["inicio_atencion_remota_min"] = reloj.now
                        yield reloj.timeout(paciente.demora_remota_min)
                registrar(paciente, "tele_respondida")
                return
            yield reloj.timeout(p.intervalo_reintento_min)

    def reevaluar(paciente: PacienteSintetico, solicitud: PriorityRequest) -> Generator[Event, object, None]:
        """Promueve la solicitud pendiente conservando su antigüedad de entrada.

        PriorityResource no interrumpe consultas. Se actualiza la clave y se
        reordena únicamente su cola de solicitudes todavía no concedidas.
        """
        fila = registros[paciente.id_paciente]
        while not solicitud.triggered and fila["prioridad_actual"] > ALTA:
            yield reloj.timeout(p.deterioro_cada_min)
            if solicitud.triggered:
                return
            fila["prioridad_actual"] -= 1
            fila["reevaluaciones"] += 1
            solicitud.priority = fila["prioridad_actual"]
            solicitud.key = (solicitud.priority, *solicitud.key[1:])
            cast(SortedQueue, consultas.queue).sort(key=lambda pendiente: pendiente.key)
            registrar(paciente, "reevaluacion")

    def atender(paciente: PacienteSintetico) -> Generator[Event, object, None]:
        yield reloj.timeout(paciente.llegada_min)
        registrar(paciente, "llegada")
        with enfermeria.request() as recurso:
            yield recurso
            registrar(paciente, "inicio_triaje")
            yield reloj.timeout(paciente.duracion_triaje_min)
            registrar(paciente, "fin_triaje")

        orden = 0
        if asistido:
            orden = prioridad_asistida(paciente.senal_a, paciente.senal_b, p)
            registros[paciente.id_paciente]["prioridad_asignada"] = orden
            registros[paciente.id_paciente]["prioridad_actual"] = orden
        with consultas.request(priority=orden) as recurso:
            if asistido and p.deterioro_cada_min:
                reloj.process(reevaluar(paciente, cast(PriorityRequest, recurso)))
            yield recurso
            registrar(paciente, "inicio_consulta")
            respuesta = None
            if paciente.requiere_teleconsulta:
                respuesta = reloj.process(teleconsulta(paciente))
            yield reloj.timeout(paciente.duracion_consulta_min)
            registros[paciente.id_paciente]["fin_servicio_local_min"] = reloj.now
            if p.esperar_teleconsulta and respuesta is not None:
                yield respuesta
            registrar(paciente, "fin_consulta")

    for paciente in cohorte:
        if paciente.llegada_min < p.turno_min:
            reloj.process(atender(paciente))
    reloj.run(until=p.horizonte_min)
    bitacora = pd.DataFrame.from_records(eventos, columns=COLUMNAS_EVENTOS)
    columnas = _registro(PacienteSintetico(0, 0, 3, 0, 0, 0, 0, False, 0, 0)).keys()
    tabla = pd.DataFrame.from_records(list(registros.values()), columns=list(columnas))
    return Resultado(tabla, bitacora, _cronologia(bitacora, p.horizonte_min), p.horizonte_min)


def simular(p: Parametros) -> Experimento:
    cohorte = generar_pacientes(p)
    referencia = _simular_estrategia(p, cohorte, asistido=False)
    asistido = _simular_estrategia(p, cohorte, asistido=True)
    return Experimento(p, referencia, asistido)

"""Evidencia compacta y reproducible para presentar el experimento.

No lee archivos de resultados ni elige semillas según el resultado. Cada media
es una media entre turnos con observación, no una tasa agrupada de pacientes.
Las métricas principales se cortan al cierre incluso si existe seguimiento.
"""

from dataclasses import asdict

import numpy as np
import pandas as pd

from analisis.experimentos import ejecutar_replicas, metadatos_experimento, resumen_pareado, semillas_replicas
from modelos.variables import Parametros

# Selección estable, declarada antes de simular: beneficio, contrapartida, capacidad y errores.
METRICAS_PITCH = {
    "espera_medica_alta_min_al_cierre": (
        "Espera médica · alta", "min", "Pacientes de referencia alta que iniciaron consulta antes del cierre.", "menor"),
    "espera_medica_baja_min_al_cierre": (
        "Espera médica · baja", "min", "Pacientes de referencia baja que iniciaron consulta antes del cierre.", "menor"),
    "espera_acumulada_hasta_consulta_alta_min_al_cierre": (
        "Tiempo acumulado hasta consulta · alta", "min", "Todos los llegados de referencia alta, incluidos los que siguen esperando al cierre.", "menor"),
    "espera_acumulada_hasta_consulta_baja_min_al_cierre": (
        "Tiempo acumulado hasta consulta · baja", "min", "Todos los llegados de referencia baja, incluidos los que siguen esperando al cierre.", "menor"),
    "pacientes_atendidos_al_cierre": (
        "Consultas completadas", "pacientes/turno", "Todos los pacientes llegados antes del cierre.", "mayor"),
    "pacientes_sin_iniciar_consulta_al_cierre": (
        "Pendientes de iniciar consulta", "pacientes/turno", "Llegados sin inicio de consulta al cierre.", "menor"),
    "pendientes_sin_consulta_alta_al_cierre": (
        "Pendientes de iniciar · alta", "pacientes/turno", "Llegados de referencia alta sin inicio de consulta al cierre.", "menor"),
    "pendientes_sin_consulta_baja_al_cierre": (
        "Pendientes de iniciar · baja", "pacientes/turno", "Llegados de referencia baja sin inicio de consulta al cierre.", "menor"),
    "pacientes_llegados_al_cierre": (
        "Pacientes llegados", "pacientes/turno", "Misma cohorte de llegadas en ambas políticas.", "descriptivo"),
    "sensibilidad_alta_pct_al_cierre": (
        "Sensibilidad de prioridad alta", "% por turno", "Casos altos clasificados antes del cierre; FIFO no clasifica.", "mayor"),
    "tasa_subtriaje_pct_al_cierre": (
        "Subtriaje", "% por turno", "Todos los clasificados antes del cierre; FIFO no clasifica.", "menor"),
    "perdida_clasificacion_media_al_cierre": (
        "Pérdida relativa por clasificación", "costo educativo/caso", "Clasificados antes del cierre; matriz de costos ilustrativa, sin significado clínico.", "menor"),
    "teleconsultas_pendientes_al_cierre": (
        "Teleconsultas pendientes", "solicitudes/turno", "Solicitudes sin respuesta al cierre; volumen condicionado a haber iniciado consulta.", "menor"),
    "carga_medicos_pct_al_cierre": (
        "Ocupación médica", "% por turno", "Minutos ocupados / capacidad disponible durante el turno.", "descriptivo"),
}


def generar_evidencia(p: Parametros, repeticiones: int = 30) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve mediciones compactas y diferencias pareadas con IC puntual del 95 %.

    Usa semillas consecutivas desde ``p.semilla`` mediante SeedSequence del
    generador; conserva los mismos pacientes y sorteos dentro de cada par.
    El llamador puede aplicar cache; esta función no escribe archivos ni lee CSV.
    """
    semillas = semillas_replicas(repeticiones, p.semilla)
    todas = ejecutar_replicas(p, semillas)
    mediciones = todas.loc[todas.metrica.isin(METRICAS_PITCH)].copy().reset_index(drop=True)
    diferencias = resumen_pareado(mediciones)
    metadata = metadatos_experimento(semillas) | {
        "parametros": asdict(p), "repeticiones_planificadas": repeticiones,
        "seleccion_semillas": "Consecutivas desde la semilla configurada; ninguna búsqueda por resultado.",
        "seleccion_metricas": list(METRICAS_PITCH),
        "horizonte_principal_min": p.turno_min,
        "agregacion": "Media entre turnos observados; porcentajes medios por turno, no tasas agrupadas.",
        "censura": "Las esperas iniciadas omiten a quienes no comenzaron. Las acumuladas incluyen el tiempo observado hasta cierre, no su espera futura.",
    }
    mediciones.attrs["metadatos"] = metadata
    diferencias.attrs["metadatos"] = metadata
    return mediciones, diferencias


def resumir_evidencia(mediciones: pd.DataFrame, diferencias: pd.DataFrame | None = None) -> pd.DataFrame:
    """Tabla de presentación de un solo escenario/condición, con muestras visibles.

    Las dos medias descriptivas usan sus observaciones disponibles. La diferencia
    e IC usan SOLO pares completos y pueden tener otro denominador, que se muestra.
    No calcula reducciones porcentuales ni convierte faltantes en ceros.
    """
    requeridas = {"escenario", "condicion", "metrica", "estrategia", "semilla", "valor"}
    if not requeridas.issubset(mediciones.columns):
        raise ValueError("Las mediciones no tienen el esquema de ejecutar_replicas.")
    if mediciones.empty:
        raise ValueError("No hay mediciones para resumir.")
    if len(mediciones[["escenario", "condicion"]].drop_duplicates()) != 1:
        raise ValueError("Selecciona un solo escenario y una sola condición para presentar la evidencia.")
    # Revalida duplicados y políticas aunque se proporcione un resumen precalculado.
    calculadas = resumen_pareado(mediciones)
    if diferencias is not None:
        claves = ["escenario", "condicion", "metrica"]
        if diferencias.duplicated(claves).any():
            raise ValueError("Las diferencias contienen métricas duplicadas.")
        verificar = [*claves, "pares_validos", "pares_faltantes", "diferencia_media", "ic95_inferior", "ic95_superior"]
        recibidas = diferencias.loc[diferencias.metrica.isin(mediciones.metrica), verificar]
        esperadas = calculadas.loc[:, verificar]
        try:
            pd.testing.assert_frame_equal(recibidas.sort_values(claves).reset_index(drop=True),
                                          esperadas.sort_values(claves).reset_index(drop=True), check_dtype=False)
        except AssertionError as error:
            raise ValueError("Las diferencias no corresponden a las mediciones proporcionadas.") from error
    filas = []
    for metrica, (etiqueta, unidad, denominador, preferencia) in METRICAS_PITCH.items():
        casos = mediciones.loc[mediciones.metrica == metrica]
        if casos.empty:
            continue
        fila_d = calculadas.loc[calculadas.metrica == metrica].iloc[0]
        valores = {}
        for estrategia, prefijo in (("FIFO", "fifo"), ("Triaje asistido", "asistido")):
            muestra = pd.to_numeric(casos.loc[casos.estrategia == estrategia, "valor"], errors="raise")
            muestra = muestra.replace([np.inf, -np.inf], np.nan).dropna()
            valores[f"{prefijo}_media"] = float(muestra.mean()) if len(muestra) else None
            valores[f"{prefijo}_repeticiones_observadas"] = len(muestra)
        inferior, superior = fila_d.ic95_inferior, fila_d.ic95_superior
        if pd.isna(inferior) or pd.isna(superior):
            lectura = "Sin IC: menos de dos pares observados."
        elif inferior > 0:
            lectura = "Diferencia positiva: el IC puntual queda por encima de cero."
        elif superior < 0:
            lectura = "Diferencia negativa: el IC puntual queda por debajo de cero."
        else:
            lectura = "El IC puntual incluye cero; no se distingue un signo con este intervalo."
        filas.append({"metrica": metrica, "etiqueta": etiqueta, "unidad": unidad,
            "denominador": denominador, "preferencia": preferencia, **valores,
            "repeticiones": int(fila_d.repeticiones), "pares_validos": int(fila_d.pares_validos),
            "pares_faltantes": int(fila_d.pares_faltantes), "diferencia_media": fila_d.diferencia_media,
            "ic95_inferior": inferior, "ic95_superior": superior, "lectura_IC": lectura})
    tabla = pd.DataFrame(filas)
    tabla.attrs.update(mediciones.attrs)
    return tabla

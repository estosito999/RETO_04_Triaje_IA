"""Distribuciones discretas educativas mediante tablas de frecuencia."""

from collections.abc import Sequence

import numpy as np

TablaFrecuencias = tuple[tuple[float, float], ...]

TABLA_INTERARRIBOS: TablaFrecuencias = ((1, 10), (2, 15), (3, 15), (4, 7), (5, 3))
TABLA_SERVICIOS: TablaFrecuencias = ((15, 5), (20, 10), (25, 20), (30, 10), (35, 5))


def _componentes(tabla: TablaFrecuencias) -> tuple[np.ndarray, np.ndarray]:
    datos = np.asarray(tabla, dtype=float)
    if datos.ndim != 2 or datos.shape[1] != 2 or len(datos) == 0:
        raise ValueError("La tabla debe contener pares de valor y frecuencia.")
    if not np.isfinite(datos).all() or np.any(datos[:, 1] <= 0):
        raise ValueError("Los valores deben ser finitos y las frecuencias positivas.")
    return datos[:, 0], datos[:, 1]


def media_frecuencias(tabla: TablaFrecuencias) -> float:
    """Media ponderada por las frecuencias, sin generar una muestra."""
    valores, frecuencias = _componentes(tabla)
    return float(np.dot(valores, frecuencias) / frecuencias.sum())


def generar_desde_frecuencias(
    tabla: TablaFrecuencias, uniformes: np.ndarray | Sequence[float],
) -> np.ndarray:
    """Transformada inversa: cada frontera acumulada pertenece al valor anterior.

    Se admiten uniformes entre cero y uno inclusive; el generador del modelo
    produce valores en [0, 1). Las tablas son supuestos educativos fijos.
    """
    valores, frecuencias = _componentes(tabla)
    sorteos = np.asarray(uniformes, dtype=float)
    if not np.isfinite(sorteos).all() or np.any((sorteos < 0) | (sorteos > 1)):
        raise ValueError("Los uniformes deben estar entre cero y uno.")
    acumuladas = np.cumsum(frecuencias) / frecuencias.sum()
    return valores[np.searchsorted(acumuladas, sorteos, side="left")]

from modelos.variables import (
    ALTA, BAJA, MEDIA, PESO_SENAL_A, UMBRAL_ALTO_ASISTIDO, UMBRAL_ALTO_REFERENCIA,
    UMBRAL_MEDIO_ASISTIDO, UMBRAL_MEDIO_REFERENCIA,
    Parametros,
)


def _clasificar(indice: float, umbral_alto: float, umbral_medio: float) -> int:
    if indice >= umbral_alto:
        return ALTA
    if indice >= umbral_medio:
        return MEDIA
    return BAJA


def prioridad_referencia(indice_latente: float) -> int:
    """Regla de etiquetado del generador sintético, sobre un índice inaccesible al clasificador."""
    return _clasificar(indice_latente, UMBRAL_ALTO_REFERENCIA, UMBRAL_MEDIO_REFERENCIA)


def prioridad_asistida(
    senal_a: float, senal_b: float, p: Parametros | None = None, *,
    peso_senal_a: float | None = None, umbral_alto: float | None = None,
    umbral_medio: float | None = None,
) -> int:
    """Clasificador experimental que opera solo sobre dos señales simuladas sin unidades."""
    peso = peso_senal_a if peso_senal_a is not None else (p.peso_senal_a if p else PESO_SENAL_A)
    alto = umbral_alto if umbral_alto is not None else (p.umbral_alto if p else UMBRAL_ALTO_ASISTIDO)
    medio = umbral_medio if umbral_medio is not None else (p.umbral_medio if p else UMBRAL_MEDIO_ASISTIDO)
    puntaje = peso * senal_a + (1 - peso) * senal_b
    return _clasificar(puntaje, alto, medio)

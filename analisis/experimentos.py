"""Repeticiones independientes con comparaciones emparejadas e IC del 95 %."""

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import platform
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import scipy
from scipy.stats import t

from analisis.metricas import COSTOS_CLASIFICACION, comparar, espera_por_prioridad
from modelos.variables import PRIORIDADES, Parametros
from simulacion.escenarios import ESCENARIOS
from simulacion.motor import simular

RAIZ = Path(__file__).resolve().parents[1]


def _validar_semillas(semillas: list[int]) -> None:
    if not semillas or len(set(semillas)) != len(semillas):
        raise ValueError("Indica al menos una semilla, sin repetir valores.")
    for semilla in semillas:
        Parametros(semilla=semilla)


def semillas_replicas(repeticiones: int, semilla_base: int = 42) -> list[int]:
    if type(repeticiones) is not int or not 1 <= repeticiones <= 10000:
        raise ValueError("Las repeticiones deben ser un entero entre 1 y 10000.")
    Parametros(semilla=semilla_base)
    # SeedSequence mezcla cada semilla dentro del generador; no se reinicia un mismo turno.
    return [(semilla_base + i) % (2**32) for i in range(repeticiones)]


def _mediciones(p: Parametros, escenario: str, condicion: str) -> list[dict]:
    exp = simular(p)
    comparacion = comparar(exp)
    for al_cierre in (False, True):
        sufijo = "_al_cierre" if al_cierre else ""
        for fila in espera_por_prioridad(exp, al_cierre=al_cierre).itertuples():
            prioridad = PRIORIDADES[fila.prioridad_referencia].lower()
            campos = {
                f"espera_medica_{prioridad}_min": fila.espera_medica_min,
                f"tiempo_hasta_atencion_{prioridad}_min": fila.tiempo_hasta_atencion_min,
                f"consultas_iniciadas_{prioridad}": fila.pacientes,
                f"pendientes_sin_consulta_{prioridad}": fila.pendientes_sin_consulta,
                f"sin_completar_{prioridad}": fila.sin_completar,
                f"espera_acumulada_hasta_consulta_{prioridad}_min": fila.espera_acumulada_hasta_consulta_min,
                f"espera_medica_p95_{prioridad}_min": fila.espera_medica_p95_min,
            }
            for campo, valor in campos.items():
                comparacion.loc[fila.estrategia, campo+sufijo] = valor
    parametros_json = json.dumps(asdict(p), ensure_ascii=False, sort_keys=True)
    return [{"escenario": escenario, "semilla": p.semilla, "condicion": condicion,
             "estrategia": estrategia, "metrica": metrica, "valor": valor, "parametros_json": parametros_json}
            for estrategia, metricas in comparacion.iterrows() for metrica, valor in metricas.items()]


def ejecutar_replicas(p: Parametros, semillas: list[int]) -> pd.DataFrame:
    """Compara ambas políticas de la configuración actual sobre la misma cohorte por semilla."""
    _validar_semillas(semillas)
    registros = []
    for semilla in semillas:
        registros.extend(_mediciones(replace(p, semilla=semilla), "Configuración actual", "Configurada"))
    return pd.DataFrame(registros)


def ejecutar_experimentos(semillas: list[int]) -> pd.DataFrame:
    _validar_semillas(semillas)
    registros = []
    for escenario, parametros in ESCENARIOS.items():
        for semilla in semillas:
            base = replace(parametros, semilla=semilla)
            for condicion, configuracion in (
                ("Conexión del escenario", base),
                ("Conexión disponible", replace(base, disponibilidad_conexion=1.0)),
            ):
                registros.extend(_mediciones(configuracion, escenario, condicion))
    return pd.DataFrame(registros)


def resumen_pareado(datos: pd.DataFrame) -> pd.DataFrame:
    """IC t de la media de diferencias independientes entre semillas.

    Conserva pares con ambos valores finitos; informa cuántos se pierden.
    Una fila ausente o sin observación no se convierte en cero. Los IC son
    puntuales por métrica, sin corrección por comparaciones múltiples.
    """
    columnas = ["escenario", "condicion", "metrica", "repeticiones", "pares_validos", "pares_faltantes",
                "diferencia_media", "desviacion_diferencias", "error_estandar", "ic95_inferior", "ic95_superior"]
    requeridas = {"escenario", "condicion", "semilla", "estrategia", "metrica", "valor"}
    if not requeridas.issubset(datos.columns):
        raise ValueError(f"Faltan columnas: {', '.join(sorted(requeridas-set(datos.columns)))}.")
    if datos.empty:
        return pd.DataFrame(columns=columnas)
    claves = ["escenario", "condicion", "metrica"]
    if datos.duplicated(claves+["semilla", "estrategia"]).any():
        raise ValueError("Hay mediciones duplicadas para una misma semilla, política y métrica.")
    if not datos.estrategia.isin(["FIFO", "Triaje asistido"]).all():
        raise ValueError("El resumen solo admite las políticas FIFO y Triaje asistido.")
    filas = []
    for clave, grupo in datos.groupby(claves, sort=False, dropna=False):
        semillas = datos.loc[(datos.escenario == clave[0]) & (datos.condicion == clave[1]), "semilla"].unique()
        pares = grupo.pivot(index="semilla", columns="estrategia", values="valor").reindex(
            index=semillas, columns=["FIFO", "Triaje asistido"])
        pares = pares.apply(pd.to_numeric, errors="raise").replace([np.inf, -np.inf], np.nan)
        diferencias = (pares["Triaje asistido"]-pares.FIFO).dropna()
        n = len(diferencias)
        media = float(diferencias.mean()) if n else None
        sd = float(diferencias.std(ddof=1)) if n >= 2 else None
        ee = sd/np.sqrt(n) if sd is not None else None
        margen = float(t.ppf(.975, n-1)*ee) if ee is not None else None
        filas.append(dict(zip(claves, clave)) | {
            "repeticiones": len(pares), "pares_validos": n, "pares_faltantes": len(pares)-n,
            "diferencia_media": media, "desviacion_diferencias": sd, "error_estandar": ee,
            "ic95_inferior": media-margen if margen is not None else None,
            "ic95_superior": media+margen if margen is not None else None})
    return pd.DataFrame(filas, columns=columnas)


def metadatos_experimento(semillas: list[int]) -> dict:
    return {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
        "generador": "PCG64", "semillas": semillas, "diferencia": "Triaje asistido - FIFO",
        "intervalo": "Student bilateral 95 %, puntual por métrica; pares completos entre semillas independientes",
        "costos_clasificacion": COSTOS_CLASIFICACION.tolist(),
        "alcance": "Experimento sintético sin validación clínica. No se imputan observaciones ausentes."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument("--semillas", nargs="+", type=int)
    grupo.add_argument("--repeticiones", type=int, help="Número de turnos independientes; por defecto 30.")
    parser.add_argument("--semilla-base", type=int, default=42)
    parser.add_argument("--validar-azar", action="store_true")
    parser.add_argument("--salida", type=Path, default=RAIZ/"resultados")
    args = parser.parse_args()
    try:
        semillas = args.semillas if args.semillas is not None else semillas_replicas(
            args.repeticiones if args.repeticiones is not None else 30, args.semilla_base)
        resultados = ejecutar_experimentos(semillas)
        resumen = resumen_pareado(resultados)
    except ValueError as error:
        parser.error(str(error))
    args.salida.mkdir(exist_ok=True, parents=True)
    with TemporaryDirectory(prefix="experimento_", dir=args.salida) as temporal:
        for nombre, tabla in (("experimentos", resultados), ("resumen_pareado", resumen)):
            archivo = Path(temporal)/f"{nombre}.csv"
            tabla.to_csv(archivo, index=False, encoding="utf-8-sig")
            archivo.replace(args.salida/archivo.name)
    metadata = metadatos_experimento(semillas)
    (args.salida/"metadatos_experimentos.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.validar_azar:
        from analisis.validacion import diagnosticar_azar
        diagnosticar_azar(args.semilla_base).to_csv(args.salida/"diagnostico_azar.csv", index=False, encoding="utf-8-sig")
    print(f"Guardadas {len(resultados)} mediciones y {len(resumen)} comparaciones en {args.salida}")
    print("Cada diferencia es Triaje asistido - FIFO. Los IC vacíos no tienen al menos dos pares válidos.")


if __name__ == "__main__":
    main()

"""Diagnósticos reproducibles del azar base y de las transformaciones del simulador.

No son certificación del generador ni validación de un centro real. Los valores
p son diagnósticos individuales; alguno puede ser pequeño por azar al realizar
varias comparaciones. No se usan como aprobación automática de la aplicación.
"""

import math

import numpy as np
import pandas as pd
from scipy import stats

from modelos.variables import Parametros
from simulacion.generador_datos import generar_pacientes


def diagnosticar_azar(semilla: int = 42, n: int = 10000) -> pd.DataFrame:
    """Comprueba U(0,1), dependencia serial y Gamma/exponencial con parámetros conocidos.

    Las muestras de tiempos se obtienen del generador real del proyecto,
    incluyendo pacientes cuyo arribo está después del turno; no están censuradas.
    """
    Parametros(semilla=semilla)
    if type(n) is not int or not 100 <= n <= 1000000:
        raise ValueError("El tamaño del diagnóstico debe ser un entero entre 100 y 1000000.")
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(semilla, spawn_key=(91,))))
    uniformes = rng.random(n)
    filas = []

    def agregar(prueba, distribucion, estadistico, p_valor, referencia, interpretacion):
        filas.append({"prueba": prueba, "distribucion": distribucion, "n": n,
            "estadistico": float(estadistico), "p_valor": float(p_valor) if p_valor is not None else None,
            "referencia": referencia, "interpretacion": interpretacion})

    ks = stats.kstest(uniformes, "uniform")
    agregar("Uniformidad KS", "Uniforme(0,1)", ks.statistic, ks.pvalue,
            "CDF completamente especificada U(0,1)", "Un p pequeño señala discrepancia; no demuestra un defecto por sí solo.")
    agregar("Media uniforme", "Uniforme(0,1)", uniformes.mean(), None,
            f"Media 0.5; error estándar teórico {math.sqrt(1/(12*n)):.6g}", "Comparar desviación con error de muestreo.")
    agregar("Varianza uniforme", "Uniforme(0,1)", uniformes.var(ddof=1), None,
            "Varianza 1/12 = 0.0833333", "La varianza muestral no debe coincidir exactamente con la teórica.")
    centrados = uniformes-uniformes.mean()
    r1 = float(np.dot(centrados[:-1], centrados[1:])/np.dot(centrados, centrados))
    agregar("Autocorrelación lag 1", "Uniforme(0,1)", r1,
            2*stats.norm.sf(abs(r1)*math.sqrt(n)), "Correlación 0; p aproximado asintótico",
            "Detecta dependencia lineal de primer orden; no prueba independencia total.")
    positivos = uniformes >= .5
    n1, n0 = int(positivos.sum()), int((~positivos).sum())
    rachas = 1+int(np.count_nonzero(positivos[1:] != positivos[:-1]))
    media_rachas = 1+2*n1*n0/n
    var_rachas = 2*n1*n0*(2*n1*n0-n)/(n*n*(n-1))
    z = (rachas-media_rachas)/math.sqrt(var_rachas) if var_rachas > 0 else math.inf
    agregar("Rachas sobre 0.5", "Uniforme(0,1)", z, 2*stats.norm.sf(abs(z)),
            "Z aproximado N(0,1)", "Busca agrupamientos excesivos o alternancia; diagnóstico aproximado.")

    intervalos, triajes, consultas = [], [], []
    restantes, lote = n, 0
    while restantes:
        cantidad = min(500, restantes)
        muestra = generar_pacientes(Parametros(semilla=(semilla+lote) % 2**32, pacientes=cantidad))
        tiempos = np.array([paciente.llegada_min for paciente in muestra])
        intervalos.extend(np.diff(np.concatenate(([0.], tiempos))))
        triajes.extend(paciente.duracion_triaje_min for paciente in muestra)
        consultas.extend(paciente.duracion_consulta_min for paciente in muestra)
        restantes -= cantidad
        lote += 1
    for nombre, valores, distribucion, args, referencia in (
        ("Intervalos de llegada KS", intervalos, "expon", (0, 5.), "Exponencial media 5 min (12 pacientes/h)"),
        ("Duración de triaje KS", triajes, "gamma", (6., 0, 4/6), "Gamma forma 6, media 4 min"),
        ("Duración de consulta KS", consultas, "gamma", (8., 0, 16/8), "Gamma forma 8, media 16 min"),
    ):
        prueba = stats.kstest(valores, distribucion, args=args)
        agregar(nombre, distribucion, prueba.statistic, prueba.pvalue, referencia,
                "Parámetros fijados de antemano; prueba de la transformación, no del realismo clínico.")
    tabla = pd.DataFrame(filas)
    tabla.attrs["metadatos"] = {"semilla": semilla, "n": n, "generador": type(rng.bit_generator).__name__,
        "numpy": np.__version__, "comparaciones_multiples": "Valores p individuales, sin corrección.",
        "alcance": "Diagnósticos; no prueban aleatoriedad absoluta ni validación clínica."}
    return tabla

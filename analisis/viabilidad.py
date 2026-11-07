"""Presupuesto paramétrico de un piloto retrospectivo del laboratorio.

Todos los importes predeterminados son supuestos ilustrativos en bolivianos,
no cotizaciones verificadas. El modelo calcula costos bajo esos supuestos;
no estima ingresos, rentabilidad, retorno, ahorro ni impacto clínico.
"""

from dataclasses import asdict, dataclass, fields, replace
from math import isfinite
from numbers import Real

import pandas as pd


NOTAS_PRESUPUESTO = (
    "Supuestos ilustrativos para un piloto retrospectivo; no son precios ni cotizaciones verificadas.",
    "La operación mensual representa soporte del laboratorio, no la operación de un servicio sanitario.",
    "No incluye atención médica real ni conectividad de una operación clínica real.",
    "Las integraciones clínicas, los trámites y los requisitos regulatorios no están estimados.",
    "Reutilizar equipo supone que los centros ya disponen de equipo adecuado y disponible.",
    "El desarrollo central se paga una sola vez; el despliegue variable se repite por centro.",
    "La contingencia se aplica solo a la inversión base inicial; no al gasto operativo mensual.",
    "Los costos por centro son un prorrateo aritmético, no evidencia de rentabilidad ni economías verificadas.",
)


@dataclass(frozen=True)
class PresupuestoPiloto:
    centros: int = 1
    meses: int = 12
    horas_desarrollo: float = 80.0
    tarifa_tecnica_bs: float = 80.0
    equipo_por_centro_bs: float = 3500.0
    reutilizar_equipo: bool = True
    horas_datos_por_centro: float = 12.0
    horas_revision_por_centro: float = 16.0
    tarifa_revision_bs: float = 100.0
    horas_capacitacion_por_centro: float = 4.0
    operacion_fija_mensual_bs: float = 200.0
    operacion_por_centro_mensual_bs: float = 100.0
    contingencia_pct: float = 15.0

    def __post_init__(self) -> None:
        for nombre in ("centros", "meses"):
            valor = getattr(self, nombre)
            if type(valor) is not int or valor < 1:
                raise ValueError(f"{nombre} debe ser un entero positivo.")
        if type(self.reutilizar_equipo) is not bool:
            raise ValueError("reutilizar_equipo debe ser booleano.")
        for campo in fields(self):
            if campo.name in ("centros", "meses", "reutilizar_equipo"):
                continue
            valor = getattr(self, campo.name)
            if isinstance(valor, bool) or not isinstance(valor, Real) or not isfinite(valor) or valor < 0:
                raise ValueError(f"{campo.name} debe ser un número finito mayor o igual a cero.")


def evaluar_presupuesto(p: PresupuestoPiloto) -> dict:
    """Costos sin redondeo intermedio ni ajustes automáticos a los supuestos.

    ``total_horizonte_bs`` = inversión inicial + meses × operación mensual.
    La inversión inicial incluye contingencia solo sobre su base inicial.
    El prorrateo distribuye el costo central y el fijo entre todos los centros.
    """
    central = p.horas_desarrollo * p.tarifa_tecnica_bs
    equipo = 0.0 if p.reutilizar_equipo else p.equipo_por_centro_bs
    datos = p.horas_datos_por_centro * p.tarifa_tecnica_bs
    revision = p.horas_revision_por_centro * p.tarifa_revision_bs
    capacitacion = p.horas_capacitacion_por_centro * p.tarifa_tecnica_bs
    por_centro = equipo + datos + revision + capacitacion
    despliegue = p.centros * por_centro
    base = central + despliegue
    contingencia = base * p.contingencia_pct / 100
    inversion = base + contingencia
    operacion_variable = p.centros * p.operacion_por_centro_mensual_bs
    operacion_mes = p.operacion_fija_mensual_bs + operacion_variable
    operacion_horizonte = p.meses * operacion_mes
    total = inversion + operacion_horizonte
    importes = {
        "desarrollo_central_bs": central,
        "equipo_por_centro_bs": equipo,
        "datos_por_centro_bs": datos,
        "revision_por_centro_bs": revision,
        "capacitacion_por_centro_bs": capacitacion,
        "despliegue_por_centro_bs": por_centro,
        "despliegue_total_bs": despliegue,
        "inversion_base_bs": base,
        "contingencia_bs": contingencia,
        "inversion_inicial_bs": inversion,
        "inversion_inicial_por_centro_bs": inversion / p.centros,
        "operacion_fija_mensual_bs": p.operacion_fija_mensual_bs,
        "operacion_variable_mensual_bs": operacion_variable,
        "operacion_mensual_bs": operacion_mes,
        "operacion_total_horizonte_bs": operacion_horizonte,
        "total_horizonte_bs": total,
        "costo_por_centro_bs": total / p.centros,
    }
    if not all(isfinite(valor) for valor in importes.values()):
        raise ValueError("Los supuestos producen importes fuera del rango numérico; reduce su magnitud.")
    return {
        "centros": p.centros, "meses": p.meses, "moneda": "BOB", **importes,
        "supuestos": asdict(p), "notas": list(NOTAS_PRESUPUESTO),
        "alcance": "Piloto retrospectivo del laboratorio con importes ilustrativos, sin evaluación de rentabilidad.",
    }


def desglose_presupuesto(p: PresupuestoPiloto) -> pd.DataFrame:
    """Partidas aditivas: la suma de importe_bs coincide con el total del horizonte.

    No incluye filas de subtotales que pudieran contarse dos veces en una gráfica.
    """
    r = evaluar_presupuesto(p)
    filas = [
        ("Desarrollo central", "Inversión inicial", f"{p.horas_desarrollo:g} h × Bs {p.tarifa_tecnica_bs:g}/h", r["desarrollo_central_bs"]),
        ("Equipo", "Inversión inicial", "Equipo existente reutilizado" if p.reutilizar_equipo
            else f"{p.centros} centros × Bs {p.equipo_por_centro_bs:g}", p.centros * r["equipo_por_centro_bs"]),
        ("Preparación de datos", "Inversión inicial", f"{p.centros} centros × {p.horas_datos_por_centro:g} h × Bs {p.tarifa_tecnica_bs:g}/h", p.centros * r["datos_por_centro_bs"]),
        ("Revisión profesional", "Inversión inicial", f"{p.centros} centros × {p.horas_revision_por_centro:g} h × Bs {p.tarifa_revision_bs:g}/h", p.centros * r["revision_por_centro_bs"]),
        ("Capacitación", "Inversión inicial", f"{p.centros} centros × {p.horas_capacitacion_por_centro:g} h × Bs {p.tarifa_tecnica_bs:g}/h", p.centros * r["capacitacion_por_centro_bs"]),
        ("Contingencia inicial", "Inversión inicial", f"{p.contingencia_pct:g} % de la inversión base", r["contingencia_bs"]),
        ("Soporte fijo del laboratorio", "Operación del laboratorio", f"{p.meses} meses × Bs {p.operacion_fija_mensual_bs:g}/mes", p.meses * p.operacion_fija_mensual_bs),
        ("Soporte variable por centro", "Operación del laboratorio", f"{p.meses} meses × {p.centros} centros × Bs {p.operacion_por_centro_mensual_bs:g}/mes", p.meses * r["operacion_variable_mensual_bs"]),
    ]
    tabla = pd.DataFrame(filas, columns=["concepto", "categoria", "base_calculo", "importe_bs"])
    tabla.attrs["metadatos"] = {"supuestos": asdict(p), "notas": list(NOTAS_PRESUPUESTO),
                                "moneda": "BOB", "total_horizonte_bs": r["total_horizonte_bs"]}
    return tabla


def escenarios_escala(p: PresupuestoPiloto, centros: tuple[int, ...] = (1, 3, 5, 10)) -> pd.DataFrame:
    """Mantiene supuestos y horizonte, variando únicamente el número de centros.

    La disminución del prorrateo central es consecuencia de esta fórmula; no es
    una predicción de costos reales ni acredita que diez centros sean factibles.
    """
    if not centros:
        raise ValueError("Indica al menos una cantidad de centros para comparar.")
    columnas = ["centros", "meses", "inversion_inicial_bs", "operacion_mensual_bs", "total_horizonte_bs", "costo_por_centro_bs"]
    filas = []
    for cantidad in centros:
        r = evaluar_presupuesto(replace(p, centros=cantidad))
        filas.append({nombre: r[nombre] for nombre in columnas})
    tabla = pd.DataFrame(filas, columns=columnas)
    tabla.attrs["metadatos"] = {"supuestos_base": asdict(p), "notas": list(NOTAS_PRESUPUESTO),
        "moneda": "BOB", "variable": "Solo cambia centros; se mantienen meses y costos unitarios."}
    return tabla

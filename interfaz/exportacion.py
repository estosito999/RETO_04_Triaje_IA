"""Exporta la configuración y las tablas del experimento local."""

from dataclasses import asdict
from datetime import datetime
from io import BytesIO
import json
from importlib.metadata import version
from pathlib import Path
import platform
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import streamlit as st


def exportar(parametros, tablas: dict[str, pd.DataFrame], prefijo: str) -> None:
    memoria = BytesIO()
    with ZipFile(memoria, "w", compression=ZIP_DEFLATED) as archivo:
        archivo.writestr("parametros.json", json.dumps(asdict(parametros), ensure_ascii=False, indent=2))
        metadatos = {
            "generador": "PCG64", "python": platform.python_version(),
            "versiones": {nombre: version(nombre) for nombre in ("numpy", "scipy", "pandas", "simpy", "streamlit")},
            "cierre_llegadas_min": parametros.turno_min, "horizonte_observacion_min": parametros.horizonte_min,
            "comparacion": "Misma cohorte y sorteos por repetición; diferencia asistido menos FIFO.",
            "alcance": "Modelo educativo; ajustes y costos sin validación clínica.",
            "tablas": {nombre: tabla.attrs["metadatos"] for nombre, tabla in tablas.items() if "metadatos" in tabla.attrs},
        }
        archivo.writestr("metadatos.json", json.dumps(metadatos, ensure_ascii=False, indent=2))
        for nombre, tabla in tablas.items():
            archivo.writestr(f"{nombre}.csv", tabla.to_csv(index=False).encode("utf-8-sig"))
    contenido = memoria.getvalue()
    nombre = f"{prefijo}_semilla_{parametros.semilla}"
    descarga, guardado = st.columns(2)
    descarga.download_button("Descargar resultados (ZIP)", contenido, f"{nombre}.zip", "application/zip",
                             on_click="ignore", width="stretch")
    if guardado.button("Guardar en resultados", width="stretch"):
        try:
            carpeta = Path(__file__).resolve().parents[1] / "resultados"
            carpeta.mkdir(exist_ok=True)
            destino = carpeta / f"{nombre}_{datetime.now():%Y%m%d_%H%M%S_%f}.zip"
            with destino.open("xb") as archivo:
                archivo.write(contenido)
            st.success(f"Guardado como resultados/{destino.name}")
        except OSError as error:
            st.error(f"No se pudo guardar el archivo. {error}")

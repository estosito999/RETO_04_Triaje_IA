"""Reproducción no bloqueante de una trayectoria calculada localmente."""

from collections.abc import Callable
from time import monotonic

import streamlit as st


def reiniciar_reproduccion() -> None:
    st.session_state.paso = 0
    st.session_state.reproduciendo = False
    st.session_state.proximo_paso = 0.0


def mostrar_reproduccion(pasos: int, dibujar: Callable[[int], None]) -> None:
    """Cada actualización programada muestra a lo sumo un paso adicional."""
    if "paso" not in st.session_state:
        reiniciar_reproduccion()
    estado = st.session_state
    ultimo = pasos - 1

    def programar() -> None:
        estado.proximo_paso = monotonic() + 1.0 / estado.velocidad

    def iniciar() -> None:
        if estado.paso == ultimo:
            estado.paso = 0
        estado.reproduciendo = True
        programar()

    def pausar() -> None:
        estado.reproduciendo = False

    def avanzar() -> None:
        pausar()
        estado.paso = min(estado.paso + 1, ultimo)

    inicio, pausa, reinicio, avance = st.columns(4)
    inicio.button("Iniciar", key="iniciar", on_click=iniciar, disabled=estado.reproduciendo or ultimo <= 0)
    pausa.button("Pausar", key="pausar", on_click=pausar, disabled=not estado.reproduciendo)
    reinicio.button("Reiniciar", key="reiniciar", on_click=reiniciar_reproduccion)
    avance.button("Avanzar un paso", key="avanzar", on_click=avanzar, disabled=estado.paso >= ultimo)
    velocidad = st.select_slider(
        "Velocidad de visualización (pasos/s)", options=[0.5, 1.0, 2.0, 4.0], value=1.0,
        key="velocidad", on_change=programar,
    )
    intervalo = 1.0 / velocidad

    @st.fragment(run_every=intervalo if estado.reproduciendo else None)
    def fotograma() -> None:
        ahora = monotonic()
        if estado.reproduciendo and ahora + 0.05 >= estado.proximo_paso:
            estado.paso = min(estado.paso + 1, ultimo)
            estado.proximo_paso = ahora + intervalo
            if estado.paso == ultimo:
                estado.reproduciendo = False
                st.rerun()
        st.progress(estado.paso / max(ultimo, 1), text=f"Paso {estado.paso} de {ultimo}")
        dibujar(estado.paso)

    fotograma()

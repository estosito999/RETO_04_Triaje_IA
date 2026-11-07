import streamlit as st

from interfaz.dashboard import mostrar
from interfaz.pitch import mostrar_pitch


if __name__ == "__main__":
    st.set_page_config(
        page_title="Umbral · Decisiones de triaje", page_icon=":material/monitor_heart:", layout="wide",
        initial_sidebar_state="collapsed",
    )
    modo = st.segmented_control("Vista", ("Pitch", "Laboratorio"), default="Pitch", required=True,
                                key="modo", label_visibility="collapsed")
    if modo == "Laboratorio":
        mostrar()
    else:
        mostrar_pitch()

import streamlit as st

from interfaz.dashboard import mostrar


if __name__ == "__main__":
    st.set_page_config(page_title="Triaje y teleconsulta virtual", page_icon="🩺", layout="wide")
    mostrar()

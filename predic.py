import streamlit as st
import random

# Configuración de la página
st.set_page_config(page_title="¿Qué comer hoy?", page_icon="🍴")

# Estilo sencillo con Markdown
st.title("🍴 Selector de Comida")
st.write("¿No sabes qué cocinar o pedir? Deja que la suerte decida por ti.")

# Lista de opciones (puedes agregar o quitar las que quieras)
opciones = [
    "Tacos al pastor", 
    "Ensalada César con pollo", 
    "Pizza artesanal", 
    "Sushi", 
    "Pasta Carbonara", 
    "Hamburguesa con papas",
    "Bowl de Poke",
    "Chilaquiles",
    "Sopa de verduras y carne asada",
    "Comida China"
]

# Interfaz de usuario
st.divider()

if st.button('¡Decidir mi comida!'):
    eleccion = random.choice(opciones)
    st.balloons() # Efecto visual de celebración
    st.success(f"### Hoy deberías comer: **{eleccion}**")
else:
    st.info("Haz clic en el botón para obtener una recomendación.")

# Opción para ver todas las posibilidades
with st.expander("Ver lista de opciones"):
    st.write(", ".join(opciones))S
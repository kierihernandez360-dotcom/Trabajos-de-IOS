import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import uuid
import time

# --- CONFIGURACIÓN BASE DE DATOS ---
DB_NAME = "tienda_suplementos_v3.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventario 
                          (id_item INTEGER PRIMARY KEY, 
                           marca TEXT, producto TEXT, sabor TEXT, 
                           presentacion TEXT, stock INTEGER, p_compra REAL, p_venta REAL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS ventas 
                          (transaccion_id TEXT, fecha TEXT, hora TEXT, marca TEXT, producto TEXT, 
                           sabor TEXT, presentacion TEXT, cantidad INTEGER, 
                           p_venta REAL, total REAL)''')
        
        cursor.execute("SELECT COUNT(*) FROM inventario")
        if cursor.fetchone()[0] == 0:
            catalogo_real = [
                ("Optimum Nutrition", "Gold Standard 100% Whey", "Double Rich Chocolate", "5 Lbs"),
                ("Dymatize", "ISO 100", "Gourmet Chocolate", "5 Lbs"),
                ("MuscleTech", "Nitro-Tech", "Milk Chocolate", "4 Lbs"),
                ("Psychotic", "Insane Labz Pre-Workout", "Fruit Punch", "35 Servings"),
                ("Birdman", "Creatina Monohidratada", "Sin Sabor", "500g"),
                ("C4 Cellucor", "Original Pre-Workout", "Icy Blue Razz", "30 Servings"),
                ("Animal", "Animal Pak", "N/A", "44 Packs")
            ]
            items = [(i, m, p, s, pr, 10, 0.0, 500.0) for i, (m, p, s, pr) in enumerate(catalogo_real, 1)]
            cursor.executemany("INSERT INTO inventario VALUES (?,?,?,?,?,?,?,?)", items)
        conn.commit()

def run_query(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

def get_df(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql_query(query, conn, params=params)

# --- INTERFAZ ---
st.set_page_config(page_title="Nutri-Pro POS", layout="wide", page_icon="💊")
init_db()

if 'carrito' not in st.session_state: 
    st.session_state.carrito = []

st.sidebar.title("🚀 NUTRI-PRO SYSTEM")
menu = ["🛒 Realizar Venta", "📦 Ver Inventario", "🛠 Ajustar Stock", "📊 Historial"]
choice = st.sidebar.selectbox("Navegación:", menu)

if choice == "🛒 Realizar Venta":
    st.header("🛒 Punto de Venta")
    df_inv = get_df("SELECT * FROM inventario WHERE stock > 0")
    
    if not df_inv.empty:
        col1, col2 = st.columns([1, 1])
        with col1:
            df_inv['label'] = df_inv['marca'] + " " + df_inv['producto'] + " (" + df_inv['sabor'] + ")"
            opcion = st.selectbox("Seleccionar Suplemento:", df_inv['label'])
            item = df_inv[df_inv['label'] == opcion].iloc[0]
            
            st.info(f"Disponibles: {item['stock']} unidades")
            cant = st.number_input("Cantidad:", 1, int(item['stock']))
            
            if st.button("➕ Añadir al carrito"):
                st.session_state.carrito.append({
                    'id': item['id_item'], 'marca': item['marca'], 'producto': item['producto'], 
                    'cantidad': cant, 'precio': item['p_venta'], 'subtotal': item['p_venta'] * cant
                })
                st.toast(f"Agregado: {item['producto']}") # Notificación pequeña arriba
                time.sleep(0.5)
                st.rerun()
        
        with col2:
            st.subheader("Resumen de Compra")
            if st.session_state.carrito:
                df_c = pd.DataFrame(st.session_state.carrito)
                st.dataframe(df_c[['marca', 'producto', 'cantidad', 'subtotal']], use_container_width=True, hide_index=True)
                
                total = df_c['subtotal'].sum()
                st.write(f"## Total: ${total:,.2f}")
                
                if st.button("✅ FINALIZAR COMPRA"):
                    # 1. Animación de globos
                    st.balloons()
                    
                    # 2. Lógica de Base de Datos
                    t_id = str(uuid.uuid4())[:8].upper()
                    f = datetime.now().strftime("%Y-%m-%d")
                    h = datetime.now().strftime("%H:%M:%S")
                    
                    for p in st.session_state.carrito:
                        run_query("INSERT INTO ventas VALUES (?,?,?,?,?,?,?,?,?,?)", 
                                  (t_id, f, h, p['marca'], p['producto'], "", "", p['cantidad'], p['precio'], p['subtotal']))
                        run_query("UPDATE inventario SET stock = stock - ? WHERE id_item = ?", (p['cantidad'], p['id']))
                    
                    # 3. Mensaje de éxito
                    st.success(f"¡Venta #{t_id} exitosa!")
                    st.session_state.carrito = []
                    # Esperamos un poco para que se vean los globos antes de limpiar
                    time.sleep(2)
                    st.rerun()
            else:
                st.write("El carrito está vacío.")
    else:
        st.warning("No hay productos con stock.")

elif choice == "📦 Ver Inventario":
    st.header("Inventario Actual")
    st.dataframe(get_df("SELECT marca, producto, sabor, presentacion, stock, p_venta FROM inventario"), use_container_width=True)

elif choice == "🛠 Ajustar Stock":
    st.header("Configuración de Productos")
    id_prod = st.number_input("ID Producto:", 1, 20)
    res = get_df("SELECT * FROM inventario WHERE id_item = ?", (id_prod,))
    if not res.empty:
        with st.form("update"):
            st.write(f"Editando: {res.iloc[0]['producto']}")
            n_stock = st.number_input("Stock", 0, 1000, int(res.iloc[0]['stock']))
            n_precio = st.number_input("Precio", 0.0, 5000.0, float(res.iloc[0]['p_venta']))
            if st.form_submit_button("Actualizar"):
                run_query("UPDATE inventario SET stock=?, p_venta=? WHERE id_item=?", (n_stock, n_precio, id_prod))
                st.success("Cambios guardados")
                st.rerun()

elif choice == "📊 Historial":
    st.header("Ventas Realizadas")
    st.dataframe(get_df("SELECT * FROM ventas"), use_container_width=True)
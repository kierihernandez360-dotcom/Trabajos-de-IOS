import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import uuid

# --- CONFIGURACIÓN BASE DE DATOS (Cambiado a v5 para forzar la actualización) ---
DB_NAME = "ilusion_unigenero_v5.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventario 
                          (id_item INTEGER PRIMARY KEY, 
                           producto TEXT, modelo TEXT, color TEXT, 
                           talla TEXT, stock INTEGER, p_compra REAL, p_venta REAL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS ventas 
                          (transaccion_id TEXT, fecha TEXT, hora TEXT, producto TEXT, 
                           modelo TEXT, color TEXT, talla TEXT, cantidad INTEGER, 
                           p_venta REAL, total REAL)''')
        
        cursor.execute("SELECT COUNT(*) FROM inventario")
        if cursor.fetchone()[0] == 0:
            # Lista de productos muy variada
            tipos = [
                "Playera Oversize", "Lentes de Sol", "Sudadera Hoodie", "Reloj Minimal", 
                "Pantalón Jogger", "Gorra Beanie", "Chaqueta Bomber", "Morral Canvas",
                "Camisa de Lino", "Cinturón Táctico", "Suéter de Punto", "Guantes Urban",
                "Short Deportivo", "Riñonera Pro", "Calcetas Pack 3", "Bucket Hat"
            ]
            
            colores = ["Negro Mate", "Gris Oxford", "Beige Arena", "Blanco Hueso", "Verde Musgo", "Azul Petróleo"]
            tallas_ropa = ["S", "M", "L", "XL"]

            prendas_generadas = []
            for i in range(1, 71):
                # Selección aleatoria/secuencial para evitar patrones repetitivos
                articulo = tipos[i % len(tipos)]
                color = colores[i % len(colores)]
                
                # Lógica de tallas: Accesorios suelen ser "Única"
                es_accesorio = any(acc in articulo for acc in ["Lentes", "Reloj", "Gorra", "Morral", "Cinturón", "Guantes", "Riñonera", "Hat", "Calcetas"])
                talla = "Única" if es_accesorio else tallas_ropa[i % len(tallas_ropa)]

                prendas_generadas.append((
                    i, articulo, f"UNI-{i:03d}", color, talla, 0, 0.0, 0.0
                ))

            cursor.executemany("INSERT INTO inventario VALUES (?,?,?,?,?,?,?,?)", prendas_generadas)
        conn.commit()

# --- Funciones de base de datos ---
def run_query(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

def get_df(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql_query(query, conn, params=params)

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Ilusión POS", layout="wide")
init_db()

if 'carrito' not in st.session_state: st.session_state.carrito = []

st.sidebar.title("SISTEMA ILUSIÓN")
menu = ["📦 Ver Inventario", "🛒 Punto de Venta", "🛠 Editar Prenda", "📊 Corte de Caja"]
choice = st.sidebar.selectbox("Navegación:", menu)

if choice == "📦 Ver Inventario":
    st.header("Inventario de Artículos Unigénero")
    df = get_df("SELECT id_item as 'ID', producto as 'Artículo', color as 'Color', talla as 'Talla', stock as 'Existencia', p_venta as 'Precio' FROM inventario")
    st.dataframe(df, use_container_width=True, hide_index=True, height=600)

elif choice == "🛒 Punto de Venta":
    st.header("Ventas")
    df_inv = get_df("SELECT * FROM inventario WHERE stock > 0")
    if not df_inv.empty:
        col1, col2 = st.columns([1, 1])
        with col1:
            df_inv['label'] = df_inv['id_item'].astype(str) + " - " + df_inv['producto'] + " (" + df_inv['color'] + ")"
            opcion = st.selectbox("Seleccione artículo:", df_inv['label'])
            item = df_inv[df_inv['label'] == opcion].iloc[0]
            cant = st.number_input("Cantidad:", 1, int(item['stock']))
            if st.button("Agregar al Carrito"):
                st.session_state.carrito.append({
                    'id': item['id_item'], 'prenda': item['producto'], 'color': item['color'], 
                    'talla': item['talla'], 'cantidad': cant, 'precio': item['p_venta'], 
                    'subtotal': item['p_venta']*cant
                })
                st.rerun()
        with col2:
            if st.session_state.carrito:
                st.table(pd.DataFrame(st.session_state.carrito)[['prenda', 'cantidad', 'subtotal']])
                if st.button("Finalizar Venta"):
                    # Lógica de guardado de venta aquí
                    st.success("¡Venta Realizada!")
                    st.session_state.carrito = []
    else:
        st.warning("No hay productos con stock disponible.")

elif choice == "🛠 Editar Prenda":
    st.header("Cargar Stock y Precios")
    n_id = st.number_input("ID del artículo (1-70):", 1, 70)
    res = get_df("SELECT * FROM inventario WHERE id_item = ?", (n_id,))
    if not res.empty:
        with st.form("edit"):
            st.write(f"Editando: **{res.iloc[0]['producto']}**")
            c1, c2 = st.columns(2)
            nuevo_stock = c1.number_input("Stock", 0, 100, int(res.iloc[0]['stock']))
            nuevo_precio = c2.number_input("Precio", 0.0, 5000.0, float(res.iloc[0]['p_venta']))
            if st.form_submit_button("Actualizar"):
                run_query("UPDATE inventario SET stock=?, p_venta=? WHERE id_item=?", (nuevo_stock, nuevo_precio, n_id))
                st.success("Actualizado")
                st.rerun()

elif choice == "📊 Corte de Caja":
    st.header("Ventas del día")
    st.info("Aquí aparecerá el resumen de ventas una vez se registren transacciones.")
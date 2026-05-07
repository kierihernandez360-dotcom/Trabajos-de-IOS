import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import uuid
import os
import streamlit.components.v1 as components

# --- CONFIGURACIÓN BASE DE DATOS ---
DB_NAME = "ilusion_unigenero_v3.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventario 
                          (id_item INTEGER PRIMARY KEY, 
                           producto TEXT DEFAULT 'Sin asignar', 
                           modelo TEXT DEFAULT '-', 
                           color TEXT DEFAULT '-', 
                           talla TEXT DEFAULT '-', 
                           stock INTEGER DEFAULT 0, 
                           p_compra REAL DEFAULT 0.0, 
                           p_venta REAL DEFAULT 0.0)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS ventas 
                          (transaccion_id TEXT, fecha TEXT, hora TEXT, producto TEXT, 
                           modelo TEXT, color TEXT, talla TEXT, cantidad INTEGER, 
                           p_venta REAL, total REAL)''')
        
        # --- AUTOMATIZACIÓN: GENERAR 1 AL 70 SIN BOTONES ---
        cursor.execute("SELECT COUNT(*) FROM inventario")
        if cursor.fetchone()[0] < 70:
            for i in range(1, 71):
                cursor.execute("INSERT OR IGNORE INTO inventario (id_item) VALUES (?)", (i,))
        conn.commit()

def run_query(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

def get_df(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql_query(query, conn, params=params)

# --- INICIALIZACIÓN ---
st.set_page_config(page_title="Ilusión POS", layout="wide")
init_db()

if 'carrito' not in st.session_state: st.session_state.carrito = []

# --- NAVEGACIÓN ---
st.sidebar.title("SISTEMA ILUSIÓN")
menu = ["📦 Ver Inventario", "🛒 Punto de Venta", "🛠 Configurar Prendas (1-70)", "📊 Corte de Caja"]
choice = st.sidebar.selectbox("Seleccione opción", menu)

# --- 1. VER INVENTARIO (VISTA COMO LA IMAGEN) ---
if choice == "📦 Ver Inventario":
    st.header("Estado Actual del Inventario")
    df = get_df("SELECT id_item as 'N°', producto as 'Prenda', modelo, color, talla, stock, p_venta as 'Precio' FROM inventario ORDER BY id_item ASC")
    st.dataframe(df, use_container_width=True, hide_index=True, height=800)

# --- 2. PUNTO DE VENTA ---
elif choice == "🛒 Punto de Venta":
    st.header("Registrar Venta")
    df_inv = get_df("SELECT * FROM inventario WHERE stock > 0 AND producto != 'Sin asignar'")
    
    if not df_inv.empty:
        c1, c2 = st.columns([1, 1.2])
        with c1:
            df_inv['display'] = df_inv['id_item'].astype(str) + " - " + df_inv['producto'] + " (" + df_inv['color'] + ")"
            opcion = st.selectbox("Seleccionar Prenda para vender", df_inv['display'])
            item = df_inv[df_inv['display'] == opcion].iloc[0]
            
            st.info(f"**Talla:** {item['talla']} | **Precio:** ${item['p_venta']:,.2f}")
            cant = st.number_input("Cantidad", 1, int(item['stock']))
            
            if st.button("➕ Agregar", use_container_width=True):
                st.session_state.carrito.append({
                    'id': item['id_item'], 'prenda': item['producto'], 'modelo': item['modelo'], 
                    'color': item['color'], 'talla': item['talla'], 'cantidad': cant, 
                    'precio': item['p_venta'], 'subtotal': item['p_venta']*cant
                })
                st.rerun()

        with c2:
            if st.session_state.carrito:
                st.subheader("Carrito")
                df_c = pd.DataFrame(st.session_state.carrito)
                st.table(df_c[['prenda', 'color', 'talla', 'cantidad', 'subtotal']])
                total = df_c['subtotal'].sum()
                if st.button(f"Finalizar Venta (${total:,.2f})", type="primary"):
                    t_id = str(uuid.uuid4())[:6].upper()
                    for i in st.session_state.carrito:
                        run_query("INSERT INTO ventas VALUES (?,?,?,?,?,?,?,?,?,?)", 
                                  (t_id, datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M"),
                                   i['prenda'], i['modelo'], i['color'], i['talla'], i['cantidad'], i['precio'], i['subtotal']))
                        run_query("UPDATE inventario SET stock = stock - ? WHERE id_item = ?", (i['cantidad'], i['id']))
                    st.success("Venta Guardada")
                    st.session_state.carrito = []
                    st.rerun()
    else:
        st.warning("No hay productos configurados con stock disponible.")

# --- 3. CONFIGURAR PRENDAS (AQUÍ ES DONDE LLENAS LOS DATOS) ---
elif choice == "🛠 Configurar Prendas (1-70)":
    st.header("Llenar Información de Prendas")
    st.write("Selecciona un número del 1 al 70 para asignar qué prenda es, su color, talla y precio.")
    
    n_prenda = st.number_input("Número de espacio a editar:", 1, 70)
    datos = get_df("SELECT * FROM inventario WHERE id_item = ?", (n_prenda,))
    
    if not datos.empty:
        with st.form("form_admin"):
            c1, c2 = st.columns(2)
            nombre = c1.text_input("¿Qué prenda es? (ej. Playera)", datos.iloc[0]['producto'])
            modelo = c2.text_input("Modelo", datos.iloc[0]['modelo'])
            
            c3, c4, c5 = st.columns(3)
            color = c3.text_input("Color", datos.iloc[0]['color'])
            talla = c4.text_input("Talla", datos.iloc[0]['talla'])
            stock = c5.number_input("Stock Actual", 0, 1000, int(datos.iloc[0]['stock']))
            
            c6, c7 = st.columns(2)
            p_c = c6.number_input("Costo Compra $", 0.0, 5000.0, float(datos.iloc[0]['p_compra']))
            p_v = c7.number_input("Precio Venta $", 0.0, 5000.0, float(datos.iloc[0]['p_venta']))
            
            if st.form_submit_button(f"Guardar Cambios en Prenda {n_prenda}"):
                run_query("""UPDATE inventario SET producto=?, modelo=?, color=?, talla=?, 
                             stock=?, p_compra=?, p_venta=? WHERE id_item=?""",
                          (nombre, modelo, color, talla, stock, p_c, p_v, n_prenda))
                st.success(f"Espacio {n_prenda} actualizado correctamente.")
                st.rerun()

# --- 4. CORTE DE CAJA ---
elif choice == "📊 Corte de Caja":
    st.header("Resumen de Ventas")
    fecha = st.date_input("Día", datetime.now())
    df_v = get_df("SELECT * FROM ventas WHERE fecha = ?", (fecha.strftime("%Y-%m-%d"),))
    if not df_v.empty:
        st.metric("Total Recaudado", f"${df_v['total'].sum():,.2f}")
        st.dataframe(df_v, use_container_width=True)
    else:
        st.info("Aún no hay ventas registradas hoy.")
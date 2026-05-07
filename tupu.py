import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import uuid

# --- CONFIGURACIÓN BASE DE DATOS ---
DB_NAME = "ilusion_unigenero_v4.db"

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
        
        # --- CARGA AUTOMÁTICA DE 70 ARTÍCULOS VARIADOS ---
        cursor.execute("SELECT COUNT(*) FROM inventario")
        if cursor.fetchone()[0] == 0:
            # Lista ampliada para mayor variedad (Ropa + Accesorios)
            articulos_base = [
                "Playera Oversize", "Sudadera Hoodie", "Pantalón Jogger", "Chaqueta Bomber", 
                "Camisa de Lino", "Gorra Beanie", "Short Canvas", "Trench Coat", 
                "Suéter de Punto", "Chaleco Acolchado", "Tenis Urban", "Playera Tank",
                "Pantalón Cargo", "Chaqueta Denim", "Mochila Minimal", "Lentes de Sol",
                "Guantes de Piel", "Cinturón de Lona", "Reloj Analógico", "Bufanda Infinita",
                "Riñonera Técnica", "Calcetas Altas", "Bota Militar", "Bucket Hat", "Totebag"
            ]
            
            colores = ["Negro", "Blanco", "Gris Oxford", "Beige", "Verde Olivo", "Azul Marino", "Arena"]
            tallas_ropa = ["S", "M", "L", "XL"]
            tallas_acc = ["Única"]

            prendas_generadas = []
            for i in range(1, 71):
                # Selección circular para evitar repeticiones excesivas
                articulo = articulos_base[(i-1) % len(articulos_base)]
                color = colores[(i-1) % len(colores)]
                
                # Asignar talla "Única" si es un accesorio
                es_accesorio = articulo in ["Lentes de Sol", "Guantes de Piel", "Cinturón de Lona", 
                                          "Reloj Analógico", "Bufanda Infinita", "Riñonera Técnica", 
                                          "Mochila Minimal", "Gorra Beanie", "Bucket Hat", "Totebag"]
                
                talla = tallas_acc[0] if es_accesorio else tallas_ropa[(i-1) % len(tallas_ropa)]

                prendas_generadas.append((
                    i, 
                    articulo, 
                    f"UNI-{i:03d}", 
                    color, 
                    talla, 
                    0,   # Stock inicial
                    0.0, # Precio compra
                    0.0  # Precio venta
                ))

            cursor.executemany("""INSERT INTO inventario 
                                  (id_item, producto, modelo, color, talla, stock, p_compra, p_venta) 
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", prendas_generadas)
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
menu = ["📦 Ver Inventario", "🛒 Punto de Venta", "🛠 Editar Prenda", "📊 Corte de Caja"]
choice = st.sidebar.selectbox("Opciones:", menu)

# --- 1. VER INVENTARIO ---
if choice == "📦 Ver Inventario":
    st.header("Inventario Completo (70 Artículos)")
    df = get_df("SELECT id_item as 'ID', producto as 'Artículo', color as 'Color', talla as 'Talla', stock as 'Stock', p_venta as 'Precio' FROM inventario ORDER BY id_item ASC")
    st.dataframe(df, use_container_width=True, hide_index=True, height=600)

# --- 2. PUNTO DE VENTA ---
elif choice == "🛒 Punto de Venta":
    st.header("Punto de Venta")
    df_inv = get_df("SELECT * FROM inventario WHERE stock > 0")
    
    if not df_inv.empty:
        c1, c2 = st.columns([1, 1.2])
        with c1:
            df_inv['label'] = df_inv['id_item'].astype(str) + " - " + df_inv['producto'] + " (" + df_inv['color'] + ")"
            opcion = st.selectbox("Buscar artículo:", df_inv['label'])
            item = df_inv[df_inv['label'] == opcion].iloc[0]
            
            st.info(f"**Talla:** {item['talla']} | **Precio:** ${item['p_venta']:,.2f}")
            cant = st.number_input("Cantidad:", 1, int(item['stock']))
            
            if st.button("➕ Agregar", use_container_width=True):
                st.session_state.carrito.append({
                    'id': item['id_item'], 'prenda': item['producto'], 'color': item['color'], 
                    'talla': item['talla'], 'cantidad': cant, 'precio': item['p_venta'], 
                    'subtotal': item['p_venta']*cant
                })
                st.rerun()
        
        with c2:
            if st.session_state.carrito:
                st.subheader("Carrito")
                df_c = pd.DataFrame(st.session_state.carrito)
                st.table(df_c[['prenda', 'color', 'cantidad', 'subtotal']])
                total = df_c['subtotal'].sum()
                if st.button(f"Confirmar Venta ${total:,.2f}", type="primary", use_container_width=True):
                    t_id = str(uuid.uuid4())[:6].upper()
                    for i in st.session_state.carrito:
                        run_query("INSERT INTO ventas VALUES (?,?,?,?,?,?,?,?,?,?)", 
                                  (t_id, datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M"),
                                   i['prenda'], "MOD", i['color'], i['talla'], i['cantidad'], i['precio'], i['subtotal']))
                        run_query("UPDATE inventario SET stock = stock - ? WHERE id_item = ?", (i['cantidad'], i['id']))
                    st.success("Venta exitosa")
                    st.session_state.carrito = []
                    st.rerun()
    else:
        st.warning("Sin stock disponible.")

# --- 3. EDITAR ARTÍCULO ---
elif choice == "🛠 Editar Prenda":
    st.header("Configurar Prenda o Accesorio")
    n_item = st.number_input("ID de artículo (1-70):", 1, 70)
    datos = get_df("SELECT * FROM inventario WHERE id_item = ?", (n_item,))
    
    if not datos.empty:
        with st.form("edit_form"):
            st.subheader(f"Editando: {datos.iloc[0]['producto']}")
            c1, c2 = st.columns(2)
            nombre = c1.text_input("Nombre", datos.iloc[0]['producto'])
            color = c2.text_input("Color", datos.iloc[0]['color'])
            
            c3, c4, c5 = st.columns(3)
            talla = c3.text_input("Talla", datos.iloc[0]['talla'])
            stock = c4.number_input("Stock", 0, 500, int(datos.iloc[0]['stock']))
            p_v = c5.number_input("Precio Venta", 0.0, 5000.0, float(datos.iloc[0]['p_venta']))
            
            if st.form_submit_button("Guardar"):
                run_query("UPDATE inventario SET producto=?, color=?, talla=?, stock=?, p_venta=? WHERE id_item=?",
                          (nombre, color, talla, stock, p_v, n_item))
                st.rerun()

# --- 4. CORTE DE CAJA ---
elif choice == "📊 Corte de Caja":
    st.header("Ventas de Hoy")
    fecha = datetime.now().strftime("%Y-%m-%d")
    df_v = get_df("SELECT * FROM ventas WHERE fecha = ?", (fecha,))
    if not df_v.empty:
        st.metric("Total", f"${df_v['total'].sum():,.2f}")
        st.dataframe(df_v, use_container_width=True)
    else:
        st.info("Sin ventas.")
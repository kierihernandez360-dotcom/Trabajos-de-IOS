import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import uuid
import os
import streamlit.components.v1 as components

# --- CONFIGURACIÓN BASE DE DATOS ---
DB_NAME = "ilusion_unigenero_v2.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Se añade 'color' y 'talla' explícitamente a la estructura principal
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
                          (transaccion_id TEXT, fecha TEXT, hora TEXT, modelo TEXT, 
                           color TEXT, talla TEXT, cantidad INTEGER, p_venta REAL, total REAL)''')
        conn.commit()

def run_query(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

def get_df(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql_query(query, conn, params=params)

def ejecutar_impresion(html_content):
    unique_id = str(uuid.uuid4())[:8]
    component_script = f"""
    <div id="ticket-{unique_id}" style="display:none;">{html_content}</div>
    <script>
        (function() {{
            var content = document.getElementById('ticket-{unique_id}').innerHTML;
            var win = window.open('', 'PRINT', 'height=600,width=400');
            win.document.write('<html><head><title>Imprimir</title></head><body style="margin:0;">' + content + '</body></html>');
            win.document.close();
            win.focus();
            win.print();
            win.close();
        }})();
    </script>
    """
    components.html(component_script, height=0)

# --- INICIALIZACIÓN ---
st.set_page_config(page_title="Ilusión Unigénero", layout="wide")
init_db()

if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'ticket_a_imprimir' not in st.session_state: st.session_state.ticket_a_imprimir = None

# --- NAVEGACIÓN ---
st.sidebar.title("SISTEMA ILUSIÓN")
menu = ["📦 Ver Inventario", "🛒 Punto de Venta", "🛠 Admin (Lote 1-70)", "📊 Corte de Caja", "💾 Respaldos"]
choice = st.sidebar.selectbox("Seleccione opción", menu)

if st.session_state.ticket_a_imprimir:
    ejecutar_impresion(st.session_state.ticket_a_imprimir)
    st.session_state.ticket_a_imprimir = None

# --- 1. VER INVENTARIO ---
if choice == "📦 Ver Inventario":
    st.header("Inventario Completo (Unigénero)")
    df = get_df("SELECT id_item as 'N°', producto as 'Prenda', modelo, color, talla, stock, p_venta as 'Precio' FROM inventario ORDER BY id_item ASC")
    st.dataframe(df, use_container_width=True, hide_index=True)

# --- 2. PUNTO DE VENTA ---
elif choice == "🛒 Punto de Venta":
    st.header("Registrar Venta")
    # Solo muestra lo que tiene stock
    df_inv = get_df("SELECT * FROM inventario WHERE stock > 0")
    
    if not df_inv.empty:
        c1, c2 = st.columns([1, 1.2])
        with c1:
            # Seleccionamos por ID o por nombre para facilitar
            df_inv['etiqueta'] = df_inv['id_item'].astype(str) + " - " + df_inv['producto'] + " (" + df_inv['color'] + ")"
            opcion = st.selectbox("Buscar Prenda", df_inv['etiqueta'])
            item_sel = df_inv[df_inv['etiqueta'] == opcion].iloc[0]
            
            st.info(f"**Detalles:** {item_sel['modelo']} | Color: {item_sel['color']} | Talla: {item_sel['talla']}")
            st.success(f"**Disponible:** {item_sel['stock']} pzs | **Precio:** ${item_sel['p_venta']:,.2f}")
            
            cant = st.number_input("Cantidad", 1, int(item_sel['stock']))
            
            if st.button("➕ Agregar al Carrito", use_container_width=True):
                st.session_state.carrito.append({
                    'id': item_sel['id_item'], 'modelo': item_sel['modelo'], 'color': item_sel['color'],
                    'talla': item_sel['talla'], 'cantidad': cant, 'precio': item_sel['p_venta'], 'subtotal': item_sel['p_venta']*cant
                })
                st.rerun()
            
            if st.button("🗑️ Vaciar Carrito"):
                st.session_state.carrito = []
                st.rerun()

        with c2:
            if st.session_state.carrito:
                st.subheader("Resumen")
                df_c = pd.DataFrame(st.session_state.carrito)
                st.table(df_c[['modelo', 'color', 'talla', 'cantidad', 'subtotal']])
                total = df_c['subtotal'].sum()
                
                if st.button(f"✅ Cobrar ${total:,.2f}", type="primary", use_container_width=True):
                    t_id = str(uuid.uuid4())[:6].upper()
                    for i in st.session_state.carrito:
                        run_query("INSERT INTO ventas VALUES (?,?,?,?,?,?,?,?,?)", 
                                  (t_id, datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M"), 
                                   i['modelo'], i['color'], i['talla'], i['cantidad'], i['precio'], i['subtotal']))
                        run_query("UPDATE inventario SET stock = stock - ? WHERE id_item = ?", (i['cantidad'], i['id']))
                    st.success("Venta Exitosa")
                    st.session_state.carrito = []
                    st.rerun()

# --- 3. ADMIN (CONFIGURAR 1-70) ---
elif choice == "🛠 Admin (Lote 1-70)":
    st.header("Gestión de Espacios 1 al 70")
    
    # Botón para crear los 70 registros si la base es nueva
    if st.button("⚡ Crear/Resetear espacios del 1 al 70"):
        for i in range(1, 71):
            run_query("INSERT OR IGNORE INTO inventario (id_item) VALUES (?)", (i,))
        st.success("Se han habilitado los 70 espacios correctamente.")

    n_prenda = st.number_input("Selecciona el número de prenda a configurar (1-70):", 1, 70)
    
    # Traer datos actuales de ese número
    datos = get_df("SELECT * FROM inventario WHERE id_item = ?", (n_prenda,))
    
    if not datos.empty:
        st.subheader(f"Editando Prenda N° {n_prenda}")
        with st.form("form_admin"):
            col1, col2 = st.columns(2)
            # Aquí es donde defines qué es la prenda y qué color tiene
            nombre = col1.text_input("¿Qué prenda es? (ej. Playera, Pantalón)", datos.iloc[0]['producto'])
            modelo = col2.text_input("Modelo / Código", datos.iloc[0]['modelo'])
            
            col3, col4, col5 = st.columns(3)
            color = col3.text_input("Color", datos.iloc[0]['color'])
            talla = col4.text_input("Talla (ej. CH, M, G, Única)", datos.iloc[0]['talla'])
            stock = col5.number_input("Cantidad en Existencia", 0, 1000, int(datos.iloc[0]['stock']))
            
            col6, col7 = st.columns(2)
            p_c = col6.number_input("Costo de Compra $", 0.0, 5000.0, float(datos.iloc[0]['p_compra']))
            p_v = col7.number_input("Precio de Venta $", 0.0, 5000.0, float(datos.iloc[0]['p_venta']))
            
            if st.form_submit_button("💾 Guardar Cambios en Espacio " + str(n_prenda)):
                run_query("""UPDATE inventario SET producto=?, modelo=?, color=?, talla=?, 
                             stock=?, p_compra=?, p_venta=? WHERE id_item=?""",
                          (nombre, modelo, color, talla, stock, p_c, p_v, n_prenda))
                st.success(f"¡Prenda {n_prenda} actualizada!")
                st.rerun()

# --- 4. CORTE DE CAJA ---
elif choice == "📊 Corte de Caja":
    st.header("Corte de Caja")
    fecha = st.date_input("Selecciona el día", datetime.now())
    df_v = get_df("SELECT * FROM ventas WHERE fecha = ?", (fecha.strftime("%Y-%m-%d"),))
    
    if not df_v.empty:
        st.metric("Venta Total del Día", f"${df_v['total'].sum():,.2f}")
        st.dataframe(df_v, use_container_width=True)
    else:
        st.info("No hay ventas registradas en esta fecha.")

# --- 5. RESPALDOS ---
elif choice == "💾 Respaldos":
    st.header("Respaldos")
    if os.path.exists(DB_NAME):
        with open(DB_NAME, "rb") as f:
            st.download_button("📥 Descargar Base de Datos", f, "respaldo_inventario.db")
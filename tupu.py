import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import uuid
import os
import streamlit.components.v1 as components

# --- CONFIGURACIÓN BASE DE DATOS ---
DB_NAME = "ilusion_unigenero.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Tabla inventario adaptada a ropa unigénero
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventario 
                          (id_item INTEGER PRIMARY KEY, producto TEXT, modelo TEXT, 
                           color TEXT, talla TEXT, stock INTEGER, p_compra REAL, 
                           p_venta REAL, categoria TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS ventas 
                          (transaccion_id TEXT, fecha TEXT, hora TEXT, modelo TEXT, 
                           talla TEXT, cantidad INTEGER, p_venta REAL, total REAL)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS apartados 
                          (id TEXT, cliente TEXT, fecha TEXT, modelo TEXT, 
                           talla TEXT, cantidad INTEGER, estado TEXT)''')
        conn.commit()

def run_query(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

def get_df(query, params=()):
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql_query(query, conn, params=params)

# --- FUNCIÓN DE IMPRESIÓN ---
def ejecutar_impresion(html_content):
    unique_id = str(uuid.uuid4())[:8]
    component_script = f"""
    <div id="ticket-{unique_id}" style="display:none;">{html_content}</div>
    <script>
        (function() {{
            var content = document.getElementById('ticket-{unique_id}').innerHTML;
            var win = window.open('', 'PRINT', 'height=600,width=400');
            win.document.write('<html><head><title>Imprimir Ticket</title></head><body>' + content + '</body></html>');
            win.document.close();
            win.focus();
            win.print();
            win.close();
        }})();
    </script>
    """
    components.html(component_script, height=0)

def generar_ticket_html(titulo, id_doc, items, total, cliente=None):
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    filas = "".join([f"<tr><td>{it['modelo']}</td><td align='center'>{it['cantidad']}</td><td align='right'>${it['subtotal']:,.2f}</td></tr>" for it in items])
    cli_html = f'<p style="font-size:11px;"><b>Cliente:</b> {cliente}</p>' if cliente else ''
    return f"""
    <div style="font-family: 'Courier New', monospace; width: 250px; padding: 10px; border: 1px solid #000;">
        <center><h2 style="margin:0;">ILUSIÓN</h2><p style="font-size:12px; margin:0;">Ropa Unigénero</p></center>
        <hr>
        <p style="font-size:11px;"><b>{titulo}</b>: #{id_doc}<br><b>Fecha:</b> {fecha}</p>
        {cli_html}
        <table style="width:100%; font-size:10px;">{filas}</table>
        <hr><h3 align="right">TOTAL: ${total:,.2f}</h3>
    </div>
    """

# --- INICIALIZACIÓN ---
st.set_page_config(page_title="Ilusión Unigénero", layout="wide")
init_db()

if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'ticket_a_imprimir' not in st.session_state: st.session_state.ticket_a_imprimir = None

# --- NAVEGACIÓN ---
st.sidebar.title("SISTEMA ILUSIÓN")
menu = ["📦 Inventario", "🛒 Punto de Venta", "📝 Apartados", "📊 Corte de Caja", "📉 Historial", "🛠 Admin", "💾 Respaldos"]
choice = st.sidebar.selectbox("Menú Principal", menu)

if st.session_state.ticket_a_imprimir:
    ejecutar_impresion(st.session_state.ticket_a_imprimir)
    st.session_state.ticket_a_imprimir = None

# --- 1. INVENTARIO ---
if choice == "📦 Inventario":
    st.header("Inventario de Ropa Unigénero")
    df = get_df("SELECT id_item as '#', producto, modelo, color, talla, stock, p_venta as 'Precio' FROM inventario ORDER BY id_item ASC")
    st.dataframe(df, use_container_width=True, hide_index=True)

# --- 2. PUNTO DE VENTA ---
elif choice == "🛒 Punto de Venta":
    st.header("Venta de Prendas")
    df_inv = get_df("SELECT * FROM inventario WHERE stock > 0")
    
    if not df_inv.empty:
        c1, c2 = st.columns([1, 1.5])
        with c1:
            # Selector por Modelo
            mod_sel = st.selectbox("Seleccionar Modelo", sorted(df_inv['modelo'].unique()))
            df_f = df_inv[df_inv['modelo'] == mod_sel]
            
            talla_sel = st.selectbox("Talla", sorted(df_f['talla'].unique()))
            item = df_f[df_f['talla'] == talla_sel].iloc[0]
            
            st.success(f"Disponible: {item['stock']} piezas | Precio: ${item['p_venta']:,.2f}")
            cant = st.number_input("Cantidad a vender", 1, int(item['stock']))
            
            if st.button("➕ Agregar a la lista", use_container_width=True):
                st.session_state.carrito.append({
                    'modelo': item['modelo'], 'talla': item['talla'], 
                    'cantidad': cant, 'precio': item['p_venta'], 'subtotal': item['p_venta']*cant
                })
                st.rerun()

            if st.button("🗑️ Vaciar Lista", type="secondary"):
                st.session_state.carrito = []
                st.rerun()

        with c2:
            if st.session_state.carrito:
                st.subheader("Lista de Compra")
                df_car = pd.DataFrame(st.session_state.carrito)
                st.table(df_car[['modelo', 'talla', 'cantidad', 'subtotal']])
                total_v = df_car['subtotal'].sum()
                
                if st.button(f"🛒 Finalizar Venta (${total_v:,.2f})", type="primary", use_container_width=True):
                    t_id = str(uuid.uuid4())[:6].upper()
                    now = datetime.now()
                    for i in st.session_state.carrito:
                        run_query("INSERT INTO ventas VALUES (?,?,?,?,?,?,?,?)", 
                                  (t_id, now.strftime("%Y-%m-%d"), now.strftime("%H:%M"), i['modelo'], i['talla'], i['cantidad'], i['precio'], i['subtotal']))
                        run_query("UPDATE inventario SET stock = stock - ? WHERE modelo=? AND talla=?", (i['cantidad'], i['modelo'], i['talla']))
                    st.session_state.ticket_a_imprimir = generar_ticket_html("TICKET VENTA", t_id, st.session_state.carrito, total_v)
                    st.session_state.carrito = []
                    st.rerun()

# --- 6. ADMIN (LISTA DEL 1 AL 70) ---
elif choice == "🛠 Admin":
    st.header("Configuración de Inventario (Prendas 1 - 70)")
    
    # Crear los 70 espacios si la base está vacía
    if st.button("🔄 Inicializar/Resetear espacios 1-70"):
        for i in range(1, 71):
            run_query("INSERT OR IGNORE INTO inventario (id_item, producto, modelo, stock, p_compra, p_venta) VALUES (?,?,?,?,?,?)", 
                      (i, "Ropa", f"Prenda {i}", 0, 0.0, 0.0))
        st.success("Espacios del 1 al 70 listos.")

    tab1, tab2 = st.tabs(["Editar Prenda Individual", "Vista Rápida"])
    
    with tab1:
        num_item = st.number_input("Número de Prenda a editar (1-70)", 1, 70)
        curr = get_df("SELECT * FROM inventario WHERE id_item = ?", (num_item,))
        
        if not curr.empty:
            with st.form("edit_form"):
                col1, col2 = st.columns(2)
                nombre = col1.text_input("Nombre/Tipo de Prenda", curr.iloc[0]['producto'])
                modelo = col2.text_input("Código/Modelo", curr.iloc[0]['modelo'])
                
                c3, c4, c5 = st.columns(3)
                talla = c3.selectbox("Talla", ["N/A", "XS", "S", "M", "L", "XL", "Única"], index=0)
                color = c4.text_input("Color", curr.iloc[0]['color'] if curr.iloc[0]['color'] else "Neutro")
                stock = c5.number_input("Cantidad en Stock", 0, 500, int(curr.iloc[0]['stock']))
                
                c6, c7 = st.columns(2)
                pc = c6.number_input("Costo Compra $", 0.0, 10000.0, float(curr.iloc[0]['p_compra']))
                pv = c7.number_input("Precio Venta $", 0.0, 10000.0, float(curr.iloc[0]['p_venta']))
                
                if st.form_submit_button("Actualizar Prenda"):
                    run_query("UPDATE inventario SET producto=?, modelo=?, color=?, talla=?, stock=?, p_compra=?, p_venta=? WHERE id_item=?",
                              (nombre, modelo, color, talla, stock, pc, pv, num_item))
                    st.success(f"Prenda {num_item} actualizada.")
                    st.rerun()

    with tab2:
        st.dataframe(get_df("SELECT * FROM inventario ORDER BY id_item ASC"), use_container_width=True)

# --- 4. CORTE DE CAJA ---
elif choice == "📊 Corte de Caja":
    st.header("Reporte de Ganancias")
    periodo = st.radio("Periodo:", ["Hoy", "Este Mes"], horizontal=True)
    f_busqueda = datetime.now().strftime("%Y-%m-%d") if periodo == "Hoy" else datetime.now().strftime("%Y-%m-") + "%"
    
    df_v = get_df("SELECT * FROM ventas WHERE fecha LIKE ?", (f_busqueda,))
    if not df_v.empty:
        total = df_v['total'].sum()
        st.metric("Total Vendido", f"${total:,.2f}")
        st.dataframe(df_v, use_container_width=True)
    else:
        st.warning("No hay ventas en este periodo.")

# --- 7. RESPALDOS ---
elif choice == "💾 Respaldos":
    st.header("Respaldos")
    if os.path.exists(DB_NAME):
        with open(DB_NAME, "rb") as f:
            st.download_button("📥 Descargar Base de Datos", f, "respaldo_ilusion.db")
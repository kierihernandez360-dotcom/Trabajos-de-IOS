import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import uuid
import io
import os
import streamlit.components.v1 as components

# --- CONFIGURACIÓN BASE DE DATOS ---
DB_NAME = "ilusion_v14.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventario 
                          (producto TEXT, modelo TEXT, color TEXT, talla TEXT, 
                           stock INTEGER, p_compra REAL, p_venta REAL, imagen TEXT,
                           PRIMARY KEY (producto, modelo, color, talla))''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS ventas 
                          (transaccion_id TEXT, fecha TEXT, hora TEXT, producto TEXT, modelo TEXT, 
                           color TEXT, talla TEXT, cantidad INTEGER, p_venta REAL, total REAL, estado TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS apartados 
                          (id TEXT, cliente TEXT, fecha TEXT, producto TEXT, modelo TEXT, 
                           color TEXT, talla TEXT, cantidad INTEGER, estado TEXT)''')
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
            win.document.write('<html><head><title>Imprimir</title></head><body>' + content + '</body></html>');
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
    return f"""
    <div style="font-family: 'Courier New', monospace; width: 250px; padding: 10px; background: white; color: black; border: 1px solid #ddd;">
        <center><h2 style="margin:0;">ILUSIÓN</h2><p style="font-size:12px; margin:0;">Punto de Venta</p></center>
        <hr>
        <p style="font-size:11px;"><b>{titulo}</b>: #{id_doc}<br><b>Fecha:</b> {fecha}</p>
        {f'<p style="font-size:11px;"><b>Cliente:</b> {cliente}</p>' if cliente else ''}
        <table style="width:100%; font-size:10px;">
            {"".join([f"<tr><td>{it['modelo']}</td><td align='center'>{it['cantidad']}</td><td align='right'>${it['subtotal']:,.2f}</td></tr>" for it in items])}
        </table>
        <hr><h3 align="right">TOTAL: ${total:,.2f}</h3>
    </div>
    """

# --- INICIALIZACIÓN ---
st.set_page_config(page_title="Ilusion Pro V14", layout="wide")
init_db()

if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'ticket_a_imprimir' not in st.session_state: st.session_state.ticket_a_imprimir = None

# --- NAVEGACIÓN ---
st.sidebar.title("SISTEMA ILUSION")
menu = ["📦 Inventario", "🛒 Punto de Venta", "📝 Apartados", "📊 Corte de Caja", "📉 Historial", "🛠 Admin", "💾 Respaldos"]
choice = st.sidebar.selectbox("Opciones", menu)

if st.session_state.ticket_a_imprimir:
    ejecutar_impresion(st.session_state.ticket_a_imprimir)
    st.session_state.ticket_a_imprimir = None

# --- 1. INVENTARIO ---
if choice == "📦 Inventario":
    st.header("Inventario de Prendas")
    st.dataframe(get_df("SELECT * FROM inventario"), width='stretch')

# --- 2. PUNTO DE VENTA (CON BOTÓN LIMPIAR) ---
elif choice == "🛒 Punto de Venta":
    st.header("Nueva Operación")
    df_inv = get_df("SELECT * FROM inventario WHERE stock > 0")
    
    if not df_inv.empty:
        c1, c2 = st.columns(2)
        with c1:
            mod_sel = st.selectbox("Modelo", sorted(df_inv['modelo'].unique()))
            df_f = df_inv[df_inv['modelo'] == mod_sel]
            col_sel = st.selectbox("Color", sorted(df_f['color'].unique()))
            df_f = df_f[df_f['color'] == col_sel]
            talla_sel = st.selectbox("Talla", sorted(df_f['talla'].unique()))
            item = df_f[df_f['talla'] == talla_sel].iloc[0]
            
            st.info(f"Stock: {item['stock']} | Precio: ${item['p_venta']:,.2f}")
            cant = st.number_input("Cantidad", 1, int(item['stock']))
            
            if st.button("➕ Agregar al Carrito", use_container_width=True):
                st.session_state.carrito.append({
                    'producto': item['producto'], 'modelo': item['modelo'], 'color': item['color'],
                    'talla': item['talla'], 'cantidad': cant, 'precio': item['p_venta'], 'subtotal': item['p_venta']*cant
                })
                st.rerun()
            
            # BOTÓN LIMPIAR CAMPOS / CARRITO
            if st.button("🗑️ Limpiar Todo", type="secondary", use_container_width=True):
                st.session_state.carrito = []
                st.rerun()

        with c2:
            if st.session_state.carrito:
                st.subheader("Resumen de Venta")
                st.table(pd.DataFrame(st.session_state.carrito)[['modelo', 'talla', 'cantidad', 'subtotal']])
                total_v = sum(i['subtotal'] for i in st.session_state.carrito)
                if st.button(f"✅ Finalizar e Imprimir (${total_v:,.2f})", type="primary", use_container_width=True):
                    t_id = str(uuid.uuid4())[:8].upper()
                    now = datetime.now()
                    for i in st.session_state.carrito:
                        run_query("INSERT INTO ventas VALUES (?,?,?,?,?,?,?,?,?,?,?)", 
                                  (t_id, now.strftime("%Y-%m-%d"), now.strftime("%H:%M"), i['producto'], i['modelo'], i['color'], i['talla'], i['cantidad'], i['precio'], i['subtotal'], "COMPLETADA"))
                        run_query("UPDATE inventario SET stock = stock - ? WHERE modelo=? AND color=? AND talla=?", (i['cantidad'], i['modelo'], i['color'], i['talla']))
                    st.session_state.ticket_a_imprimir = generar_ticket_html("TICKET VENTA", t_id, st.session_state.carrito, total_v)
                    st.session_state.carrito = []
                    st.rerun()

# --- 3. APARTADOS ---
elif choice == "📝 Apartados":
    st.header("Control de Apartados")
    df_inv = get_df("SELECT * FROM inventario WHERE stock > 0")
    with st.form("ap_f"):
        cli = st.text_input("Nombre de la Clienta")
        df_inv['lbl'] = df_inv['modelo'] + " | " + df_inv['color'] + " (" + df_inv['talla'] + ")"
        sel = st.selectbox("Prenda", df_inv['lbl'] if not df_inv.empty else ["Vacío"])
        cnt = st.number_input("Cant", 1)
        if st.form_submit_button("Guardar Apartado"):
            r = df_inv[df_inv['lbl'] == sel].iloc[0]
            ap_id = "AP-" + str(uuid.uuid4())[:4].upper()
            run_query("INSERT INTO apartados VALUES (?,?,?,?,?,?,?,?,?)", (ap_id, cli, datetime.now().strftime("%Y-%m-%d"), r['producto'], r['modelo'], r['color'], r['talla'], cnt, "ACTIVO"))
            run_query("UPDATE inventario SET stock = stock - ? WHERE modelo=? AND color=? AND talla=?", (cnt, r['modelo'], r['color'], r['talla']))
            st.session_state.ticket_a_imprimir = generar_ticket_html("VALE APARTADO", ap_id, [{'modelo': r['modelo'], 'cantidad': cnt, 'subtotal': r['p_venta']*cnt}], r['p_venta']*cnt, cliente=cli)
            st.rerun()

# --- 4. CORTE DE CAJA (NUEVO) ---
elif choice == "📊 Corte de Caja":
    st.header("Corte de Caja y Utilidades")
    periodo = st.radio("Seleccione Periodo de Corte:", ["Hoy", "Esta Semana", "Este Mes"], horizontal=True)
    
    # Definición de fechas
    hoy = datetime.now()
    if periodo == "Hoy":
        fecha_inicio = hoy.strftime("%Y-%m-%d")
    elif periodo == "Esta Semana":
        fecha_inicio = (hoy - timedelta(days=hoy.weekday())).strftime("%Y-%m-%d")
    else: # Este Mes
        fecha_inicio = hoy.strftime("%Y-%m-01")
    
    # Consulta uniendo ventas con inventario para obtener p_compra
    query_corte = """
        SELECT v.*, i.p_compra 
        FROM ventas v 
        LEFT JOIN inventario i ON v.modelo = i.modelo AND v.color = i.color AND v.talla = i.talla
        WHERE v.fecha >= ? AND v.estado = 'COMPLETADA'
    """
    df_corte = get_df(query_corte, (fecha_inicio,))
    
    if not df_corte.empty:
        total_ventas = df_corte['total'].sum()
        total_costos = (df_corte['cantidad'] * df_corte['p_compra']).sum()
        utilidad = total_ventas - total_costos
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Ingresos Totales", f"${total_ventas:,.2f}")
        m2.metric("Inversión (Costos)", f"${total_costos:,.2f}")
        m3.metric("Utilidad Neta", f"${utilidad:,.2f}", delta=f"{ (utilidad/total_ventas)*100:.1f}%" if total_ventas > 0 else "0%")
        
        st.subheader("Detalle de Ventas en el Periodo")
        st.dataframe(df_corte[['transaccion_id', 'fecha', 'modelo', 'talla', 'cantidad', 'total']], width='stretch')
    else:
        st.info(f"No hay ventas registradas desde el {fecha_inicio}")

# --- 5. HISTORIAL ---
elif choice == "📉 Historial":
    st.header("Historial de Operaciones")
    st.subheader("Ventas")
    st.dataframe(get_df("SELECT * FROM ventas"), width='stretch')
    st.subheader("Apartados")
    st.dataframe(get_df("SELECT * FROM apartados"), width='stretch')

# --- 6. ADMIN ---
elif choice == "🛠 Admin":
    with st.form("adm"):
        c1, c2, c3, c4 = st.columns(4)
        p, m, col, t = c1.text_input("Art"), c2.text_input("Mod"), c3.text_input("Col"), c4.text_input("Tal")
        s = st.number_input("Stock", 0)
        pc, pv = st.number_input("Costo", 0.0), st.number_input("Venta", 0.0)
        if st.form_submit_button("Guardar en Inventario"):
            run_query("INSERT OR REPLACE INTO inventario VALUES (?,?,?,?,?,?,?,?)", (p,m,col,t,s,pc,pv,""))
            st.success("Guardado.")

# --- 7. RESPALDOS ---
elif choice == "💾 Respaldos":
    st.header("Respaldos")
    if os.path.exists(DB_NAME):
        with open(DB_NAME, "rb") as f:
            st.download_button("📥 Descargar DB", f, f"Backup_Ilusion_{datetime.now().strftime('%Y%m%d')}.db")
    
    file_up = st.file_uploader("Restaurar", type=["db"])
    if file_up and st.button("🚀 Restaurar"):
        with open(DB_NAME, "wb") as f: f.write(file_up.getbuffer())
        st.rerun()
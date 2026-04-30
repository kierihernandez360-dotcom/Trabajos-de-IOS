import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import uuid
import os
import random
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

# --- FUNCIÓN PARA CARGAR 50 DATOS DE PRUEBA ---
def cargar_50_datos():
    productos = ["Bra Push Up", "Panty Clásico", "Faja Reductora", "Pijama Seda", "Baby Doll", "Bra Deportivo", "Body Encaje"]
    modelos = ["MOD-101", "MOD-202", "MOD-303", "MOD-404", "MOD-505", "MOD-606", "MOD-707", "MOD-808"]
    colores = ["Negro", "Blanco", "Nude", "Rojo", "Azul Marino", "Rosa Pastel"]
    tallas = ["CH", "M", "G", "XG", "32B", "34B", "36B", "38B"]

    datos_inventario = []
    while len(datos_inventario) < 50:
        prod = random.choice(productos)
        mod = random.choice(modelos)
        col = random.choice(colores)
        tal = random.choice(tallas)
        
        # Evitar duplicados
        if not any(x[1] == mod and x[2] == col and x[3] == tal for x in datos_inventario):
            stock = random.randint(5, 30)
            p_compra = round(random.uniform(100.0, 350.0), 2)
            p_venta = round(p_compra * 1.6, 2)
            datos_inventario.append((prod, mod, col, tal, stock, p_compra, p_venta, ""))

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.executemany('INSERT OR REPLACE INTO inventario VALUES (?,?,?,?,?,?,?,?)', datos_inventario)
        conn.commit()

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
    rows = "".join([f"<tr><td>{it['modelo']}</td><td align='center'>{it['cantidad']}</td><td align='right'>${it['subtotal']:,.2f}</td></tr>" for it in items])
    return f"""
    <div style="font-family: 'Courier New', monospace; width: 250px; padding: 10px; background: white; color: black; border: 1px solid #ddd;">
        <center><h2 style="margin:0;">ILUSIÓN</h2><p style="font-size:12px; margin:0;">Punto de Venta</p></center>
        <hr>
        <p style="font-size:11px;"><b>{titulo}</b>: #{id_doc}<br><b>Fecha:</b> {fecha}</p>
        {f'<p style="font-size:11px;"><b>Cliente:</b> {cliente}</p>' if cliente else ''}
        <table style="width:100%; font-size:10px;">
            {rows}
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

# --- LÓGICA DE SECCIONES ---

if choice == "📦 Inventario":
    st.header("Inventario de Prendas")
    df_inv = get_df("SELECT * FROM inventario")
    if df_inv.empty:
        st.warning("El inventario está vacío.")
        if st.button("✨ Cargar 50 datos de prueba"):
            cargar_50_datos()
            st.rerun()
    else:
        st.dataframe(df_inv, use_container_width=True)

elif choice == "🛒 Punto de Venta":
    st.header("Nueva Operación")
    df_inv = get_df("SELECT * FROM inventario WHERE stock > 0")
    
    if not df_inv.empty:
        c1, c2 = st.columns([1, 1])
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
                    'talla': item['talla'], 'cantidad': int(cant), 'precio': float(item['p_venta']), 'subtotal': float(item['p_venta']*cant)
                })
                st.rerun()
            
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
    else:
        st.error("No hay stock disponible en el inventario.")

elif choice == "📝 Apartados":
    st.header("Control de Apartados")
    df_inv = get_df("SELECT * FROM inventario WHERE stock > 0")
    if not df_inv.empty:
        with st.form("ap_f"):
            cli = st.text_input("Nombre de la Clienta")
            df_inv['lbl'] = df_inv['modelo'] + " | " + df_inv['color'] + " (" + df_inv['talla'] + ")"
            sel = st.selectbox("Prenda", df_inv['lbl'])
            cnt = st.number_input("Cant", 1)
            if st.form_submit_button("Guardar Apartado"):
                r = df_inv[df_inv['lbl'] == sel].iloc[0]
                ap_id = "AP-" + str(uuid.uuid4())[:4].upper()
                run_query("INSERT INTO apartados VALUES (?,?,?,?,?,?,?,?,?)", (ap_id, cli, datetime.now().strftime("%Y-%m-%d"), r['producto'], r['modelo'], r['color'], r['talla'], cnt, "ACTIVO"))
                run_query("UPDATE inventario SET stock = stock - ? WHERE modelo=? AND color=? AND talla=?", (cnt, r['modelo'], r['color'], r['talla']))
                st.session_state.ticket_a_imprimir = generar_ticket_html("VALE APARTADO", ap_id, [{'modelo': r['modelo'], 'cantidad': cnt, 'subtotal': r['p_venta']*cnt}], r['p_venta']*cnt, cliente=cli)
                st.rerun()
    else:
        st.info("No hay productos disponibles para apartar.")

elif choice == "📊 Corte de Caja":
    st.header("Corte de Caja y Utilidades")
    periodo = st.radio("Seleccione Periodo:", ["Hoy", "Esta Semana", "Este Mes"], horizontal=True)
    hoy = datetime.now()
    if periodo == "Hoy": f_inicio = hoy.strftime("%Y-%m-%d")
    elif periodo == "Esta Semana": f_inicio = (hoy - timedelta(days=hoy.weekday())).strftime("%Y-%m-%d")
    else: f_inicio = hoy.strftime("%Y-%m-01")
    
    query_corte = """
        SELECT v.*, i.p_compra 
        FROM ventas v 
        LEFT JOIN inventario i ON v.modelo = i.modelo AND v.color = i.color AND v.talla = i.talla
        WHERE v.fecha >= ? AND v.estado = 'COMPLETADA'
    """
    df_corte = get_df(query_corte, (f_inicio,))
    
    if not df_corte.empty:
        total_ventas = df_corte['total'].sum()
        total_costos = (df_corte['cantidad'] * df_corte['p_compra']).sum()
        utilidad = total_ventas - total_costos
        m1, m2, m3 = st.columns(3)
        m1.metric("Ingresos", f"${total_ventas:,.2f}")
        m2.metric("Costos", f"${total_costos:,.2f}")
        m3.metric("Utilidad", f"${utilidad:,.2f}")
        st.dataframe(df_corte, use_container_width=True)
    else:
        st.info("Sin ventas en este periodo.")

elif choice == "📉 Historial":
    st.header("Historial de Operaciones")
    st.subheader("Ventas")
    st.dataframe(get_df("SELECT * FROM ventas"), use_container_width=True)
    st.subheader("Apartados")
    st.dataframe(get_df("SELECT * FROM apartados"), use_container_width=True)

elif choice == "🛠 Admin":
    st.header("Administración de Inventario")
    with st.form("adm"):
        c1, c2, c3, c4 = st.columns(4)
        p = c1.text_input("Producto (ej. Bra)")
        m = c2.text_input("Modelo (ej. MOD-01)")
        col = c3.text_input("Color")
        t = c4.text_input("Talla")
        s = st.number_input("Stock inicial", 0)
        pc = st.number_input("Costo Unitario", 0.0)
        pv = st.number_input("Precio Venta", 0.0)
        if st.form_submit_button("Guardar en Inventario"):
            if p and m:
                run_query("INSERT OR REPLACE INTO inventario VALUES (?,?,?,?,?,?,?,?)", (p,m,col,t,s,pc,pv,""))
                st.success("Producto registrado!")
            else: st.error("Faltan datos.")
    
    if st.button("⚠️ Cargar 50 datos demo ahora"):
        cargar_50_datos()
        st.rerun()

elif choice == "💾 Respaldos":
    st.header("Respaldos")
    if os.path.exists(DB_NAME):
        with open(DB_NAME, "rb") as f:
            st.download_button("📥 Descargar Base de Datos", f, f"Backup_Ilusion_{datetime.now().strftime('%Y%m%d')}.db")

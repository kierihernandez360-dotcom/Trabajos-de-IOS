import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import uuid
import os
import streamlit.components.v1 as components

# --- CONFIGURACIÓN BASE DE DATOS ---
DB_NAME = "ilusion_v14.db"

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # El Inventario no permite duplicados de Producto/Modelo/Color/Talla
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventario 
                          (producto TEXT, modelo TEXT, color TEXT, talla TEXT, 
                           stock INTEGER, p_compra REAL, p_venta REAL, imagen TEXT,
                           PRIMARY KEY (modelo, color, talla))''')
        
        # Las Ventas usan transaccion_id como llave única
        cursor.execute('''CREATE TABLE IF NOT EXISTS ventas 
                          (transaccion_id TEXT PRIMARY KEY, fecha TEXT, hora TEXT, producto TEXT, modelo TEXT, 
                           color TEXT, talla TEXT, cantidad INTEGER, p_venta REAL, total REAL, estado TEXT)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS apartados 
                          (id TEXT PRIMARY KEY, cliente TEXT, fecha TEXT, producto TEXT, modelo TEXT, 
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

# --- FUNCIÓN PARA CARGAR 50 REGISTROS ÚNICOS ---
def cargar_datos_demo():
    # 1. Limpiar tablas para asegurar que no haya nada previo
    run_query("DELETE FROM inventario")
    run_query("DELETE FROM ventas")
    
    # 2. Generar 20 registros de Inventario únicos
    inventario_base = [
        ('Bra', 'BR-101', 'Negro', '34B', 10, 100, 250),
        ('Bra', 'BR-102', 'Blanco', '36C', 15, 110, 280),
        ('Bra', 'BR-103', 'Rojo', '32B', 8, 100, 250),
        ('Pantie', 'PT-201', 'Nude', 'CH', 20, 30, 80),
        ('Pantie', 'PT-202', 'Azul', 'M', 25, 30, 80),
        ('Pantie', 'PT-203', 'Rosa', 'G', 12, 35, 90),
        ('Pijama', 'PJ-501', 'Gris', 'M', 5, 200, 450),
        ('Pijama', 'PJ-502', 'Verde', 'G', 7, 220, 480),
        ('BabyDoll', 'BD-01', 'Negro', 'CH', 4, 150, 390),
        ('BabyDoll', 'BD-02', 'Rojo', 'M', 6, 160, 410),
        ('Deportivo', 'DP-10', 'Negro', 'M', 10, 180, 350),
        ('Deportivo', 'DP-11', 'Gris', 'CH', 8, 180, 350),
        ('Faja', 'FJ-99', 'Beige', 'G', 5, 300, 650),
        ('Media', 'MD-05', 'Negro', 'U', 30, 20, 60),
        ('Media', 'MD-06', 'Blanco', 'U', 20, 20, 60),
        ('Bata', 'BT-12', 'Seda', 'U', 3, 250, 550),
        ('Corset', 'CT-88', 'Blanco', '34B', 2, 400, 950),
        ('Top', 'TP-04', 'Lila', 'CH', 15, 60, 150),
        ('Short', 'SH-22', 'Denim', 'M', 10, 120, 280),
        ('Tirantes', 'TR-01', 'Transp', 'U', 50, 5, 20)
    ]
    
    for p in inventario_base:
        run_query("INSERT INTO inventario VALUES (?,?,?,?,?,?,?,?)", (*p, ""))

    # 3. Generar 30 registros de Ventas únicos (IDs secuenciales)
    hoy = datetime.now()
    for i in range(30):
        v_id = f"V-UNIQUE-{2000 + i}" # ID garantizado único
        item = inventario_base[i % len(inventario_base)]
        fecha = (hoy - timedelta(days=i % 10)).strftime("%Y-%m-%d")
        cant = 1
        total = item[6] * cant
        run_query("INSERT INTO ventas VALUES (?,?,?,?,?,?,?,?,?,?,?)", 
                  (v_id, fecha, "10:00", item[0], item[1], item[2], item[3], cant, item[6], total, "COMPLETADA"))
    
    st.success("✅ Base de datos reiniciada y cargada con 50 registros únicos.")

# --- IMPRESIÓN ---
def ejecutar_impresion(html_content):
    unique_id = str(uuid.uuid4())[:8]
    component_script = f"""
    <div id="ticket-{unique_id}" style="display:none;">{html_content}</div>
    <script>
        (function() {{
            var content = document.getElementById('ticket-{unique_id}').innerHTML;
            var win = window.open('', 'PRINT', 'height=600,width=400');
            win.document.write('<html><head><title>Ticket</title></head><body>' + content + '</body></html>');
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
    return f"""
    <div style="font-family: 'Courier New', monospace; width: 250px; padding: 10px; border: 1px solid #000;">
        <center><b>ILUSIÓN PRO</b></center>
        <hr>
        <p style="font-size:11px;">{titulo}: {id_doc}<br>Fecha: {fecha}</p>
        {f'<p style="font-size:11px;">Cliente: {cliente}</p>' if cliente else ''}
        <table style="width:100%; font-size:10px;">{filas}</table>
        <hr><h3 align="right">TOTAL: ${total:,.2f}</h3>
    </div>
    """

# --- INICIO APP ---
st.set_page_config(page_title="Ilusion V14", layout="wide")
init_db()

if 'carrito' not in st.session_state: st.session_state.carrito = []
if 'ticket_a_imprimir' not in st.session_state: st.session_state.ticket_a_imprimir = None

# Sidebar
st.sidebar.title("SISTEMA ILUSION")
choice = st.sidebar.selectbox("Menú", ["📦 Inventario", "🛒 Punto de Venta", "📝 Apartados", "📊 Corte de Caja", "📉 Historial", "🛠 Admin", "💾 Respaldos"])

if st.session_state.ticket_a_imprimir:
    ejecutar_impresion(st.session_state.ticket_a_imprimir)
    st.session_state.ticket_a_imprimir = None

# --- VISTAS ---

if choice == "📦 Inventario":
    st.header("Inventario Real")
    st.dataframe(get_df("SELECT * FROM inventario"), use_container_width=True)

elif choice == "🛒 Punto de Venta":
    st.header("Caja")
    df_inv = get_df("SELECT * FROM inventario WHERE stock > 0")
    if not df_inv.empty:
        col1, col2 = st.columns([1, 1])
        with col1:
            mod = st.selectbox("Modelo", df_inv['modelo'].unique())
            df_m = df_inv[df_inv['modelo'] == mod]
            color = st.selectbox("Color", df_m['color'].unique())
            df_c = df_m[df_m['color'] == color]
            talla = st.selectbox("Talla", df_c['talla'].unique())
            sel = df_c[df_c['talla'] == talla].iloc[0]
            
            st.metric("Disponible", f"{sel['stock']} pz", f"${sel['p_venta']}")
            cant = st.number_input("Cantidad", 1, int(sel['stock']))
            
            if st.button("➕ Añadir"):
                st.session_state.carrito.append({'producto': sel['producto'], 'modelo': sel['modelo'], 'color': sel['color'], 'talla': sel['talla'], 'cantidad': cant, 'p_venta': sel['p_venta'], 'subtotal': sel['p_venta']*cant})
                st.rerun()
        
        with col2:
            if st.session_state.carrito:
                df_car = pd.DataFrame(st.session_state.carrito)
                st.table(df_car[['modelo', 'talla', 'cantidad', 'subtotal']])
                total = df_car['subtotal'].sum()
                if st.button(f"Pagar ${total:,.2f}"):
                    t_id = f"T-{str(uuid.uuid4())[:6].upper()}"
                    for i in st.session_state.carrito:
                        run_query("INSERT INTO ventas VALUES (?,?,?,?,?,?,?,?,?,?,?)", (t_id, datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%H:%M"), i['producto'], i['modelo'], i['color'], i['talla'], i['cantidad'], i['p_venta'], i['subtotal'], "COMPLETADA"))
                        run_query("UPDATE inventario SET stock = stock - ? WHERE modelo=? AND color=? AND talla=?", (i['cantidad'], i['modelo'], i['color'], i['talla']))
                    st.session_state.ticket_a_imprimir = generar_ticket_html("VENTA", t_id, st.session_state.carrito, total)
                    st.session_state.carrito = []
                    st.rerun()

elif choice == "📊 Corte de Caja":
    st.header("Análisis de Ganancias")
    df_v = get_df("""SELECT v.*, i.p_compra FROM ventas v 
                     LEFT JOIN inventario i ON v.modelo = i.modelo AND v.color = i.color AND v.talla = i.talla""")
    if not df_v.empty:
        df_v['costo_total'] = df_v['cantidad'] * df_v['p_compra']
        df_v['ganancia'] = df_v['total'] - df_v['costo_total']
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Ventas Totales", f"${df_v['total'].sum():,.2f}")
        c2.metric("Inversión", f"${df_v['costo_total'].sum():,.2f}")
        c3.metric("Utilidad Neta", f"${df_v['ganancia'].sum():,.2f}")
        st.bar_chart(df_v.groupby('fecha')['total'].sum())

elif choice == "🛠 Admin":
    st.header("Configuración")
    
    st.subheader("Carga de Datos (Sin Duplicados)")
    if st.button("🚀 Limpiar y Cargar 50 Datos de Prueba"):
        cargar_datos_demo()
        st.rerun()
        
    with st.form("add_p"):
        st.write("Añadir manualmente:")
        c1, c2, c3, c4 = st.columns(4)
        p = c1.text_input("Producto")
        m = c2.text_input("Modelo")
        cl = c3.text_input("Color")
        tl = c4.text_input("Talla")
        st = st.number_input("Stock", 0)
        pc = st.number_input("Costo", 0.0)
        pv = st.number_input("Venta", 0.0)
        if st.form_submit_button("Guardar"):
            run_query("INSERT OR REPLACE INTO inventario VALUES (?,?,?,?,?,?,?,?)", (p,m,cl,tl,st,pc,pv,""))
            st.rerun()

elif choice == "💾 Respaldos":
    st.header("Backup")
    if os.path.exists(DB_NAME):
        with open(DB_NAME, "rb") as f:
            st.download_button("📥 Descargar DB", f, "ilusion_backup.db")
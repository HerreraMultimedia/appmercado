import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import date

st.set_page_config(page_title="Control de Facturas y Precios", layout="wide", page_icon="🛒")

# ----------------- BASE DE DATOS -----------------
def init_db():
    conn = sqlite3.connect("gastos.db")
    c = conn.cursor()
    c.execute("PRAGMA foreign_keys = ON;")
    c.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            categoria TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha DATE NOT NULL,
            supermercado TEXT NOT NULL,
            total REAL NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS detalle_factura (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_id INTEGER,
            producto_id INTEGER,
            cantidad REAL NOT NULL,
            precio_unitario REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (factura_id) REFERENCES facturas (id) ON DELETE CASCADE,
            FOREIGN KEY (producto_id) REFERENCES productos (id) ON DELETE RESTRICT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def get_connection():
    conn = sqlite3.connect("gastos.db")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def obtener_ultimo_precio(nombre_producto):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT df.precio_unitario 
        FROM detalle_factura df
        JOIN productos p ON df.producto_id = p.id
        JOIN facturas f ON df.factura_id = f.id
        WHERE p.nombre = ?
        ORDER BY f.fecha DESC, df.id DESC
        LIMIT 1
    """, (nombre_producto,))
    res = c.fetchone()
    conn.close()
    return float(res[0]) if res else 1.0

# ----------------- VARIABLES DE SESIÓN (ESTADO) -----------------
if "items_factura" not in st.session_state:
    st.session_state.items_factura = []
if "f_supermercado" not in st.session_state:
    st.session_state.f_supermercado = ""
if "f_select_prod" not in st.session_state:
    st.session_state.f_select_prod = "-- Seleccionar existente --"
if "f_input_prod" not in st.session_state:
    st.session_state.f_input_prod = ""
if "f_cantidad" not in st.session_state:
    st.session_state.f_cantidad = 1.0
if "f_precio" not in st.session_state:
    st.session_state.f_precio = 1.00

# ----------------- FUNCIONES DE EVENTOS Y LIMPIEZA -----------------
def on_select_change():
    """Al elegir un desplegable, borra el campo manual y carga el último precio."""
    sel = st.session_state.f_select_prod
    if sel != "-- Seleccionar existente --":
        st.session_state.f_input_prod = ""
        st.session_state.f_precio = obtener_ultimo_precio(sel)

def on_input_change():
    """Al escribir manualmente, anula la selección previa para evitar choques."""
    if st.session_state.f_input_prod.strip():
        st.session_state.f_select_prod = "-- Seleccionar existente --"

def limpiar_formulario_item():
    """Programa la limpieza para el siguiente ciclo de ejecución."""
    st.session_state["_reset_item_form"] = True


def limpiar_factura_completa():
    """Programa la limpieza completa de la factura."""
    st.session_state.items_factura = []
    st.session_state["_reset_factura_completa"] = True

# ----------------- APLICAR LIMPIEZAS PENDIENTES -----------------
# Se ejecuta antes de crear los widgets, evitando errores de session_state.

if st.session_state.pop("_reset_factura_completa", False):
    st.session_state.f_supermercado = ""
    st.session_state.f_select_prod = "-- Seleccionar existente --"
    st.session_state.f_input_prod = ""
    st.session_state.f_cantidad = 1.0
    st.session_state.f_precio = 1.00

elif st.session_state.pop("_reset_item_form", False):
    st.session_state.f_select_prod = "-- Seleccionar existente --"
    st.session_state.f_input_prod = ""
    st.session_state.f_cantidad = 1.0
    st.session_state.f_precio = 1.00

# ----------------- INTERFAZ -----------------
st.title("🛒 Gestor de Facturas y Control de Gastos")

tabs = st.tabs(["🧾 Registrar Factura", "📊 Análisis y Consumo", "📈 Evolución de Precios", "📦 Catálogo de Productos"])

# ----------------- TAB 1: REGISTRAR FACTURA -----------------
with tabs[0]:
    st.header("Nueva Factura")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fecha_compra = st.date_input("Fecha de la compra", value=date.today())
    with col_f2:
        supermercado = st.text_input("Supermercado (ej. Mercadona, Carrefour, Día)", key="f_supermercado").strip().title()

    st.subheader("Agregar Productos")
    
    conn = get_connection()
    df_prods = pd.read_sql("SELECT id, nombre FROM productos ORDER BY nombre ASC", conn)
    conn.close()
    opciones_prods = ["-- Seleccionar existente --"] + df_prods["nombre"].tolist()

    col_p1, col_p2, col_p3, col_p4 = st.columns([3, 1.3, 1.3, 1])
    
    with col_p1:
        st.selectbox("Producto existente", opciones_prods, key="f_select_prod", on_change=on_select_change)
        st.text_input("O producto nuevo", key="f_input_prod", on_change=on_input_change)

    with col_p2:
        st.number_input("Cantidad", min_value=0.01, step=1.0, key="f_cantidad")
    with col_p3:
        st.number_input("Precio Unit. (€)", min_value=0.01, step=0.05, format="%.2f", key="f_precio")
        
    with col_p4:
        st.write("")
        st.write("")
        if st.button("➕ Añadir", use_container_width=True):
            if st.session_state.f_input_prod.strip():
                nombre_final = st.session_state.f_input_prod.strip().title()
            elif st.session_state.f_select_prod != "-- Seleccionar existente --":
                nombre_final = st.session_state.f_select_prod
            else:
                nombre_final = None

            if nombre_final:
                subtotal = round(st.session_state.f_cantidad * st.session_state.f_precio, 2)
                st.session_state.items_factura.append({
                    "nombre": nombre_final,
                    "cantidad": st.session_state.f_cantidad,
                    "precio_unitario": st.session_state.f_precio,
                    "subtotal": subtotal
                })
                # Limpiar sólo la entrada del producto
                limpiar_formulario_item()
                st.rerun()
            else:
                st.error("Selecciona o introduce un producto.")

    # LISTA DE LA FACTURA EN CURSO
    if st.session_state.items_factura:
        st.markdown("---")
        st.markdown("### 🛒 Productos en la compra actual:")
        
        h1, h2, h3, h4, h5 = st.columns([3, 1.5, 1.5, 1.5, 1])
        h1.markdown("**Producto**")
        h2.markdown("**Cantidad**")
        h3.markdown("**Precio Unit.**")
        h4.markdown("**Subtotal**")
        h5.markdown("**Acción**")

        idx_to_remove = None
        for i, item in enumerate(st.session_state.items_factura):
            c1, c2, c3, c4, c5 = st.columns([3, 1.5, 1.5, 1.5, 1])
            c1.write(item["nombre"])
            c2.write(f"{item['cantidad']}")
            c3.write(f"{item['precio_unitario']:.2f} €")
            c4.write(f"{item['subtotal']:.2f} €")
            if c5.button("❌", key=f"del_{i}", help="Eliminar de la lista"):
                idx_to_remove = i

        if idx_to_remove is not None:
            st.session_state.items_factura.pop(idx_to_remove)
            st.rerun()

        total_factura = sum(item["subtotal"] for item in st.session_state.items_factura)
        st.markdown(f"## Total Factura: **{total_factura:.2f} €**")

        c_save, c_clear = st.columns([2, 4])
        with c_save:
            if st.button("💾 Guardar Factura Completa", type="primary", use_container_width=True):
                if not st.session_state.f_supermercado.strip():
                    st.error("Por favor, introduce el nombre del supermercado.")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute("INSERT INTO facturas (fecha, supermercado, total) VALUES (?, ?, ?)",
                                   (fecha_compra, st.session_state.f_supermercado.strip(), total_factura))
                    factura_id = cursor.lastrowid

                    for item in st.session_state.items_factura:
                        cursor.execute("SELECT id FROM productos WHERE nombre = ?", (item["nombre"],))
                        res = cursor.fetchone()
                        if res:
                            prod_id = res[0]
                        else:
                            cursor.execute("INSERT INTO productos (nombre) VALUES (?)", (item["nombre"],))
                            prod_id = cursor.lastrowid
                        
                        cursor.execute("""
                            INSERT INTO detalle_factura (factura_id, producto_id, cantidad, precio_unitario, subtotal)
                            VALUES (?, ?, ?, ?, ?)
                        """, (factura_id, prod_id, item["cantidad"], item["precio_unitario"], item["subtotal"]))

                    conn.commit()
                    conn.close()
                    
                    # Limpiar todo para la siguiente factura
                    limpiar_factura_completa()
                    st.success("¡Factura guardada con éxito!")
                    st.rerun()
        with c_clear:
            if st.button("Vaciar Factura Actual"):
                limpiar_factura_completa()
                st.rerun()

# ----------------- TAB 2: ANÁLISIS Y CONSUMO -----------------
with tabs[1]:
    st.header("Historial de Consumo y Gasto")
    conn = get_connection()

    # Resumen del mes actual
    mes_actual = date.today().strftime("%Y-%m")

    df_mes = pd.read_sql_query("""
        SELECT COALESCE(SUM(total), 0) AS gasto,
               COUNT(*) AS facturas
        FROM facturas
        WHERE strftime('%Y-%m', fecha) = ?
    """, conn, params=(mes_actual,))

    gasto_mes = float(df_mes.iloc[0]["gasto"])
    facturas_mes = int(df_mes.iloc[0]["facturas"])

    st.subheader(f"Gasto acumulado — {date.today().strftime('%m/%Y')}")

    presupuesto = st.number_input(
        "Tu presupuesto mensual (€)",
        min_value=0.0,
        value=200.0,
        step=25.0,
        key="presupuesto_mensual"
    )

    if presupuesto > 0:
        porcentaje = gasto_mes / presupuesto * 100
        restante = presupuesto - gasto_mes

        if porcentaje < 70:
            color = "#198754"
            estado = "Gasto bajo control"
        elif porcentaje < 90:
            color = "#e0a000"
            estado = "Atención: presupuesto próximo al límite"
        else:
            color = "#dc3545"
            estado = "Presupuesto casi agotado o superado"

        barra = min(porcentaje, 100)
        texto_presupuesto = (
            f"Disponible: {restante:.2f} €"
            if restante >= 0
            else f"Exceso: {abs(restante):.2f} €"
        )
    else:
        porcentaje = 0
        barra = 0
        color = "#2878b5"
        estado = "Configura un presupuesto mensual"
        texto_presupuesto = "Sin límite definido"

    st.markdown(
        f"""
        <div style="border-left:8px solid {color};
                    background-color:{color}15;
                    padding:22px;
                    border-radius:10px;
                    margin:10px 0 24px 0;">
            <div style="font-size:15px;color:#666;">
                TOTAL GASTADO ESTE MES
            </div>
            <div style="font-size:38px;font-weight:700;color:{color};">
                {gasto_mes:.2f} €
            </div>
            <div style="font-weight:600;margin:8px 0;">
                {estado}
            </div>
            <div style="background:#ddd;border-radius:10px;height:12px;">
                <div style="background:{color};width:{barra}%;
                            height:12px;border-radius:10px;"></div>
            </div>
            <div style="margin-top:10px;">
                {porcentaje:.1f}% del presupuesto · {texto_presupuesto}
                · {facturas_mes} facturas
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()


    # --------- RESUMEN DEL GASTO DEL MES ACTUAL ---------
    mes_actual = date.today().strftime("%Y-%m")

    df_mes = pd.read_sql_query("""
        SELECT COALESCE(SUM(total), 0) AS gasto_mes,
               COUNT(*) AS num_facturas
        FROM facturas
        WHERE strftime('%Y-%m', fecha) = ?
    """, conn, params=(mes_actual,))

    gasto_mes = float(df_mes.iloc[0]["gasto_mes"])
    num_facturas = int(df_mes.iloc[0]["num_facturas"])

    st.subheader("Gasto del mes actual")


    df_gastos = pd.read_sql("""
        SELECT strftime('%Y-%m', fecha) as mes, SUM(total) as gasto_total
        FROM facturas
        GROUP BY mes
        ORDER BY mes ASC
    """, conn)

    if not df_gastos.empty:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.subheader("Gasto Mensual (€)")
            fig_mes = px.bar(df_gastos, x="mes", y="gasto_total", labels={"mes": "Mes", "gasto_total": "Total (€)"}, text_auto=True)
            st.plotly_chart(fig_mes, use_container_width=True)

        with col_g2:
            st.subheader("Top 10 Productos Más Comprados")
            df_top = pd.read_sql("""
                SELECT p.nombre, SUM(df.cantidad) as total_unidades
                FROM detalle_factura df
                JOIN productos p ON df.producto_id = p.id
                GROUP BY p.id
                ORDER BY total_unidades DESC
                LIMIT 10
            """, conn)
            fig_top = px.bar(df_top, x="total_unidades", y="nombre", orientation="h", labels={"total_unidades": "Cantidad", "nombre": "Producto"})
            fig_top.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_top, use_container_width=True)

        st.subheader("Historial de Facturas")
        df_ultimas = pd.read_sql("SELECT id, fecha, supermercado, total FROM facturas ORDER BY fecha DESC", conn)
        st.dataframe(df_ultimas, use_container_width=True)
    else:
        st.info("No hay facturas registradas todavía.")
    conn.close()

# ----------------- TAB 3: EVOLUCIÓN DE PRECIOS Y TOTALES -----------------
with tabs[2]:
    st.header("Evolución de Precios y Totales")
    conn = get_connection()
    df_prods_existentes = pd.read_sql("SELECT nombre FROM productos ORDER BY nombre ASC", conn)
    
    if not df_prods_existentes.empty:
        prod_analizar = st.selectbox("Selecciona un producto para ver sus métricas:", df_prods_existentes["nombre"])
        
        query_precios = """
            SELECT f.fecha, f.supermercado, df.precio_unitario, df.cantidad, df.subtotal
            FROM detalle_factura df
            JOIN facturas f ON df.factura_id = f.id
            JOIN productos p ON df.producto_id = p.id
            WHERE p.nombre = ?
            ORDER BY f.fecha ASC
        """
        df_hist_precio = pd.read_sql(query_precios, conn, params=(prod_analizar,))
        
        if not df_hist_precio.empty:
            # MÉTRICAS Y TOTALES DEL PRODUCTO
            total_gastado = df_hist_precio["subtotal"].sum()
            total_unidades = df_hist_precio["cantidad"].sum()
            ultimo_precio = df_hist_precio.iloc[-1]["precio_unitario"]
            precio_promedio = total_gastado / total_unidades if total_unidades > 0 else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Último Precio Pagado", f"{ultimo_precio:.2f} €")
            m2.metric("Total Gastado Histórico", f"{total_gastado:.2f} €")
            m3.metric("Total Cantidad Comprada", f"{total_unidades:.2f}")
            m4.metric("Precio Medio Histórico", f"{precio_promedio:.2f} €")

            # GRÁFICA DE EVOLUCIÓN
            fig_precio = px.line(df_hist_precio, x="fecha", y="precio_unitario", color="supermercado", markers=True,
                                 title=f"Evolución del Precio Unitario: {prod_analizar}",
                                 labels={"fecha": "Fecha", "precio_unitario": "Precio Unitario (€)"})
            st.plotly_chart(fig_precio, use_container_width=True)
            
            st.subheader("Desglose Histórico de Compras")
            st.dataframe(df_hist_precio, use_container_width=True)
        else:
            st.warning("Este producto no tiene compras registradas aún.")
    else:
        st.info("No hay productos en el catálogo.")
    conn.close()

# ----------------- TAB 4: CATÁLOGO DE PRODUCTOS -----------------
with tabs[3]:
    st.header("Catálogo de Productos")
    conn = get_connection()

    with st.expander("➕ Añadir Nuevo Producto Manualmente"):
        c_n1, c_n2 = st.columns(2)
        nuevo_p = c_n1.text_input("Nombre", key="cat_nuevo_p").strip().title()
        categoria_p = c_n2.text_input("Categoría (opcional)", key="cat_nuevo_c").strip().title()
        if st.button("Guardar en Catálogo"):
            if nuevo_p:
                try:
                    c = conn.cursor()
                    c.execute("INSERT INTO productos (nombre, categoria) VALUES (?, ?)", (nuevo_p, categoria_p))
                    conn.commit()
                    st.success(f"Producto '{nuevo_p}' añadido.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Ya existe un producto con ese nombre.")
            else:
                st.error("El nombre no puede estar vacío.")

    st.subheader("Editar o Eliminar del Catálogo")
    df_catalogo = pd.read_sql("SELECT id, nombre, categoria FROM productos ORDER BY nombre ASC", conn)

    if not df_catalogo.empty:
        prod_map = {f"{row['nombre']} (ID: {row['id']})": row['id'] for _, row in df_catalogo.iterrows()}
        seleccion = st.selectbox("Selecciona un producto para gestionar:", list(prod_map.keys()))
        selected_id = prod_map[seleccion]

        prod_actual = df_catalogo[df_catalogo['id'] == selected_id].iloc[0]

        col_e1, col_e2 = st.columns(2)
        with col_e1:
            nuevo_nombre_val = st.text_input("Editar Nombre", value=prod_actual['nombre'], key=f"edit_n_{selected_id}")
        with col_e2:
            nueva_cat_val = st.text_input("Editar Categoría", value=prod_actual['categoria'] if prod_actual['categoria'] else "", key=f"edit_c_{selected_id}")

        col_b1, col_b2 = st.columns([1, 4])
        with col_b1:
            if st.button("✏️ Actualizar"):
                if nuevo_nombre_val:
                    try:
                        c = conn.cursor()
                        c.execute("UPDATE productos SET nombre = ?, categoria = ? WHERE id = ?", 
                                  (nuevo_nombre_val.strip().title(), nueva_cat_val.strip().title(), selected_id))
                        conn.commit()
                        st.success("¡Producto actualizado!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Ya existe otro producto con ese nombre.")
                else:
                    st.error("El nombre no puede quedar vacío.")

        with col_b2:
            if st.button("🗑️ Eliminar Producto"):
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM detalle_factura WHERE producto_id = ?", (selected_id,))
                count = c.fetchone()[0]

                if count > 0:
                    st.error(f"No se puede eliminar: este producto está asociado a {count} factura(s).")
                else:
                    c.execute("DELETE FROM productos WHERE id = ?", (selected_id,))
                    conn.commit()
                    st.success("Producto eliminado del catálogo.")
                    st.rerun()

        st.divider()
        st.subheader("Listado General")
        st.dataframe(df_catalogo, use_container_width=True)
    else:
        st.info("No hay productos en el catálogo.")

    conn.close()
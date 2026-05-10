import streamlit as st
import sqlite3
import pandas as pd
import os

# 1. CONFIGURACION DE LA PAGINA
st.set_page_config(
    page_title="Tech Monitor",
    layout="wide"
)

def load_data():
    """
    Se conecta a la base de datos en data/db/tech_prices_gold.db
    subiendo un nivel desde la carpeta visualization/
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Subimos un nivel para salir de visualization/ y luego entramos a data/db/
    db_path = os.path.join(base_dir, '..', 'data', 'db', 'tech_prices_gold.db')
    
    if not os.path.exists(db_path):
        st.error(f"No se encontro la base de datos en: {db_path}")
        return pd.DataFrame()
        
    try:
        conn = sqlite3.connect(db_path)
        # Cargamos la tabla products
        df = pd.read_sql("SELECT * FROM products", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error al leer la base de datos: {e}")
        return pd.DataFrame()

# --- TITULO Y DESCRIPCION ---
st.title("Monitor de Laptops Refurbished")
st.markdown("""
Este panel muestra los datos procesados de Amazon, eBay y Newegg. 
Filtra por especificaciones tecnicas para encontrar las mejores ofertas.
""")

df = load_data()

if not df.empty:
    # --- BARRA LATERAL: FILTROS ---
    st.sidebar.header("Filtros de Busqueda")
    
    # Filtro por Marca
    marcas_disponibles = sorted(df['brand'].unique())
    marcas_sel = st.sidebar.multiselect("Marcas", marcas_disponibles, default=marcas_disponibles)
    
    # Filtro por RAM
    # Nos aseguramos de que ram_gb sea numerico y eliminamos nulos para el slider
    df_ram = df.dropna(subset=['ram_gb'])
    if not df_ram.empty:
        ram_list = sorted([int(x) for x in df_ram['ram_gb'].unique()])
        ram_min = st.sidebar.select_slider("RAM Minima (GB)", options=ram_list, value=min(ram_list))
    else:
        ram_min = 0
    
    # Filtro por Precio
    precio_max = st.sidebar.slider(
        "Presupuesto Maximo ($)", 
        min_value=float(df['price'].min()), 
        max_value=float(df['price'].max()), 
        value=float(df['price'].max())
    )
    
    # Filtro por Plataforma
    plataformas = st.sidebar.multiselect("Plataformas", df['platform'].unique(), default=df['platform'].unique())

    # --- APLICAR LOGICA DE FILTRADO ---
    df_filtered = df[
        (df['brand'].isin(marcas_sel)) & 
        (df['ram_gb'] >= ram_min) & 
        (df['price'] <= precio_max) &
        (df['platform'].isin(plataformas))
    ]

    # --- METRICAS PRINCIPALES ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Laptops encontradas", len(df_filtered))
    m2.metric("Precio Promedio", f"${df_filtered['price'].mean():.2f}")
    
    if not df_filtered.empty:
        mejor_oferta = df_filtered.loc[df_filtered['price'].idxmin()]
        m3.metric("Precio mas bajo", f"${mejor_oferta['price']:.2f}")

    # --- VISUALIZACION DE DATOS ---
    st.subheader("Inventario Detectado")
    
    # Configuracion de columnas para que la URL sea un link
    st.dataframe(
        df_filtered[['brand', 'title', 'ram_gb', 'storage_gb', 'price', 'platform', 'url']],
        column_config={
            "url": st.column_config.LinkColumn("Ir al Anuncio"),
            "price": st.column_config.NumberColumn("Precio ($)", format="$%.2f"),
            "ram_gb": "RAM (GB)",
            "storage_gb": "Disco (GB)"
        },
        use_container_width=True,
        hide_index=True
    )

    # --- GRAFICOS ---
    st.divider()
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Distribucion por Marca")
        st.bar_chart(df_filtered['brand'].value_counts())
        
    with c2:
        st.subheader("Precios Promedio por Plataforma")
        if not df_filtered.empty:
            avg_prices = df_filtered.groupby('platform')['price'].mean()
            st.bar_chart(avg_prices)

else:
    st.info("La base de datos esta vacia o no existe. Ejecuta data_cleaning.py para procesar los archivos JSON.")

# Pie de pagina
st.caption("Pixor Tech Data Pipeline - Dashboard v1.0")
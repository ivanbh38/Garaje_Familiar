import streamlit as st
import pandas as pd
from datetime import datetime, time
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Garajes Pontika/Beraun", page_icon="🅿️")

RELACION = {
    "Furgoneta": "Pontika 1",
    "Zafira": "Beraun",
    "Astra": "Pontika 2"
}

ARCHIVO_DB = 'reservas.csv'

def cargar_datos():
    if os.path.exists(ARCHIVO_DB):
        df = pd.read_csv(ARCHIVO_DB)
        df['Inicio'] = pd.to_datetime(df['Inicio'])
        df['Fin'] = pd.to_datetime(df['Fin'])
        if 'Llegado' not in df.columns:
            df['Llegado'] = False
        return df
    return pd.DataFrame(columns=["Coche", "Usuario", "Inicio", "Fin", "Garaje", "Llegado"])

def guardar_datos(df):
    df.to_csv(ARCHIVO_DB, index=False)

df = cargar_datos()
ahora = datetime.now()

# --- 1. ESTADO ACTUAL ---
st.title("🚗 Control de Garajes- v1.0.1 🚗")

st.subheader("Estado de los garajes ahora:")
cols = st.columns(3)

for i, (coche, garaje) in enumerate(RELACION.items()):
    # Buscamos la reserva activa o la más próxima no llegada
    reserva_coche = df[(df['Coche'] == coche) & (df['Llegado'] == False)].sort_values('Inicio').head(1)
    
    with cols[i % 3]:
        if not reserva_coche.empty:
            res = reserva_coche.iloc[0]
            hora_fin_str = res['Fin'].strftime('%H:%M')
            
            if ahora >= res['Inicio'] and ahora <= res['Fin']:
                st.success(f"🟢 **{garaje}**\n\nLIBRE")
                st.caption(f"Usa: {res['Usuario']}\nFin: {hora_fin_str}")
            elif ahora > res['Fin']:
                st.warning(f"🟠 **{garaje}**\n\nPENDIENTE")
                st.caption(f"Debía volver: {hora_fin_str}")
            else:
                st.error(f"🔴 **{garaje}**\n\nOCUPADO")
                st.caption(f"Próxima: {res['Inicio'].strftime('%H:%M')}")
        else:
            st.error(f"🔴 **{garaje}**\n\nOCUPADO")
            st.caption(f"Sin reservas")

# --- 2. BOTÓN DE CONFIRMACIÓN DE LLEGADA ---
st.divider()
pendientes = df[(df['Llegado'] == False) & (df['Inicio'] <= ahora)]

if not pendientes.empty:
    st.subheader("🏁 Confirmar Llegada")
    for idx, row in pendientes.iterrows():
        col_txt, col_btn = st.columns([2, 1])
        with col_txt:
            st.write(f"¿Ha vuelto la **{row['Coche']}** de {row['Usuario']}?")
        with col_btn:
            if st.button(f"Confirmar ✅", key=f"llegada_{idx}"):
                df.at[idx, 'Llegado'] = True
                guardar_datos(df)
                st.rerun()

# --- 3. FORMULARIO DE RESERVA ---
st.divider()
st.subheader("📅 Nueva Reserva")
with st.form("nueva_reserva"):
    usuario = st.selectbox("Usuario", ["Sergio", "Sylvia", "Iván", "Maider"])
    coche_res = st.selectbox("Coche", list(RELACION.keys()))
    fecha_res = st.date_input("Día", value=ahora.date(), min_value=ahora.date())
    
    c1, c2 = st.columns(2)
    with c1:
        h_inicio = st.time_input("Hora Inicio", value=time(9, 0))
    with c2:
        h_fin = st.time_input("Hora Fin", value=time(10, 0))
    
    if st.form_submit_button("Confirmar Reserva"):
        inicio_dt = datetime.combine(fecha_res, h_inicio)
        fin_dt = datetime.combine(fecha_res, h_fin)
        
        if inicio_dt >= fin_dt:
            st.error("Error: La hora de fin debe ser posterior a la de inicio.")
        else:
            nueva_fila = {"Coche": coche_res, "Usuario": usuario, "Inicio": inicio_dt, "Fin": fin_dt, "Garaje": RELACION[coche_res], "Llegado": False}
            df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
            guardar_datos(df)
            st.rerun()

# --- 4. LISTA DETALLADA Y CANCELACIÓN ---
st.divider()
st.subheader("📝 Próximas Reservas y Gestión")

if not df.empty:
    # Mostramos reservas que no han llegado aún
    df_ver = df[df['Llegado'] == False].sort_values('Inicio')
    
    if not df_ver.empty:
        # Mostramos la tabla con las columnas que querías
        st.dataframe(
            df_ver[['Coche', 'Usuario', 'Inicio', 'Fin']], 
            column_config={
                "Inicio": st.column_config.DatetimeColumn("Desde", format="D MMM, HH:mm"),
                "Fin": st.column_config.DatetimeColumn("Hasta", format="D MMM, HH:mm"),
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Selector para cancelar
        opciones_cancelar = [f"{r['Coche']} - {r['Usuario']} ({r['Inicio'].strftime('%d/%m %H:%M')})" for i, r in df_ver.iterrows()]
        seleccion = st.selectbox("Si te has equivocado, elige para borrar:", opciones_cancelar)
        if st.button("❌ Cancelar Reserva"):
            indice = df_ver.index[opciones_cancelar.index(seleccion)]
            df = df.drop(indice)
            guardar_datos(df)
            st.rerun()
    else:
        st.info("No hay reservas pendientes.")
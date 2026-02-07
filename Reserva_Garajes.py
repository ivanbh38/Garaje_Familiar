import streamlit as st
import pandas as pd
from datetime import datetime, time
import os
import pytz # Importamos la librería de zonas horarias

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Garajes Pontika/Beraun", page_icon="🅿️")

# Definimos la zona horaria de España
TZ_MADRID = pytz.timezone('Europe/Madrid')

RELACION = {
    "Furgoneta": "Pontika Furgoneta",
    "Zafira": "Beraun",
    "Astra": "Pontika Astra"
}

ARCHIVO_DB = 'reservas.csv'

def obtener_hora_madrid():
    # Obtiene la hora actual en Madrid y quita la información de zona para poder comparar con el Excel
    return datetime.now(TZ_MADRID).replace(tzinfo=None)

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
ahora = obtener_hora_madrid()

# --- 1. TÍTULO Y BOTÓN DE REFRESCO ---
col_tit, col_ref = st.columns([3, 1])
with col_tit:
    st.title("🚗 Gestión de Garajes v1.0.3")
with col_ref:
    # Este botón sirve para recargar la página si estás esperando a que cambie la hora
    if st.button("🔄 Actualizar"):
        st.rerun()

st.caption(f"Hora del sistema (Madrid): {ahora.strftime('%H:%M')}")

# --- 2. ESTADO ACTUAL ---
st.subheader("Estado actual:")
cols = st.columns(3)

for i, (coche, garaje) in enumerate(RELACION.items()):
    # Buscamos la reserva activa o la más próxima no llegada
    reserva_coche = df[(df['Coche'] == coche) & (df['Llegado'] == False)].sort_values('Inicio').head(1)
    
    with cols[i % 3]:
        if not reserva_coche.empty:
            res = reserva_coche.iloc[0]
            hora_fin_str = res['Fin'].strftime('%H:%M')
            hora_ini_str = res['Inicio'].strftime('%H:%M')
            
            # COMPARACIÓN DE HORAS CORREGIDA
            if ahora >= res['Inicio'] and ahora <= res['Fin']:
                # ESTÁ DENTRO DEL HORARIO
                st.success(f"🟢 **{garaje}**\n\nLIBRE")
                st.caption(f"Usa: {res['Usuario']}\nFin: {hora_fin_str}")
                
            elif ahora > res['Fin']:
                # SE HA PASADO DE HORA
                st.warning(f"🟠 **{garaje}**\n\nPENDIENTE")
                st.caption(f"Debía volver: {hora_fin_str}")
            else:
                # ES FUTURO
                st.error(f"🔴 **{garaje}**\n\nOCUPADO")
                st.caption(f"Próxima: {hora_ini_str}")
        else:
            st.error(f"🔴 **{garaje}**\n\nOCUPADO")
            st.caption(f"Sin reservas")

# --- 3. BOTÓN DE CONFIRMACIÓN DE LLEGADA ---
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

# --- 4. FORMULARIO DE RESERVA ---
st.divider()
st.subheader("📅 Nueva Reserva")
with st.form("nueva_reserva"):
    usuario = st.selectbox("Usuario", ["Sergio", "Sylvia", "Iván", "Maider"])
    coche_res = st.selectbox("Coche", list(RELACION.keys()))
    fecha_res = st.date_input("Día", value=ahora.date(), min_value=ahora.date())
    
    c1, c2 = st.columns(2)
    with c1:
        # Ponemos una hora por defecto cómoda
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

# --- 5. LISTA DETALLADA Y CANCELACIÓN ---
st.divider()
st.subheader("📝 Gestión")

if not df.empty:
    df_ver = df[df['Llegado'] == False].sort_values('Inicio')
    
    if not df_ver.empty:
        # Tabla visual
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
        seleccion = st.selectbox("Borrar reserva:", opciones_cancelar)
        if st.button("❌ Cancelar"):
            indice = df_ver.index[opciones_cancelar.index(seleccion)]
            df = df.drop(indice)
            guardar_datos(df)
            st.rerun()
    else:
        st.info("No hay reservas pendientes.")
